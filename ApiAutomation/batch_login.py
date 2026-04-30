"""
批量登录脚本（多线程 + 连接池）。

使用 ThreadPoolExecutor 并发执行登录，通过 HttpUtils 连接池复用 HTTP 连接。
"""

import argparse
import csv
import logging
import random
import sys
import time
import base64
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


def load_csv_values(data_file: Path, field_name: str):
    """从CSV文件加载指定字段的值"""
    values = []
    with data_file.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            value = (row.get(field_name) or "").strip()
            if value:
                values.append(value)
    return values


def allocate_unique_ids(phones, unique_ids):
    """为每个手机号分配设备ID，当手机号比设备ID多时循环使用设备ID"""
    if not unique_ids:
        unique_ids = ["bac1131e82cd4c738e3199375ffe77b4"]

    test_cases = []
    # 使用循环分配策略，确保每个设备ID被均匀使用
    for i, phone in enumerate(phones):
        # 使用取模运算循环选择设备ID
        unique_id = unique_ids[i % len(unique_ids)]
        test_cases.append({"phone_number": phone, "uniqueId": unique_id})

    return test_cases


def _to_base64(value):
    """将字符串转为base64编码"""
    if value is None:
        return None
    return base64.b64encode(str(value).encode("utf-8")).decode("utf-8")


def create_login_params(phone_number, unique_id, verification_code="8888", area_code="86", password="a123456"):
    """创建登录参数"""
    params = {
        "platformType": 0,
        "appType": 0,
        "variantType": 0,
        "appVersion": "2.1.4",
        "buildVersion": 317,
        "osModel": "V2278A",
        "osVersion": "13",
        "language": "en",
        "uniqueId": unique_id,
        "uuid": "9fcd8047c27442138fdbdcddcb026ebd",
        "deviceId": "be825900787d419f9872eed48566f45c",
        "widevineId": None,
        "idfv": None,
        "idfa": None,
        "mcc": None,
        "mnc": None,
        "networkName": None,
        "inviteCode": None,
        "downloadChannel": None,
        "ipAddress": "41.235.64.230",
        "remoteIp": "41.235.64.230",
        "languageCountry": "en",
        "appLanguage": "en",
        "areaCode": area_code,
        "phoneNumber": phone_number,
        "verificationCode": verification_code,
        "captchaType": 0,
        "loginPwdType": 0,
        "password": _to_base64(password),
        "tablet": 0,
        "simulator": 0,
        "useVpn": 0,
        "useRoot": 0,
        "useDebug": 0,
        "mockLocation": 0,
        "timezone": "Asia/Shanghai",
    }
    return params


def is_success(response):
    """判断登录是否成功"""
    if not isinstance(response, dict):
        return False
    
    # 检查特定的网络错误代码
    stay_code = response.get("stayCode")
    if stay_code == 980003000:  # 网络错误代码
        error_msg = response.get("stayErrorMessage", "")
        if "100087" in str(error_msg):
            # 这是网络不可用错误，需要重试
            return False
    
    if stay_code in (0, "0", 200, "200"):
        return True
    if response.get("stayIsSuccess") is True:
        return True
    
    code = response.get("code")
    if code in (0, "0", 200, "200"):
        return True
    if response.get("success") is True:
        return True
    if response.get("status") in ("success", "ok", "SUCCESS", "OK"):
        return True
    
    data = response.get("data")
    if isinstance(data, dict) and (data.get("token") or data.get("accessToken") or data.get("jwt")):
        return True
    
    return False


def extract_login_info(response):
    """从登录响应中提取用户信息"""
    if not isinstance(response, dict):
        return None

    candidates = []
    if isinstance(response.get("stayResult"), dict):
        candidates.append(response["stayResult"])
    if isinstance(response.get("data"), dict):
        candidates.append(response["data"])
    candidates.append(response)

    for data in candidates:
        if not isinstance(data, dict):
            continue
        stay_user_id = data.get("stayUserId")
        stay_token = data.get("stayToken")
        if stay_user_id and stay_token:
            return {
                "stayUserId": str(stay_user_id),
                "stayToken": str(stay_token),
            }
    return None


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


def execute_login(test_case, encrypt_key, delay, verbose=False, retry=1, retry_delay=1.0, jitter=0.3):
    """执行单个登录任务"""
    phone_number = test_case["phone_number"]
    unique_id = test_case["uniqueId"]
    headers = settings.build_common_encrypted_headers()
    login_url = f"{settings.BASE_URL}{settings.LOGIN_PHONE_PATH}"

    last_failure = None
    for attempt in range(1, retry + 1):
        if delay and delay > 0:
            # 添加随机抖动，避免请求过于规律
            actual_delay = delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.1, actual_delay))

        if verbose and attempt > 1:
            logger.info("[RETRY %s/%s] %s", attempt, retry, phone_number)

        login_payload = create_login_params(phone_number, unique_id)
        login_response = HttpUtils.post(
            url=login_url,
            data=login_payload,
            headers=headers,
            encrypt_key=encrypt_key,
        )

        if is_success(login_response):
            login_info = extract_login_info(login_response)
            if verbose:
                if login_info:
                    logger.info("[OK] %s - stayUserId=%s", phone_number, login_info['stayUserId'])
                else:
                    logger.info("[OK] %s", phone_number)
            return {
                "phone": phone_number,
                "ok": True,
                "login_info": login_info,
                "response": login_response
            }

        # 提取错误详情
        error_details = get_error_details(login_response)
        
        last_failure = {
            "phone": phone_number,
            "unique_id": unique_id,
            "ok": False,
            "stage": "login",
            "response": login_response,
            "error_details": error_details,
            "attempt": attempt
        }
        
        # 检查是否是网络错误，如果是则增加重试延迟
        is_network_error = False
        if isinstance(login_response, dict):
            stay_code = login_response.get("stayCode")
            error_msg = login_response.get("stayErrorMessage", "")
            if stay_code == 980003000 and "100087" in str(error_msg):
                is_network_error = True
                if verbose:
                    logger.warning("[网络错误 100087] %s 将在重试前等待更长时间", phone_number)
        
        if attempt < retry:
            # 如果是网络错误，增加重试延迟
            extra_delay = 2.0 if is_network_error else 0.0
            actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter)) + extra_delay
            time.sleep(max(0.5, actual_retry_delay))

    return last_failure


def main():
    parser = argparse.ArgumentParser(description="批量登录用户，支持多线程和时间间隔控制")
    parser.add_argument("--workers", type=int, default=3, help="并发线程数，默认3（减少并发避免网络错误）")
    parser.add_argument("--delay", type=float, default=1.0, help="每个任务开始前等待秒数，默认1.0（增加延迟避免频率过高）")
    parser.add_argument("--retry", type=int, default=2, help="每个手机号最大重试次数，默认2")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="失败后重试前等待秒数，默认2.0")
    parser.add_argument("--jitter", type=float, default=0.3, help="随机抖动系数（0-1），默认0.3，用于避免规律请求")
    parser.add_argument("--verbose", action="store_true", help="是否打印每条成功日志")
    parser.add_argument("--start-index", type=int, default=0, help="从第几个手机号开始登录，默认0")
    parser.add_argument("--max-count", type=int, default=0, help="最多登录多少个手机号，默认0表示全部")
    parser.add_argument("--save-credentials", action="store_true", help="是否保存登录凭证到JSON文件")
    args = parser.parse_args()

    # 配置日志
    configure_logging(args.verbose)

    # 加载手机号和设备ID
    phones = load_csv_values(PROJECT_ROOT / "data" / "login_phone.csv", "phone_number")
    unique_ids = load_csv_values(PROJECT_ROOT / "data" / "device_ids.csv", "uniqueId")

    if args.max_count > 0:
        phones = phones[args.start_index : args.start_index + args.max_count]
    else:
        phones = phones[args.start_index:]

    test_cases = allocate_unique_ids(phones, unique_ids)
    total = len(test_cases)
    if total == 0:
        logger.error("没有找到可登录的手机号，请检查 data/login_phone.csv")
        return

    logger.info("开始批量登录: total=%s, workers=%s, delay=%s", total, args.workers, args.delay)

    success_count = 0
    failures = []
    login_credentials = {}
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_case = {
            executor.submit(
                execute_login,
                case,
                settings.TEST_ENCRYPT_KEY,
                args.delay,
                args.verbose,
                args.retry,
                args.retry_delay,
                args.jitter,
            ): case
            for case in test_cases
        }
        for future in as_completed(future_to_case):
            result = future.result()
            if result["ok"]:
                success_count += 1
                # 保存登录凭证
                if args.save_credentials and result.get("login_info"):
                    phone = result["phone"]
                    login_info = result["login_info"]
                    login_credentials[phone] = {
                        "phone_number": phone,
                        "stayUserId": login_info["stayUserId"],
                        "stayToken": login_info["stayToken"],
                        "uniqueId": future_to_case[future]["uniqueId"]
                    }
            else:
                failures.append(result)
                error_msg = result.get('error_details', str(result.get('response', '未知错误')))
                logger.warning("[FAILED] %s stage=%s attempt=%s", result['phone'], result['stage'], result.get('attempt', 1))
                logger.debug("        错误: %s", error_msg[:100])

    elapsed = time.time() - start_time
    logger.info("批量登录完成: 成功=%s/%s, 失败=%s, 耗时=%.1fs", success_count, total, len(failures), elapsed)
    
    # 清理当前线程的 Session 连接
    HttpUtils.close_session()
    
    # 保存登录凭证
    if args.save_credentials and login_credentials:
        import json
        credentials_file = PROJECT_ROOT / "data" / "batch_login_credentials.json"
        with credentials_file.open("w", encoding="utf-8") as f:
            json.dump(login_credentials, f, ensure_ascii=False, indent=2)
        logger.info("登录凭证已保存到: %s", credentials_file)
    
    if failures:
        logger.warning("失败手机号列表 (手机号 - 设备ID):")
        for fail in failures:
            logger.warning("  %s - %s stage=%s", fail['phone'], fail.get('unique_id', '未知设备ID'), fail['stage'])


# 多线程批量登录 python batch_login.py --workers 10 --delay 0.5 --save-credentials
# --workers 10：使用 10 个线程并发执行
# --delay 0.5：每个任务启动前等待 0.5 秒，避免请求过于密集
# --save-credentials：保存登录凭证到JSON文件

if __name__ == "__main__":
    main()
