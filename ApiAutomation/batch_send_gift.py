"""根据本地登录凭证批量发送直播礼物。"""

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

from common.api_paths import BATCH_SEND_GIFT_PATH
from common.auth_utils import load_batch_login_credentials
from common.live_gift import (
    GIFT_SOURCE_TYPES,
    LIVE_GIFT_SOURCE_TYPE,
    RECIPIENT_MODES,
    build_live_gift_headers,
    build_live_gift_payload,
    post_live_gift,
)
from common.http_utils import HttpUtils
from common.live_heartbeat import LiveHeartbeatLoop
from common.response_utils import extract_error_message, is_api_success
from config import settings


logger = logging.getLogger(__name__)


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


def post_batch_gift(
    credential: dict,
    payload: dict,
):
    """使用一个发送人凭证向直播服务发送一次明文送礼请求。"""
    stay_token = credential.get("stayToken")
    stay_user_id = credential.get("stayUserId")
    if not stay_token or not stay_user_id:
        raise ValueError("发送人凭证缺少 stayToken 或 stayUserId")

    url = f"{settings.LIVE_BASE_URL}{BATCH_SEND_GIFT_PATH}"
    return post_live_gift(url, payload, build_live_gift_headers(credential))


def distribute_request_counts(total_requests: int, sender_count: int) -> list[int]:
    """将总请求数尽量均分给各发送人，并保证总数精确一致。"""
    if total_requests <= 0:
        raise ValueError("total_requests 必须为正整数")
    if sender_count <= 0:
        raise ValueError("sender_count 必须为正整数")

    base_count, remainder = divmod(total_requests, sender_count)
    return [base_count + (1 if index < remainder else 0) for index in range(sender_count)]


def execute_send_gift_repeated(
    credential: dict,
    payload: dict,
    request_count: int,
    delay: float = 0.0,
    heartbeat_loop: Optional[LiveHeartbeatLoop] = None,
    progress_every: int = 0,
) -> dict:
    """由一个发送人连续执行多次送礼，并返回可汇总结果。"""
    if request_count <= 0:
        raise ValueError("request_count 必须为正整数")

    user_id = str(credential.get("stayUserId", ""))
    phone_number = credential.get("phone_number", user_id)
    attempted_count = 0
    success_count = 0
    failure_count = 0
    last_error = None
    try:
        for index in range(1, request_count + 1):
            if heartbeat_loop:
                heartbeat_loop.raise_if_failed()
            if delay > 0:
                time.sleep(delay)

            attempted_count += 1
            try:
                response = post_batch_gift(credential, payload)
                if is_api_success(response):
                    success_count += 1
                else:
                    failure_count += 1
                    last_error = extract_error_message(response)
            except Exception as exc:
                failure_count += 1
                last_error = str(exc)

            if progress_every and index % progress_every == 0:
                logger.info(
                    "发送人=%s 进度=%s/%s，成功=%s，失败=%s",
                    user_id,
                    index,
                    request_count,
                    success_count,
                    failure_count,
                )

        return {
            "sender_user_id": user_id,
            "phone": phone_number,
            "planned_count": request_count,
            "attempted_count": attempted_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "skipped_count": request_count - attempted_count,
            "ok": failure_count == 0 and attempted_count == request_count,
            "error": last_error,
        }
    except Exception as exc:
        last_error = str(exc)
        return {
            "sender_user_id": user_id,
            "phone": phone_number,
            "planned_count": request_count,
            "attempted_count": attempted_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "skipped_count": request_count - attempted_count,
            "ok": False,
            "error": last_error,
        }
    finally:
        HttpUtils.close_session()


def execute_send_gift(
    credential: dict,
    payload: dict,
    delay: float = 0.0,
    heartbeat_loop: Optional[LiveHeartbeatLoop] = None,
) -> dict:
    """执行单个发送人的一次送礼任务，保留原有调用接口。"""
    return execute_send_gift_repeated(
        credential,
        payload,
        request_count=1,
        delay=delay,
        heartbeat_loop=heartbeat_loop,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量发送直播礼物")
    parser.add_argument("--run-api", action="store_true", help="确认执行真实送礼请求")
    parser.add_argument("--workers", type=int, default=1, help="并发发送人数，默认 1")
    parser.add_argument("--delay", type=float, default=0.0, help="每个请求发送前的等待秒数")
    parser.add_argument("--start-index", type=int, default=0, help="从第几个本地凭证开始")
    parser.add_argument("--max-count", type=int, default=0, help="最多使用多少个发送人；0 表示全部")
    parser.add_argument(
        "--total-requests",
        type=int,
        help="总送礼请求数；未指定时每位发送人发送 1 次",
    )
    parser.add_argument("--sender-user-ids", type=str, nargs="+", help="仅使用指定 user_id 的发送人")
    parser.add_argument("--gift-id", type=int, required=True, help="礼物 ID")
    parser.add_argument("--count", type=int, required=True, help="每位发送人的礼物数量")
    parser.add_argument(
        "--source-type",
        type=int,
        default=LIVE_GIFT_SOURCE_TYPE,
        choices=GIFT_SOURCE_TYPES,
        help="来源类型，默认 1（直播）",
    )
    parser.add_argument("--object-id", type=int, required=True, help="直播间 ID")
    parser.add_argument("--payload", type=str, help="礼物负载信息（可选）")
    parser.add_argument("--backpack-id", type=int, help="背包礼物 ID（可选）")
    parser.add_argument("--room-id", type=str, help="房间 ID（可选）")
    parser.add_argument("--live-id", type=int, required=True, help="心跳接口的 liveId")
    parser.add_argument(
        "--heartbeat-interval",
        type=float,
        default=10.0,
        help="直播心跳间隔秒数，默认 10",
    )
    recipients = parser.add_mutually_exclusive_group(required=True)
    recipients.add_argument("--recipients", type=int, nargs="+", help="收礼人 user_id 列表")
    recipients.add_argument(
        "--recipient-mode",
        choices=RECIPIENT_MODES,
        help="收礼范围：ALL_MIC（全麦位）或 ALL_ROOM（全房间）",
    )
    parser.add_argument("--verbose", action="store_true", help="输出每个发送人的结果")
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
        help="每位发送人每完成多少次请求输出一次进度；0 表示不输出，默认 1000",
    )
    return parser.parse_args()


def select_credentials(args: argparse.Namespace) -> list[dict]:
    credentials = load_batch_login_credentials()
    if args.sender_user_ids:
        allowed_user_ids = set(args.sender_user_ids)
        credentials = [
            item for item in credentials if str(item.get("stayUserId")) in allowed_user_ids
        ]
    credentials = credentials[args.start_index :]
    if args.max_count > 0:
        credentials = credentials[: args.max_count]
    return credentials


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)
    if not args.run_api:
        logger.error("拒绝执行真实送礼；请明确添加 --run-api")
        return 2
    if args.workers <= 0 or args.delay < 0 or args.live_id < 0 or args.heartbeat_interval <= 0:
        logger.error("workers 和 heartbeat-interval 必须大于 0，delay 和 live-id 不能小于 0")
        return 2
    if args.total_requests is not None and args.total_requests <= 0:
        logger.error("total-requests 必须为正整数")
        return 2
    if args.progress_every < 0:
        logger.error("progress-every 不能小于 0")
        return 2
    try:
        payload = build_live_gift_payload(
            args.recipients,
            gift_id=args.gift_id,
            count=args.count,
            source_type=args.source_type,
            object_id=args.object_id,
            recipient_mode=args.recipient_mode,
            payload=args.payload,
            backpack_id=args.backpack_id,
            room_id=args.room_id,
        )
    except ValueError as exc:
        logger.error("请求参数无效: %s", exc)
        return 2

    credentials = select_credentials(args)
    if not credentials:
        logger.error("没有符合条件的本地发送人凭证")
        return 2

    total_requests = args.total_requests or len(credentials)
    request_counts = distribute_request_counts(total_requests, len(credentials))
    scheduled_sends = [
        (credential, request_count)
        for credential, request_count in zip(credentials, request_counts)
        if request_count > 0
    ]
    active_credentials = [credential for credential, _ in scheduled_sends]

    heartbeat_loop = LiveHeartbeatLoop(
        active_credentials,
        live_id=args.live_id,
        interval_seconds=args.heartbeat_interval,
    )
    try:
        heartbeat_loop.start()
    except RuntimeError as exc:
        logger.error("首轮直播心跳未完成，取消送礼: %s", exc)
        return 1

    logger.info(
        "开始批量送礼：发送人=%s，总请求=%s，并发=%s，liveId=%s，心跳间隔=%ss，载荷=%s",
        len(active_credentials),
        total_requests,
        args.workers,
        args.live_id,
        args.heartbeat_interval,
        payload,
    )
    results = []
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [
                executor.submit(
                    execute_send_gift_repeated,
                    credential,
                    payload,
                    request_count,
                    args.delay,
                    heartbeat_loop,
                    args.progress_every,
                )
                for credential, request_count in scheduled_sends
            ]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                if args.verbose:
                    level = logging.INFO if result["ok"] else logging.WARNING
                    logger.log(
                        level,
                        "发送人=%s 成功=%s，请求=%s/%s，失败=%s %s",
                        result["sender_user_id"],
                        result["ok"],
                        result["attempted_count"],
                        result["planned_count"],
                        result["failure_count"],
                        result.get("error") or "",
                    )
    finally:
        heartbeat_loop.stop()

    attempted_count = sum(result["attempted_count"] for result in results)
    success_count = sum(result["success_count"] for result in results)
    failure_count = sum(result["failure_count"] for result in results)
    skipped_count = sum(result["skipped_count"] for result in results)
    heartbeat_failures = heartbeat_loop.failures
    if heartbeat_failures:
        logger.error("送礼期间发生 %s 个心跳失败", len(heartbeat_failures))
    logger.info(
        "批量送礼完成：计划=%s，尝试=%s，成功=%s，失败=%s，未执行=%s",
        total_requests,
        attempted_count,
        success_count,
        failure_count,
        skipped_count,
    )
    return 0 if success_count == total_requests and not heartbeat_failures else 1


if __name__ == "__main__":
    sys.exit(main())
