import argparse
import json
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


SEND_GIFT_RED_PACKET_PATH = "/payer/redPacket/send/gift"


def load_login_credentials():
    """从JSON文件加载登录凭证"""
    credentials_file = PROJECT_ROOT / "data" / "login_credentials.json"
    if not credentials_file.exists():
        print(f"错误: 登录凭证文件不存在: {credentials_file}")
        print("请先运行 batch_login.py --save-credentials 生成登录凭证")
        sys.exit(1)
    
    with credentials_file.open("r", encoding="utf-8") as f:
        credentials = json.load(f)
    
    # 转换为列表，每个元素包含手机号和凭证信息
    credential_list = []
    for stay_user_id, cred in credentials.items():
        credential_list.append({
            "stayUserId": stay_user_id,
            "phone_number": cred.get("phone_number", ""),
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


def execute_send_gift_red_packet(credential, room_id, gift_id, gift_count, total_amount, total_count, condition, distribute_type, delay, verbose=False, retry=1, retry_delay=1.0, jitter=0.3):
    """执行单个礼物红包发送任务"""
    stay_user_id = credential["stayUserId"]
    phone_number = credential["phone_number"]
    stay_token = credential["stayToken"]
    
    last_failure = None
    for attempt in range(1, retry + 1):
        if delay and delay > 0:
            # 添加随机抖动，避免请求过于规律
            actual_delay = delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.1, actual_delay))

        if verbose and attempt > 1:
            print(f"[RETRY {attempt}/{retry}] {phone_number} (ID: {stay_user_id})")

        # 构建请求
        headers = build_business_headers(stay_token)
        url = f"{settings.BASE_URL}{SEND_GIFT_RED_PACKET_PATH}"
        
        # 如果room_id为None，使用登录用户的ID作为roomId
        actual_room_id = room_id if room_id is not None else stay_user_id
        
        payload = {
            "roomId": actual_room_id,
            "giftId": gift_id,
            "giftCount": gift_count,
            "totalAmount": total_amount,
            "totalCount": total_count,
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
                print(f"[OK] {phone_number} (ID: {stay_user_id}) - 礼物红包发送成功")
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
            "stage": "send_gift_red_packet",
            "response": response,
            "error_details": error_details,
            "attempt": attempt
        }
        
        if attempt < retry:
            # 重试前等待
            actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.5, actual_retry_delay))

    return last_failure


def main():
    parser = argparse.ArgumentParser(description="多线程批量发送礼物红包")
    parser.add_argument("--workers", type=int, default=3, help="并发线程数，默认3")
    parser.add_argument("--delay", type=float, default=1.0, help="每个任务开始前等待秒数，默认1.0")
    parser.add_argument("--retry", type=int, default=2, help="每个用户最大重试次数，默认2")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="失败后重试前等待秒数，默认2.0")
    parser.add_argument("--jitter", type=float, default=0.3, help="随机抖动系数（0-1），默认0.3，用于避免规律请求")
    parser.add_argument("--verbose", action="store_true", help="是否打印每条成功日志")
    parser.add_argument("--start-index", type=int, default=0, help="从第几个用户开始，默认0")
    parser.add_argument("--max-count", type=int, default=0, help="最多发送多少个用户，默认0表示全部")
    
    # 礼物红包参数
    parser.add_argument("--room-id", type=str, default=None, help="房间ID，默认使用登录用户的ID")
    parser.add_argument("--gift-id", type=int, default=107, help="礼物ID，默认107")
    parser.add_argument("--gift-count", type=int, default=7, help="礼物数量，默认7")
    parser.add_argument("--total-amount", type=int, default=266, help="红包总金额，默认266")
    parser.add_argument("--total-count", type=int, default=5, help="红包个数，默认5")
    parser.add_argument("--condition", type=int, default=2, choices=[1, 2], help="领取条件：1-拼手气，2-普通，默认2")
    parser.add_argument("--distribute-type", type=int, default=1, choices=[1, 2], help="分发类型：1-即时，2-定时，默认1")
    
    args = parser.parse_args()

    # 加载登录凭证
    credentials = load_login_credentials()
    if args.max_count > 0:
        credentials = credentials[args.start_index : args.start_index + args.max_count]
    else:
        credentials = credentials[args.start_index:]

    total = len(credentials)
    if total == 0:
        print("没有找到可用的登录凭证，请检查 data/login_credentials.json")
        return

    print(f"开始批量发送礼物红包: total={total}, workers={args.workers}, delay={args.delay}")
    print(f"礼物红包参数: room-id={args.room_id}, gift-id={args.gift_id}, gift-count={args.gift_count}")
    print(f"红包参数: total-amount={args.total_amount}, total-count={args.total_count}, condition={args.condition}, distribute-type={args.distribute_type}")

    success_count = 0
    failures = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_cred = {
            executor.submit(
                execute_send_gift_red_packet,
                cred,
                args.room_id,
                args.gift_id,
                args.gift_count,
                args.total_amount,
                args.total_count,
                args.condition,
                args.distribute_type,
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
                print(f"[FAILED] {result['phone']} (ID: {result['stayUserId']}) stage={result['stage']} attempt={result.get('attempt', 1)}")
                print(f"        错误: {error_msg[:100]}...")

    elapsed = time.time() - start_time
    print("\n批量发送礼物红包完成")
    print(f"成功: {success_count}/{total}, 失败: {len(failures)}")
    print(f"总耗时: {elapsed:.1f}s")
    
    if failures:
        print("失败用户列表 (手机号 - 用户ID):")
        for fail in failures:
            print(f"  {fail['phone']} - {fail['stayUserId']} stage={fail['stage']}")


# 多线程批量发送礼物红包 python batch_send_gift_red_packet.py --workers 5 --delay 0.5 --gift-id 107 --gift-count 7 --total-amount 266 --total-count 5
# --workers 5：使用 5 个线程并发执行
# --delay 0.5：每个任务启动前等待 0.5 秒，避免请求过于密集
# --gift-id 107：礼物ID为 107
# --gift-count 7：礼物数量为 7
# --total-amount 266：红包总金额 266
# --total-count 5：红包个数为 5

if __name__ == "__main__":
    main()