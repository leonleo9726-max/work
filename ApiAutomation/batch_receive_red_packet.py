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
SEND_COIN_RED_PACKET_PATH = "/payer/redPacket/send/coin"
SEND_GIFT_RED_PACKET_PATH = "/payer/redPacket/send/gift"


def load_login_credentials():
    """从JSON文件加载登录凭证（优先加载 batch_login_credentials.json）"""
    # 优先使用 batch_login_credentials.json
    batch_file = PROJECT_ROOT / "data" / "batch_login_credentials.json"
    single_file = PROJECT_ROOT / "data" / "login_credentials.json"
    
    if batch_file.exists():
        credentials_file = batch_file
    elif single_file.exists():
        credentials_file = single_file
    else:
        print(f"错误: 登录凭证文件不存在")
        print(f"  请检查以下文件是否存在:")
        print(f"    - {batch_file}")
        print(f"    - {single_file}")
        print(f"请先运行 batch_login.py --save-credentials 生成登录凭证")
        sys.exit(1)
    
    with credentials_file.open("r", encoding="utf-8") as f:
        credentials = json.load(f)
    
    # 转换为列表，每个元素包含手机号和凭证信息
    credential_list = []
    for key, cred in credentials.items():
        # key 可能是手机号（batch_login_credentials.json）或 stayUserId（login_credentials.json）
        stay_user_id = cred.get("stayUserId", key)
        credential_list.append({
            "stayUserId": stay_user_id,
            "phone_number": cred.get("phone_number", key),
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
    if code in (984003303, 984003304):
        return True
    if "exhausted" in error_msg or "抢完" in error_msg or "已领完" in error_msg:
        return True
    
    return False


def is_already_received(response):
    """判断是否为重复抢红包的错误"""
    if not isinstance(response, dict):
        return False
    
    error_msg = str(response.get("stayErrorMessage", "")).lower()
    
    if "already" in error_msg or "重复" in error_msg or "已领取" in error_msg:
        return True
    
    return False


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


def execute_receive_red_packet(credential, red_packet_id, delay, verbose=False, retry=1, retry_delay=1.0, jitter=0.3):
    """执行单个抢红包任务（使用指定的红包ID）"""
    stay_user_id = credential["stayUserId"]
    phone_number = credential["phone_number"]
    stay_token = credential["stayToken"]
    
    last_failure = None
    for attempt in range(1, retry + 1):
        if delay and delay > 0:
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
            actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.5, actual_retry_delay))

    return last_failure


def execute_send_coin_only(credential, room_id, amount, count, condition, distribute_type, delay, verbose=False, retry=1, retry_delay=1.0, jitter=0.3):
    """仅发送金币红包，返回 red_packet_id（不抢红包）"""
    stay_user_id = credential["stayUserId"]
    phone_number = credential["phone_number"]
    stay_token = credential["stayToken"]
    
    actual_room_id = room_id if room_id is not None else stay_user_id
    
    for attempt in range(1, retry + 1):
        if delay and delay > 0:
            actual_delay = delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.1, actual_delay))

        if verbose and attempt > 1:
            print(f"[RETRY {attempt}/{retry}] {phone_number} (ID: {stay_user_id})")

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
            if verbose:
                print(f"[FAILED] {phone_number} (ID: {stay_user_id}) - 发金币红包失败: {error_details}")
            if attempt < retry:
                actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
                time.sleep(max(0.5, actual_retry_delay))
            continue

        red_packet_id = extract_stay_red_packet_id(send_response)
        if red_packet_id is None:
            if verbose:
                print(f"[FAILED] {phone_number} (ID: {stay_user_id}) - 发金币红包响应中未找到 stayRedPacketId")
            if attempt < retry:
                actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
                time.sleep(max(0.5, actual_retry_delay))
            continue

        if verbose:
            print(f"[SEND_OK] {phone_number} (ID: {stay_user_id}) - 金币红包发送成功, stayRedPacketId={red_packet_id}, count={count}")
        
        return {
            "ok": True,
            "phone": phone_number,
            "stayUserId": stay_user_id,
            "red_packet_id": red_packet_id,
            "send_response": send_response,
            "count": count,
        }

    return {
        "ok": False,
        "phone": phone_number,
        "stayUserId": stay_user_id,
        "stage": "send_coin_red_packet",
        "error_details": "发金币红包失败",
    }


def execute_send_gift_only(credential, room_id, gift_id, gift_count, total_amount, total_count, condition, distribute_type, delay, verbose=False, retry=1, retry_delay=1.0, jitter=0.3):
    """仅发送礼物红包，返回 red_packet_id（不抢红包）"""
    stay_user_id = credential["stayUserId"]
    phone_number = credential["phone_number"]
    stay_token = credential["stayToken"]
    
    actual_room_id = room_id if room_id is not None else stay_user_id
    
    for attempt in range(1, retry + 1):
        if delay and delay > 0:
            actual_delay = delay * (1 + random.uniform(-jitter, jitter))
            time.sleep(max(0.1, actual_delay))

        if verbose and attempt > 1:
            print(f"[RETRY {attempt}/{retry}] {phone_number} (ID: {stay_user_id})")

        headers = build_business_headers(stay_token)
        send_url = f"{settings.BASE_URL}{SEND_GIFT_RED_PACKET_PATH}"
        send_payload = {
            "roomId": actual_room_id,
            "giftId": gift_id,
            "giftCount": gift_count,
            "totalAmount": total_amount,
            "totalCount": total_count,
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
            if verbose:
                print(f"[FAILED] {phone_number} (ID: {stay_user_id}) - 发礼物红包失败: {error_details}")
            if attempt < retry:
                actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
                time.sleep(max(0.5, actual_retry_delay))
            continue

        red_packet_id = extract_stay_red_packet_id(send_response)
        if red_packet_id is None:
            if verbose:
                print(f"[FAILED] {phone_number} (ID: {stay_user_id}) - 发礼物红包响应中未找到 stayRedPacketId")
            if attempt < retry:
                actual_retry_delay = retry_delay * (1 + random.uniform(-jitter, jitter))
                time.sleep(max(0.5, actual_retry_delay))
            continue

        if verbose:
            print(f"[SEND_OK] {phone_number} (ID: {stay_user_id}) - 礼物红包发送成功, stayRedPacketId={red_packet_id}, total_count={total_count}")
        
        return {
            "ok": True,
            "phone": phone_number,
            "stayUserId": stay_user_id,
            "red_packet_id": red_packet_id,
            "send_response": send_response,
            "total_count": total_count,
        }

    return {
        "ok": False,
        "phone": phone_number,
        "stayUserId": stay_user_id,
        "stage": "send_gift_red_packet",
        "error_details": "发礼物红包失败",
    }




def main():
    parser = argparse.ArgumentParser(description="多线程批量抢红包（支持直接抢、先发金币红包再抢、先发礼物红包再抢）")
    parser.add_argument("--workers", type=int, default=5, help="并发线程数，默认5（抢红包需要更高并发）")
    parser.add_argument("--delay", type=float, default=0.1, help="每个任务开始前等待秒数，默认0.1（抢红包需要快速并发）")
    parser.add_argument("--retry", type=int, default=1, help="每个用户最大重试次数，默认1（抢红包通常不需要重试）")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="失败后重试前等待秒数，默认1.0")
    parser.add_argument("--jitter", type=float, default=0.2, help="随机抖动系数（0-1），默认0.2，用于避免规律请求")
    parser.add_argument("--verbose", action="store_true", help="是否打印每条成功日志")
    parser.add_argument("--start-index", type=int, default=0, help="从第几个用户开始，默认0")
    parser.add_argument("--max-count", type=int, default=0, help="最多多少个用户参与抢红包，默认0表示全部")
    
    # 红包参数（直接抢模式）
    parser.add_argument("--red-packet-id", type=int, help="红包ID（直接抢模式使用）")
    parser.add_argument("--ignore-exhausted", action="store_true", help="忽略红包已抢完的错误，继续执行其他用户")
    parser.add_argument("--ignore-duplicate", action="store_true", help="忽略重复抢红包的错误，继续执行其他用户")
    
    # 串联模式：先发金币红包再抢
    parser.add_argument("--send-coin", action="store_true", help="先发金币红包，从响应提取 stayRedPacketId 再抢（串联模式）")
    parser.add_argument("--amount", type=int, default=20000, help="金币红包总金额（单位：分），默认20000")
    parser.add_argument("--count", type=int, default=1, help="金币红包个数，默认1")
    parser.add_argument("--condition", type=int, default=2, choices=[1, 2], help="领取条件：1-拼手气，2-普通，默认2")
    parser.add_argument("--distribute-type", type=int, default=1, choices=[1, 2], help="分发类型：1-即时，2-定时，默认1")
    
    # 串联模式：先发礼物红包再抢
    parser.add_argument("--send-gift", action="store_true", help="先发礼物红包，从响应提取 stayRedPacketId 再抢（串联模式）")
    parser.add_argument("--room-id", type=str, default=None, help="房间ID，默认使用登录用户的ID（同时适用于 --send-coin 和 --send-gift 模式）")
    parser.add_argument("--gift-id", type=int, default=107, help="礼物ID，默认107")
    parser.add_argument("--gift-count", type=int, default=7, help="礼物数量，默认7")
    parser.add_argument("--total-amount", type=int, default=266, help="红包总金额，默认266")
    parser.add_argument("--total-count", type=int, default=5, help="红包个数，默认5")
    
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

    # 确定运行模式
    if args.send_coin:
        # ===== 串联模式：每个用户发一个红包，被随机5人抢完 =====
        print(f"开始发金币红包并随机抢红包（串联模式）: total={total}, workers={args.workers}, delay={args.delay}")
        print(f"金币红包参数: room-id={args.room_id}, amount={args.amount}, count={args.count}, condition={args.condition}, distribute-type={args.distribute_type}")
        
        if total < 6:
            print("错误: 串联模式至少需要6个用户（1个发红包 + 5个抢红包）")
            sys.exit(1)
        
        # 每个用户发一个红包，每个红包被随机5人抢
        # 注意：--count 表示每个红包的个数（发给多少人），这里固定为5
        # 但用户可能传 --count 5，我们内部固定每个红包发5个
        red_packet_count_per_user = 5  # 每个红包被5个人抢
        
        start_time = time.time()
        total_send_success = 0
        total_receive_success = 0
        total_receive_failures = []
        
        for sender_idx, sender_cred in enumerate(credentials):
            print(f"\n--- 用户 {sender_idx + 1}/{total}: {sender_cred['phone_number']} (ID: {sender_cred['stayUserId']}) 发红包 ---")
            
            # 步骤1: 当前用户发红包（固定发5个）
            send_result = execute_send_coin_only(
                sender_cred, args.room_id, args.amount, red_packet_count_per_user, args.condition, args.distribute_type,
                args.delay, args.verbose, args.retry, args.retry_delay, args.jitter
            )
            
            if not send_result["ok"]:
                print(f"  [FAILED] 发红包失败: {send_result.get('error_details', '未知错误')}")
                total_receive_failures.append(send_result)
                continue
            
            red_packet_id = send_result["red_packet_id"]
            total_send_success += 1
            print(f"  [SEND_OK] 红包发送成功, red_packet_id={red_packet_id}")
            
            # 步骤2: 从所有用户中随机选5个不同的用户抢红包（排除发红包者自己）
            other_credentials = [c for i, c in enumerate(credentials) if i != sender_idx]
            selected_receivers = random.sample(other_credentials, min(red_packet_count_per_user, len(other_credentials)))
            
            print(f"  [RECEIVE] 随机选 {len(selected_receivers)} 个用户抢红包...")
            
            # 并发抢红包
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                future_to_receiver = {
                    executor.submit(
                        execute_receive_red_packet,
                        receiver_cred,
                        red_packet_id,
                        args.delay,
                        args.verbose,
                        args.retry,
                        args.retry_delay,
                        args.jitter,
                    ): receiver_cred
                    for receiver_cred in selected_receivers
                }
                for future in as_completed(future_to_receiver):
                    result = future.result()
                    if result["ok"]:
                        total_receive_success += 1
                    else:
                        total_receive_failures.append(result)
                        error_msg = result.get('error_details', str(result.get('response', '未知错误')))
                        print(f"    [FAILED] {result['phone']} (ID: {result['stayUserId']}) 抢红包失败: {error_msg[:80]}...")
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*50}")
        print(f"全部完成!")
        print(f"  发红包成功: {total_send_success}/{total}")
        print(f"  抢红包成功: {total_receive_success}/{total_send_success * red_packet_count_per_user}")
        print(f"  抢红包失败: {len(total_receive_failures)}")
        print(f"  总耗时: {elapsed:.1f}s")
        return
        
    elif args.send_gift:
        # ===== 串联模式：每个用户发一个礼物红包，被随机5人抢完 =====
        print(f"开始发礼物红包并随机抢红包（串联模式）: total={total}, workers={args.workers}, delay={args.delay}")
        print(f"礼物红包参数: room-id={args.room_id}, gift-id={args.gift_id}, gift-count={args.gift_count}")
        print(f"红包参数: total-amount={args.total_amount}, total-count={args.total_count}, condition={args.condition}, distribute-type={args.distribute_type}")
        
        if total < 6:
            print("错误: 串联模式至少需要6个用户（1个发红包 + 5个抢红包）")
            sys.exit(1)
        
        red_packet_count_per_user = 5  # 每个红包被5个人抢
        
        start_time = time.time()
        total_send_success = 0
        total_receive_success = 0
        total_receive_failures = []
        
        for sender_idx, sender_cred in enumerate(credentials):
            print(f"\n--- 用户 {sender_idx + 1}/{total}: {sender_cred['phone_number']} (ID: {sender_cred['stayUserId']}) 发红包 ---")
            
            # 步骤1: 当前用户发礼物红包（固定发5个）
            send_result = execute_send_gift_only(
                sender_cred, args.room_id, args.gift_id, args.gift_count, args.total_amount, red_packet_count_per_user,
                args.condition, args.distribute_type,
                args.delay, args.verbose, args.retry, args.retry_delay, args.jitter
            )
            
            if not send_result["ok"]:
                print(f"  [FAILED] 发红包失败: {send_result.get('error_details', '未知错误')}")
                total_receive_failures.append(send_result)
                continue
            
            red_packet_id = send_result["red_packet_id"]
            total_send_success += 1
            print(f"  [SEND_OK] 红包发送成功, red_packet_id={red_packet_id}")
            
            # 步骤2: 从所有用户中随机选5个不同的用户抢红包（排除发红包者自己）
            other_credentials = [c for i, c in enumerate(credentials) if i != sender_idx]
            selected_receivers = random.sample(other_credentials, min(red_packet_count_per_user, len(other_credentials)))
            
            print(f"  [RECEIVE] 随机选 {len(selected_receivers)} 个用户抢红包...")
            
            # 并发抢红包
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                future_to_receiver = {
                    executor.submit(
                        execute_receive_red_packet,
                        receiver_cred,
                        red_packet_id,
                        args.delay,
                        args.verbose,
                        args.retry,
                        args.retry_delay,
                        args.jitter,
                    ): receiver_cred
                    for receiver_cred in selected_receivers
                }
                for future in as_completed(future_to_receiver):
                    result = future.result()
                    if result["ok"]:
                        total_receive_success += 1
                    else:
                        total_receive_failures.append(result)
                        error_msg = result.get('error_details', str(result.get('response', '未知错误')))
                        print(f"    [FAILED] {result['phone']} (ID: {result['stayUserId']}) 抢红包失败: {error_msg[:80]}...")
        
        elapsed = time.time() - start_time
        
        print(f"\n{'='*50}")
        print(f"全部完成!")
        print(f"  发红包成功: {total_send_success}/{total}")
        print(f"  抢红包成功: {total_receive_success}/{total_send_success * red_packet_count_per_user}")
        print(f"  抢红包失败: {len(total_receive_failures)}")
        print(f"  总耗时: {elapsed:.1f}s")
        return
        
    else:
        # 直接抢模式（需要 --red-packet-id）
        if args.red_packet_id is None:
            print("错误: 直接抢模式需要指定 --red-packet-id 参数")
            print("或者使用 --send-coin 或 --send-gift 进入串联模式（自动发红包并抢）")
            sys.exit(1)
        
        print(f"开始批量抢红包（直接抢模式）: total={total}, workers={args.workers}, delay={args.delay}")
        print(f"红包ID: {args.red_packet_id}")
        print(f"忽略已抢完错误: {args.ignore_exhausted}, 忽略重复抢错误: {args.ignore_duplicate}")
        
        receive_credentials = credentials
        task_func = execute_receive_red_packet
        task_args = (args.red_packet_id,)

        success_count = 0
        failures = []
        exhausted_count = 0
        duplicate_count = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_cred = {
                executor.submit(
                    task_func,
                    cred,
                    *task_args,
                    args.delay,
                    args.verbose,
                    args.retry,
                    args.retry_delay,
                    args.jitter,
                ): cred
                for cred in receive_credentials
            }
            for future in as_completed(future_to_cred):
                result = future.result()
                if result["ok"]:
                    success_count += 1
                else:
                    failures.append(result)
                    
                    # 统计特殊错误（仅直接抢模式）
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
        print(f"  其中: 红包已抢完: {exhausted_count}, 重复抢: {duplicate_count}")
        print(f"成功: {success_count}/{len(receive_credentials)}, 失败: {len(failures)}")
        print(f"总耗时: {elapsed:.1f}s")
        
        if failures:
            print("失败用户列表 (手机号 - 用户ID - 阶段):")
            for fail in failures:
                error_type = ""
                if fail.get("red_packet_exhausted"):
                    error_type = " (红包已抢完)"
                elif fail.get("already_received"):
                    error_type = " (重复抢)"
                print(f"  {fail['phone']} - {fail['stayUserId']} stage={fail['stage']}{error_type}")


# 直接抢模式（需要指定红包ID）:
#   python batch_receive_red_packet.py --red-packet-id 123 --workers 10 --delay 0.05
# 串联模式（先发金币红包再抢）:
#   python batch_receive_red_packet.py --send-coin --workers 5 --delay 0.5 --amount 20000 --count 1
#   python batch_receive_red_packet.py --send-coin --room-id "你的固定房间ID" --amount 20000 --count 1


# 固定房间，每个用户发金币红包，被随机5人抢完
#   python batch_receive_red_packet.py --send-coin --room-id "固定的房间ID" --amount 20000

# 礼物红包模式
#   python batch_receive_red_packet.py --send-gift --room-id "固定的房间ID" --gift-id 107 --gift-count 7 --total-amount 266




if __name__ == "__main__":
    main()
