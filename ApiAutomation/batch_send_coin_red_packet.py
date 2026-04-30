"""
批量发送金币红包脚本（多线程 + 连接池）。

支持两种模式：
1. 仅发送金币红包（--skip-receive）
2. 发送金币红包并自动抢红包（串联模式）

通过 HttpUtils 连接池复用 HTTP 连接。
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


SEND_COIN_RED_PACKET_PATH = "/payer/redPacket/send/coin"
RECEIVE_RED_PACKET_PATH = "/payer/redPacket/receive"


def load_login_credentials():
    """从JSON文件加载登录凭证"""
    credentials_file = PROJECT_ROOT / "data" / "batch_login_credentials.json"
    if not credentials_file.exists():
        logger.error("错误: 登录凭证文件不存在: %s", credentials_file)
        logger.error("请先运行 batch_login.py --save-credentials 生成登录凭证")
        sys.exit(1)
    
    with credentials_file.open("r", encoding="utf-8") as f:
        credentials = json.load(f)
    
    # 转换为列表，每个元素包含手机号和凭证信息
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
    """判断红包发送是否成功"""
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


def extract_stay_red_packet_id(response):
    """从发红包接口的响应中提取 stayRedPacketId"""
    if not isinstance(response, dict):
        return None
    
    # 尝试从 stayResult 中提取
    stay_result = response.get("stayResult")
    if isinstance(stay_result, dict):
        red_packet_id = stay_result.get("stayRedPacketId")
        if red_packet_id is not None:
            return red_packet_id
    
    # 尝试从 data 中提取
    data = response.get("data")
    if isinstance(data, dict):
        red_packet_id = data.get("stayRedPacketId")
        if red_packet_id is not None:
            return red_packet_id
    
    # 尝试从响应顶层提取
    red_packet_id = response.get("stayRedPacketId")
    if red_packet_id is not None:
        return red_packet_id
    
    return None


def execute_send_coin_only(credential, amount, count, condition, distribute_type, delay, verbose=False, retry=1, retry_delay=1.0, jitter=0.3, room_id=None):
    """仅发送金币红包（向后兼容模式）"""
    stay_user_id = credential["stayUserId"]
    phone_number = credential["phone_number"]
    stay_token = credential["stayToken"]
    
    # 如果未指定 room_id，则使用 stayUserId 作为默认值
    actual_room_id = room_id if room_id is not None else stay_user_id
    
    last_failure = None
    for attempt in range(1, retry + 1):
        if delay and delay > 0:
            actual_delay = delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.1, actual_delay))

        if verbose and attempt > 1:
            logger.info("[RETRY %s/%s] %s (ID: %s)", attempt, retry, phone_number, stay_user_id)

        # 构建请求
        headers = build_business_headers(stay_token)
        url = f"{settings.BASE_URL}{SEND_COIN_RED_PACKET_PATH}"
        payload = {
            "roomId": actual_room_id,
            "totalAmount": amount,
            "totalCount": count,
            "claimCondition": condition,
            "distributeType": distribute_type,
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

        if is_success(response):
            if verbose:
                logger.info("[OK] %s (ID: %s) - 红包发送成功", phone_number, stay_user_id)
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
            "stage": "send_coin_red_packet",
            "response": response,
            "error_details": error_details,
            "attempt": attempt
        }
        
        if attempt < retry:
            actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.5, actual_retry_delay))

    return last_failure


def execute_send_coin_and_receive(credential, amount, count, condition, distribute_type, delay, verbose=False, retry=1, retry_delay=1.0, jitter=0.3, room_id=None):
    """执行单个金币红包发送 + 自动抢红包的串联任务"""
    stay_user_id = credential["stayUserId"]
    phone_number = credential["phone_number"]
    stay_token = credential["stayToken"]
    
    # 如果未指定 room_id，则使用 stayUserId 作为默认值
    actual_room_id = room_id if room_id is not None else stay_user_id
    
    last_failure = None
    for attempt in range(1, retry + 1):
        if delay and delay > 0:
            actual_delay = delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.1, actual_delay))

        if verbose and attempt > 1:
            logger.info("[RETRY %s/%s] %s (ID: %s)", attempt, retry, phone_number, stay_user_id)

        # ===== 步骤1: 发送金币红包 =====
        headers = build_business_headers(stay_token)
        send_url = f"{settings.BASE_URL}{SEND_COIN_RED_PACKET_PATH}"
        send_payload = {
            "roomId": actual_room_id,
            "totalAmount": amount,
            "totalCount": count,
            "claimCondition": condition,
            "distributeType": distribute_type,
        }

        send_response = HttpUtils.post(
            url=send_url,
            data=send_payload,
            headers=headers,
            encrypt_key=settings.TEST_ENCRYPT_KEY,
            locale="en",
            timestamp=str(int(time.time() * 1000)),
        )

        if not is_success(send_response):
            error_details = get_error_details(send_response)
            last_failure = {
                "phone": phone_number,
                "stayUserId": stay_user_id,
                "ok": False,
                "stage": "send_coin_red_packet",
                "response": send_response,
                "error_details": error_details,
                "attempt": attempt
            }
            if attempt < retry:
                actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
                time.sleep(max(0.5, actual_retry_delay))
            continue

        # ===== 步骤2: 从发红包响应中提取 stayRedPacketId =====
        red_packet_id = extract_stay_red_packet_id(send_response)
        if red_packet_id is None:
            last_failure = {
                "phone": phone_number,
                "stayUserId": stay_user_id,
                "ok": False,
                "stage": "extract_red_packet_id",
                "response": send_response,
                "error_details": "发红包响应中未找到 stayRedPacketId",
                "attempt": attempt
            }
            if attempt < retry:
                actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
                time.sleep(max(0.5, actual_retry_delay))
            continue

        if verbose:
            logger.info("[SEND_OK] %s (ID: %s) - 金币红包发送成功, stayRedPacketId=%s", phone_number, stay_user_id, red_packet_id)

        # ===== 步骤3: 使用提取到的 red_packet_id 抢红包 =====
        receive_url = f"{settings.BASE_URL}{RECEIVE_RED_PACKET_PATH}"
        receive_payload = {
            "redPacketId": red_packet_id
        }

        receive_response = HttpUtils.post(
            url=receive_url,
            data=receive_payload,
            headers=headers,
            encrypt_key=settings.TEST_ENCRYPT_KEY,
            locale="en",
            timestamp=str(int(time.time() * 1000)),
        )

        if is_success(receive_response):
            if verbose:
                logger.info("[OK] %s (ID: %s) - 发金币红包并抢红包成功, red_packet_id=%s", phone_number, stay_user_id, red_packet_id)
            return {
                "phone": phone_number,
                "stayUserId": stay_user_id,
                "ok": True,
                "red_packet_id": red_packet_id,
                "send_response": send_response,
                "receive_response": receive_response
            }

        # 抢红包失败
        error_details = get_error_details(receive_response)
        last_failure = {
            "phone": phone_number,
            "stayUserId": stay_user_id,
            "ok": False,
            "stage": "receive_red_packet",
            "red_packet_id": red_packet_id,
            "response": receive_response,
            "error_details": error_details,
            "attempt": attempt
        }
        
        if attempt < retry:
            actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.5, actual_retry_delay))

    return last_failure


def main():
    parser = argparse.ArgumentParser(description="多线程批量发送金币红包并自动抢红包（串联模式）")
    parser.add_argument("--workers", type=int, default=3, help="并发线程数，默认3")
    parser.add_argument("--delay", type=float, default=1.0, help="每个任务开始前等待秒数，默认1.0")
    parser.add_argument("--retry", type=int, default=2, help="每个用户最大重试次数，默认2")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="失败后重试前等待秒数，默认2.0")
    parser.add_argument("--jitter", type=float, default=0.3, help="随机抖动系数（0-1），默认0.3，用于避免规律请求")
    parser.add_argument("--verbose", action="store_true", help="是否打印每条成功日志")
    parser.add_argument("--start-index", type=int, default=0, help="从第几个用户开始，默认0")
    parser.add_argument("--max-count", type=int, default=0, help="最多发送多少个用户，默认0表示全部")
    
    # 红包参数
    parser.add_argument("--amount", type=int, default=20000, help="红包总金额（单位：分），默认20000")
    parser.add_argument("--count", type=int, default=1, help="红包个数，默认1")
    parser.add_argument("--condition", type=int, default=2, choices=[1, 2], help="领取条件：1-拼手气，2-普通，默认2")
    parser.add_argument("--distribute-type", type=int, default=1, choices=[1, 2], help="分发类型：1-即时，2-定时，默认1")
    
    # 房间ID参数
    parser.add_argument("--room-id", type=str, default=None, help="房间ID，默认使用每个用户的 stayUserId")
    
    # 抢红包控制
    parser.add_argument("--skip-receive", action="store_true", help="跳过抢红包步骤，仅发送红包（向后兼容）")
    
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

    if args.skip_receive:
        logger.info("开始批量发送金币红包（仅发送，跳过抢红包）: total=%s, workers=%s, delay=%s", total, args.workers, args.delay)
        task_func = execute_send_coin_only
    else:
        logger.info("开始批量发送金币红包并自动抢红包（串联模式）: total=%s, workers=%s, delay=%s", total, args.workers, args.delay)
        task_func = execute_send_coin_and_receive
    
    room_id_info = f", room_id={args.room_id}" if args.room_id else ", room_id=每个用户的stayUserId(默认)"
    logger.info("红包参数: amount=%s, count=%s, condition=%s, distribute-type=%s%s", args.amount, args.count, args.condition, args.distribute_type, room_id_info)

    success_count = 0
    failures = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_cred = {
            executor.submit(
                task_func,
                cred,
                args.amount,
                args.count,
                args.condition,
                args.distribute_type,
                args.delay,
                args.verbose,
                args.retry,
                args.retry_delay,
                args.jitter,
                args.room_id,
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
                logger.debug("        错误: %s", error_msg[:100])

    elapsed = time.time() - start_time
    logger.info("批量发送金币红包完成: 成功=%s/%s, 失败=%s, 耗时=%.1fs", success_count, total, len(failures), elapsed)
    
    # 清理当前线程的 Session 连接
    HttpUtils.close_session()
    
    if failures:
        logger.warning("失败用户列表 (手机号 - 用户ID - 阶段):")
        for fail in failures:
            logger.warning("  %s - %s stage=%s", fail['phone'], fail['stayUserId'], fail['stage'])


# 串联模式（发金币红包 + 自动抢红包）:
#   python batch_send_coin_red_packet.py --workers 5 --delay 0.5 --amount 20000 --count 5 --room-id 15712 
# 仅发送模式（向后兼容）:
#   python batch_send_coin_red_packet.py --workers 5 --delay 0.5 --amount 20000 --count 1 --skip-receive

if __name__ == "__main__":
    main()
