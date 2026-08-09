"""
批量发送礼物脚本（多线程 + 连接池）。

使用 BatchRunner 执行并发与重试，通过 HttpUtils 复用 HTTP 连接。
"""

import argparse
import logging
import random
import sys
import time
from pathlib import Path

from common.api_paths import BATCH_SEND_GIFT_PATH
from common.auth_utils import build_business_headers, load_batch_login_credentials
from common.batch_runner import BatchPolicy, BatchRunner
from common.http_utils import HttpUtils
from common.logging_utils import install_sensitive_data_filter
from common.response_utils import get_error_details, is_success
from config import settings

PROJECT_ROOT = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)


def configure_logging(verbose: bool = False):
    """配置日志输出"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    install_sensitive_data_filter()


def execute_send_gift(credential, recipients, gift_id, count, source_type, object_id, room_id, delay, verbose=False, retry=1, retry_delay=1.0, jitter=0.3):
    """执行单个用户的批量发送礼物任务"""
    stay_user_id = credential["stayUserId"]
    phone_number = credential["phone_number"]
    stay_token = credential["stayToken"]

    last_failure = None
    for attempt in range(1, retry + 1):
        if delay and delay > 0:
            actual_delay = delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.1, actual_delay))

        if verbose and attempt > 1:
            logger.info("[RETRY %s/%s] %s (ID: %s)", attempt, retry, phone_number, stay_user_id)

        # 构建请求
        headers = build_business_headers(stay_token)
        url = f"{settings.BASE_URL}{BATCH_SEND_GIFT_PATH}"
        payload = {
            "recipients": recipients,
            "giftId": gift_id,
            "count": count,
            "sourceType": source_type,
            "objectId": object_id,
            "roomId": room_id,
        }

        # 发送请求
        response = HttpUtils.post(
            url=url,
            data=payload,
            headers=headers,
            encrypt_key=settings.require_encrypt_key(),
            locale="en",
            timestamp=str(int(time.time() * 1000)),
        )

        # 处理 response 为 None 的情况（网络错误等）
        if response is None:
            error_details = "请求失败（网络错误或超时），响应为 None"
            last_failure = {
                "phone": phone_number,
                "stayUserId": stay_user_id,
                "ok": False,
                "stage": "send_gift",
                "response": None,
                "error_details": error_details,
                "attempt": attempt
            }
            if attempt < retry:
                actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
                time.sleep(max(0.5, actual_retry_delay))
            continue

        if is_success(response):
            if verbose:
                logger.info("[OK] %s (ID: %s) - 礼物发送成功", phone_number, stay_user_id)
            return {
                "phone": phone_number,
                "stayUserId": stay_user_id,
                "ok": True,
                "response": response
            }

        # 提取错误详情
        error_details = get_error_details(response)

        last_failure = {
            "phone": phone_number,
            "stayUserId": stay_user_id,
            "ok": False,
            "stage": "send_gift",
            "response": response,
            "error_details": error_details,
            "attempt": attempt
        }

        if attempt < retry:
            actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.5, actual_retry_delay))

    return last_failure


def main():
    parser = argparse.ArgumentParser(description="多线程批量发送礼物")
    parser.add_argument("--workers", type=int, default=3, help="并发线程数，默认3")
    parser.add_argument("--delay", type=float, default=1.0, help="每个任务开始前等待秒数，默认1.0")
    parser.add_argument("--retry", type=int, default=2, help="每个用户最大重试次数，默认2")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="失败后重试前等待秒数，默认2.0")
    parser.add_argument("--jitter", type=float, default=0.3, help="随机抖动系数（0-1），默认0.3，用于避免规律请求")
    parser.add_argument("--verbose", action="store_true", help="是否打印每条成功日志")
    parser.add_argument("--start-index", type=int, default=0, help="从第几个用户开始，默认0")
    parser.add_argument("--max-count", type=int, default=0, help="最多发送多少个用户，默认0表示全部")
    # 礼物参数
    parser.add_argument("--recipients", type=int, nargs="+", required=True,
                        help="接收者用户ID列表，可传多个值")
    parser.add_argument("--gift-id", type=int, default=93, help="礼物ID，默认93")
    parser.add_argument("--count", type=int, default=10, help="礼物数量，默认10")
    parser.add_argument("--source-type", type=int, default=1, choices=[1, 2],
                        help="来源类型，默认1")
    parser.add_argument("--object-id", type=int, required=True, help="对象ID")
    parser.add_argument("--room-id", type=str, required=True, help="房间ID")

    args = parser.parse_args()

    # 配置日志
    configure_logging(args.verbose)

    # 加载登录凭证
    credentials = load_batch_login_credentials()
    if args.max_count > 0:
        credentials = credentials[args.start_index : args.start_index + args.max_count]
    else:
        credentials = credentials[args.start_index:]

    total = len(credentials)
    if total == 0:
        logger.error("没有找到可用的登录凭证，请检查 data/local/batch_login_credentials.json")
        return

    logger.info("开始批量发送礼物: total=%s, workers=%s, delay=%s", total, args.workers, args.delay)
    logger.info("礼物参数: recipients=%s, gift_id=%s, count=%s, source_type=%s, object_id=%s, room_id=%s",
                args.recipients, args.gift_id, args.count, args.source_type, args.object_id, args.room_id)

    success_count = 0
    failures = []
    start_time = time.time()

    summary = BatchRunner(finalizer=HttpUtils.close_session).run(
        credentials,
        lambda credential: execute_send_gift(
            credential,
            args.recipients,
            args.gift_id,
            args.count,
            args.source_type,
            args.object_id,
            args.room_id,
            0,
            args.verbose,
            1,
            0,
            0,
        ),
        BatchPolicy(
            workers=args.workers,
            attempts=args.retry,
            delay=args.delay,
            retry_delay=args.retry_delay,
            jitter=args.jitter,
        ),
        succeeded=lambda result: result["ok"],
    )
    for item_result in summary.results:
        result = item_result.result or {
            "ok": False,
            "phone": item_result.item.get("phone_number", "***"),
            "stayUserId": item_result.item.get("stayUserId", "***"),
            "stage": "exception",
            "error_details": item_result.error,
        }
        if result["ok"]:
            success_count += 1
        else:
            failures.append(result)
            error_msg = result.get('error_details', '未知错误')
            logger.warning("[FAILED] %s (ID: %s) stage=%s attempt=%s", result['phone'], result['stayUserId'], result['stage'], item_result.attempts)
            logger.debug("        错误: %s", error_msg)

    elapsed = time.time() - start_time
    logger.info("批量发送礼物完成: 成功=%s/%s, 失败=%s, 耗时=%.1fs", success_count, total, len(failures), elapsed)

    if failures:
        logger.warning("失败用户列表 (手机号 - 用户ID):")
        for fail in failures:
            logger.warning("  %s - %s", fail['phone'], fail['stayUserId'])


# 使用示例:
#   python batch_send_gift.py --workers 5 --delay 0.5 --recipients <ID> --gift-id 93 --count 10 --object-id <ID> --room-id <ID>

if __name__ == "__main__":
    main()
