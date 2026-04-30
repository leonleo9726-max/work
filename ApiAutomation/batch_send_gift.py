"""
批量发送礼物脚本（多线程 + 连接池）。

使用 ThreadPoolExecutor 并发发送礼物，通过 HttpUtils 连接池复用 HTTP 连接。
"""

import argparse
import json
import logging
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.http_utils import HttpUtils
from config import settings

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


BATCH_SEND_GIFT_PATH = "/live/stay/gift/batch-send"


def load_login_credentials():
    """从 batch_login_credentials.json 加载登录凭证"""
    credentials_file = PROJECT_ROOT / "data" / "batch_login_credentials.json"
    if not credentials_file.exists():
        logger.error("错误: 登录凭证文件不存在: %s", credentials_file)
        logger.error("请先运行 batch_login.py --save-credentials 生成登录凭证")
        sys.exit(1)

    with credentials_file.open("r", encoding="utf-8") as f:
        credentials = json.load(f)

    # 转换为列表，每个元素包含手机号和凭证信息
    # batch_login_credentials.json 的 key 是手机号
    credential_list = []
    for phone_number, cred in credentials.items():
        credential_list.append({
            "stayUserId": cred.get("stayUserId", ""),
            "phone_number": cred.get("phone_number", phone_number),
            "stayToken": cred.get("stayToken", ""),
            "uniqueId": cred.get("uniqueId", "")
        })

    return credential_list


def build_business_headers(stay_token):
    """构建业务请求头"""
    headers = settings.build_common_encrypted_headers()
    headers["token"] = stay_token
    return headers


def is_success(response):
    """判断礼物发送是否成功"""
    if not isinstance(response, dict):
        return False

    # 检查各种成功标志
    if response.get("code") in (0, "0", 200, "200"):
        return True
    if response.get("stayCode") in (0, "0", 200, "200"):
        return True
    if response.get("stayIsSuccess") is True:
        return True
    if response.get("success") is True:
        return True
    if response.get("status") in ("success", "ok", "SUCCESS", "OK"):
        return True

    return False


def get_error_details(response):
    """从响应中提取详细的错误信息"""
    if not isinstance(response, dict):
        return "无效的响应格式"

    error_info = []

    # 检查各种可能的错误字段
    error_fields = [
        "stayErrorMessage",
        "stayMessage",
        "errorMessage",
        "message",
        "msg",
        "error"
    ]

    for field in error_fields:
        if field in response and response[field]:
            error_info.append(f"{field}: {response[field]}")

    # 检查错误代码
    code_fields = ["stayCode", "code", "errorCode"]
    for field in code_fields:
        if field in response:
            error_info.append(f"{field}: {response[field]}")

    if error_info:
        return "; ".join(error_info)

    return str(response)


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
            encrypt_key=settings.TEST_ENCRYPT_KEY,
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
    parser.add_argument("--show-full-response", action="store_true", help="打印完整的失败响应（用于调试）")

    # 礼物参数
    parser.add_argument("--recipients", type=int, nargs="+", default=[15712],
                        help="接收者用户ID列表，可传多个值，默认: 15712")
    parser.add_argument("--gift-id", type=int, default=93, help="礼物ID，默认93")
    parser.add_argument("--count", type=int, default=10, help="礼物数量，默认10")
    parser.add_argument("--source-type", type=int, default=1, choices=[1, 2],
                        help="来源类型，默认1")
    parser.add_argument("--object-id", type=int, default=202604290000000003,
                        help="对象ID，默认202604290000000003")
    parser.add_argument("--room-id", type=str, default="15712", help="房间ID，默认15712")

    args = parser.parse_args()

    # 配置日志
    configure_logging(args.verbose)

    # 加载登录凭证
    credentials = load_login_credentials()
    if args.max_count > 0:
        credentials = credentials[args.start_index : args.start_index + args.max_count]
    else:
        credentials = credentials[args.start_index:]

    total = len(credentials)
    if total == 0:
        logger.error("没有找到可用的登录凭证，请检查 data/batch_login_credentials.json")
        return

    logger.info("开始批量发送礼物: total=%s, workers=%s, delay=%s", total, args.workers, args.delay)
    logger.info("礼物参数: recipients=%s, gift_id=%s, count=%s, source_type=%s, object_id=%s, room_id=%s",
                args.recipients, args.gift_id, args.count, args.source_type, args.object_id, args.room_id)

    success_count = 0
    failures = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_cred = {
            executor.submit(
                execute_send_gift,
                cred,
                args.recipients,
                args.gift_id,
                args.count,
                args.source_type,
                args.object_id,
                args.room_id,
                args.delay,
                args.verbose,
                args.retry,
                args.retry_delay,
                args.jitter,
            ): cred
            for cred in credentials
        }

        for future in as_completed(future_to_cred):
            result = future.result()
            if result["ok"]:
                success_count += 1
            else:
                failures.append(result)
                error_msg = result.get('error_details', str(result.get('response', '未知错误')))
                logger.warning("[FAILED] %s (ID: %s) stage=%s attempt=%s", result['phone'], result['stayUserId'], result['stage'], result.get('attempt', 1))
                logger.debug("        错误: %s", error_msg)
                if args.show_full_response and result.get('response'):
                    logger.debug("        完整响应: %s", json.dumps(result['response'], ensure_ascii=False, indent=2))

    elapsed = time.time() - start_time
    logger.info("批量发送礼物完成: 成功=%s/%s, 失败=%s, 耗时=%.1fs", success_count, total, len(failures), elapsed)

    # 清理当前线程的 Session 连接
    HttpUtils.close_session()

    if failures:
        logger.warning("失败用户列表 (手机号 - 用户ID):")
        for fail in failures:
            logger.warning("  %s - %s", fail['phone'], fail['stayUserId'])


# 使用示例:
#   python batch_send_gift.py --workers 5 --delay 0.5 --recipients 15685 --gift-id 93 --count 10 --object-id 202604290000000010
#   python batch_send_gift.py --workers 5 --delay 0.5 --recipients 15685 --gift-id 15 --count 10 --object-id 202604290000000014 --room-id 15685 --show-full-response

if __name__ == "__main__":
    main()
