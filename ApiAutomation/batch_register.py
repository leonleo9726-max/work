"""
批量注册脚本（多线程 + 连接池）。

使用 BatchRunner 执行并发与重试，通过 HttpUtils 复用 HTTP 连接。
"""

import argparse
import csv
import logging
import random
import sys
import time
from pathlib import Path

from common.batch_runner import BatchPolicy, BatchRunner
from common.http_utils import HttpUtils
from common.logging_utils import install_sensitive_data_filter
from common.registration_operations import (
    create_register_params,
    create_send_code_params,
    register_user,
    send_verification_code,
)
from common.response_utils import is_success
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


def load_csv_values(data_file: Path, field_name: str):
    values = []
    with data_file.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            value = (row.get(field_name) or "").strip()
            if value:
                values.append(value)
    return values


def allocate_unique_ids(phones, unique_ids):
    if not unique_ids:
        unique_ids = ["example-device-id"]

    test_cases = []
    for phone in phones:
        unique_id = random.choice(unique_ids)
        test_cases.append({"phone_number": phone, "uniqueId": unique_id})

    return test_cases


def execute_registration(test_case, encrypt_key, delay, verbose=False, retry=1, retry_delay=1.0):
    phone_number = test_case["phone_number"]
    unique_id = test_case["uniqueId"]

    last_failure = None
    for attempt in range(1, retry + 1):
        if delay and delay > 0:
            time.sleep(delay)

        if verbose and attempt > 1:
            logger.info("[RETRY %s/%s] %s", attempt, retry, phone_number)

        send_code_payload = create_send_code_params(phone_number, unique_id)
        send_response = send_verification_code(send_code_payload, encrypt_key)

        if not is_success(send_response):
            last_failure = {
                "phone": phone_number,
                "ok": False,
                "stage": "send_code",
                "response": send_response,
            }
            if attempt < retry:
                time.sleep(retry_delay)
                continue
            return last_failure

        register_payload = create_register_params(phone_number, unique_id)
        register_response = register_user(register_payload, encrypt_key)

        if is_success(register_response):
            if verbose:
                logger.info("[OK] %s", phone_number)
            return {"phone": phone_number, "ok": True}

        last_failure = {
            "phone": phone_number,
            "ok": False,
            "stage": "register",
            "response": register_response,
        }
        if attempt < retry:
            time.sleep(retry_delay)

    return last_failure


def main():
    parser = argparse.ArgumentParser(description="批量注册用户，支持多线程和时间间隔控制")
    parser.add_argument("--workers", type=int, default=5, help="并发线程数，默认5")
    parser.add_argument("--delay", type=float, default=0.5, help="每个任务开始前等待秒数，默认0.5")
    parser.add_argument("--retry", type=int, default=1, help="每个手机号最大重试次数，默认1")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="失败后重试前等待秒数，默认1.0")
    parser.add_argument("--verbose", action="store_true", help="是否打印每条成功日志")
    parser.add_argument("--start-index", type=int, default=0, help="从第几个手机号开始注册，默认0")
    parser.add_argument("--max-count", type=int, default=0, help="最多注册多少个手机号，默认0表示全部")
    args = parser.parse_args()

    # 配置日志
    configure_logging(args.verbose)

    phones = load_csv_values(PROJECT_ROOT / "data" / "local" / "register_phone.csv", "phone_number")
    unique_ids = load_csv_values(PROJECT_ROOT / "data" / "local" / "device_ids.csv", "uniqueId")

    if args.max_count > 0:
        phones = phones[args.start_index : args.start_index + args.max_count]
    else:
        phones = phones[args.start_index:]

    test_cases = allocate_unique_ids(phones, unique_ids)
    total = len(test_cases)
    if total == 0:
        logger.error("没有找到可注册的手机号，请检查 data/local/register_phone.csv")
        return

    logger.info("开始批量注册: total=%s, workers=%s, delay=%s", total, args.workers, args.delay)

    success_count = 0
    failures = []
    start_time = time.time()
    encrypt_key = settings.require_encrypt_key()
    summary = BatchRunner(finalizer=HttpUtils.close_session).run(
        test_cases,
        lambda case: execute_registration(
            case, encrypt_key, 0, args.verbose, 1, 0
        ),
        BatchPolicy(
            workers=args.workers,
            attempts=args.retry,
            delay=args.delay,
            retry_delay=args.retry_delay,
        ),
        succeeded=lambda result: result["ok"],
    )
    for item_result in summary.results:
        result = item_result.result or {
            "ok": False,
            "phone": item_result.item["phone_number"],
            "stage": "exception",
        }
        if result["ok"]:
            success_count += 1
        else:
            failures.append(result)
            logger.warning("[FAILED] %s stage=%s", result['phone'], result['stage'])

    elapsed = time.time() - start_time
    logger.info("批量注册完成: 成功=%s/%s, 失败=%s, 耗时=%.1fs", success_count, total, len(failures), elapsed)

    if failures:
        logger.warning("失败手机号列表:")
        for fail in failures:
            logger.warning("  %s stage=%s", fail['phone'], fail['stage'])


# 多线程批量注册 python batch_register.py --workers 10 --delay 0.5
# --workers 10：使用 10 个线程并发执行
# delay 0.5：每个任务启动前等待 0.5 秒，避免请求过于密集


if __name__ == "__main__":
    main()
