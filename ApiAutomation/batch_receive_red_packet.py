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


RECEIVE_RED_PACKET_PATH = "/payer/redPacket/receive"


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
    """判断抢红包是否成功"""
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
    
    # 抢红包可能有特殊错误码，但成功时通常有特定字段
    # 例如：红包已抢完、重复抢等不算成功
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


def is_red_packet_exhausted(response):
    """判断是否为红包已抢完的错误"""
    if not isinstance(response, dict):
        return False
    
    error_msg = str(response.get("stayErrorMessage", "")).lower()
    code = response.get("stayCode")
    
    # 根据实际错误码判断红包是否已抢完
    if code in (984003303, 984003304):  # 假设这些是红包相关的错误码
        return True
    if "exhausted" in error_msg or "抢完" in error_msg or "已领完" in error_msg:
        return True
    
    return False


def is_already_received(response):
    """判断是否为重复抢红包的错误"""
    if not isinstance(response, dict):
        return False
    
    error_msg = str(response.get("stayErrorMessage", "")).lower()
    code = response.get("stayCode")
    
    if "already" in error_msg or "重复" in error_msg or "已领取" in error_msg:
        return True
    
    return False


def execute_receive_red_packet(credential, red_packet_id, delay, verbose=False, retry=1, retry_delay=1.0, jitter=0.3):
    """执行单个抢红包任务"""
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
        url = f"{settings.BASE_URL}{RECEIVE_RED_PACKET_PATH}"
        payload = {
            "redPacketId": red_packet_id
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
                print(f"[OK] {phone_number} (ID: {stay_user_id}) - 抢红包成功")
            return {
                "phone": phone_number,
                "stayUserId": stay_user_id,
                "ok": True,
                "response": response
            }

        # 提取错误详情
        error_details = get_error_details(response)
        
        # 检查是否为红包已抢完或重复抢的错误
        if is_red_packet_exhausted(response):
            error_details = f"红包已抢完: {error_details}"
        elif is_already_received(response):
            error_details = f"重复抢红包: {error_details}"
        
        last_failure = {
            "phone": phone_number,
            "stayUserId": stay_user_id,
            "ok": False,
            "stage": "receive_red_packet",
            "response": response,
            "error_details": error_details,
            "attempt": attempt,
            "red_packet_exhausted": is_red_packet_exhausted(response),
            "already_received": is_already_received(response)
        }
        
        # 如果是红包已抢完，不再重试
        if is_red_packet_exhausted(response) or is_already_received(response):
            break
        
        if attempt < retry:
            # 重试前等待
            actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.5, actual_retry_delay))

    return last_failure


def main():
    parser = argparse.ArgumentParser(description="多线程批量抢红包")
    parser.add_argument("--workers", type=int, default=5, help="并发线程数，默认5（抢红包需要更高并发）")
    parser.add_argument("--delay", type=float, default=0.1, help="每个任务开始前等待秒数，默认0.1（抢红包需要快速并发）")
    parser.add_argument("--retry", type=int, default=1, help="每个用户最大重试次数，默认1（抢红包通常不需要重试）")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="失败后重试前等待秒数，默认1.0")
    parser.add_argument("--jitter", type=float, default=0.2, help="随机抖动系数（0-1），默认0.2，用于避免规律请求")
    parser.add_argument("--verbose", action="store_true", help="是否打印每条成功日志")
    parser.add_argument("--start-index", type=int, default=0, help="从第几个用户开始，默认0")
    parser.add_argument("--max-count", type=int, default=0, help="最多多少个用户参与抢红包，默认0表示全部")
    
    # 红包参数
    parser.add_argument("--red-packet-id", type=int, required=True, help="红包ID（必需参数）")
    parser.add_argument("--ignore-exhausted", action="store_true", help="忽略红包已抢完的错误，继续执行其他用户")
    parser.add_argument("--ignore-duplicate", action="store_true", help="忽略重复抢红包的错误，继续执行其他用户")
    
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

    print(f"开始批量抢红包: total={total}, workers={args.workers}, delay={args.delay}")
    print(f"红包ID: {args.red_packet_id}")
    print(f"忽略已抢完错误: {args.ignore_exhausted}, 忽略重复抢错误: {args.ignore_duplicate}")

    success_count = 0
    failures = []
    exhausted_count = 0
    duplicate_count = 0
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_cred = {
            executor.submit(
                execute_receive_red_packet,
                cred,
                args.red_packet_id,
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
                
                # 统计特殊错误
                if result.get("red_packet_exhausted"):
                    exhausted_count += 1
                if result.get("already_received"):
                    duplicate_count += 1
                
                # 根据参数决定是否打印错误
                should_print = True
                if args.ignore_exhausted and result.get("red_packet_exhausted"):
                    should_print = False
                if args.ignore_duplicate and result.get("already_received"):
                    should_print = False
                
                if should_print:
                    error_msg = result.get('error_details', str(result.get('response', '未知错误')))
                    print(f"[FAILED] {result['phone']} (ID: {result['stayUserId']}) stage={result['stage']} attempt={result.get('attempt', 1)}")
                    print(f"        错误: {error_msg[:100]}...")

    elapsed = time.time() - start_time
    print("\n批量抢红包完成")
    print(f"成功: {success_count}/{total}, 失败: {len(failures)}")
    print(f"  其中: 红包已抢完: {exhausted_count}, 重复抢: {duplicate_count}")
    print(f"总耗时: {elapsed:.1f}s")
    
    if failures and (not args.ignore_exhausted or not args.ignore_duplicate):
        print("失败用户列表 (手机号 - 用户ID - 错误类型):")
        for fail in failures:
            error_type = "普通错误"
            if fail.get("red_packet_exhausted"):
                error_type = "红包已抢完"
            elif fail.get("already_received"):
                error_type = "重复抢"
            print(f"  {fail['phone']} - {fail['stayUserId']} - {error_type}")


# 多线程批量抢红包 python batch_receive_red_packet.py --red-packet-id 123 --workers 10 --delay 0.05
# --red-packet-id 123：指定要抢的红包ID（必需）
# --workers 10：使用 10 个线程并发执行（模拟多人同时抢）
# --delay 0.05：每个任务启动前等待 0.05 秒，模拟几乎同时抢

if __name__ == "__main__":
    main()