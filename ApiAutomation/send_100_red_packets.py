#!/usr/bin/env python3
"""
单人发送100个红包的优化脚本
只需登录一次，使用同一个token发送100个红包
"""

import json
import time
import sys
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.http_utils import HttpUtils
from config import settings

SEND_COIN_RED_PACKET_PATH = "/payer/redPacket/send/coin"

def load_login_credentials():
    """从JSON文件加载登录凭证"""
    credentials_file = PROJECT_ROOT / "data" / "login_credentials.json"
    if not credentials_file.exists():
        print(f"错误: 登录凭证文件不存在: {credentials_file}")
        sys.exit(1)
    
    with credentials_file.open("r", encoding="utf-8") as f:
        credentials = json.load(f)
    
    # 获取第一个用户的凭证
    for stay_user_id, cred in credentials.items():
        return {
            "stayUserId": stay_user_id,
            "phone_number": cred.get("phone_number", ""),
            "stayToken": cred.get("stayToken", ""),
            "uniqueId": cred.get("uniqueId", "")
        }
    
    print("错误: 登录凭证文件中没有找到有效的用户凭证")
    sys.exit(1)

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

def send_single_red_packet(credential, amount, count, condition, distribute_type, packet_index):
    """发送单个红包"""
    stay_user_id = credential["stayUserId"]
    phone_number = credential["phone_number"]
    stay_token = credential["stayToken"]
    
    # 构建请求
    headers = build_business_headers(stay_token)
    url = f"{settings.BASE_URL}{SEND_COIN_RED_PACKET_PATH}"
    payload = {
        "roomId": stay_user_id,
        "totalAmount": amount,
        "totalCount": count,
        "claimCondition": condition,
        "distributeType": distribute_type,
    }
    
    print(f"[{packet_index:3d}/100] 发送红包: 用户 {phone_number} (ID: {stay_user_id})")
    print(f"        参数: amount={amount}, count={count}, condition={condition}, distribute-type={distribute_type}")
    
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
        print(f"[{packet_index:3d}/100] ✓ 发送成功")
        return True
    else:
        error_msg = response.get("message") or response.get("errorMessage") or response.get("msg") or "未知错误"
        print(f"[{packet_index:3d}/100] ✗ 发送失败: {error_msg}")
        return False

def main():
    """主函数：发送100个红包"""
    print("=" * 60)
    print("单人发送100个红包脚本")
    print("=" * 60)
    
    # 加载登录凭证（只加载一次）
    print("正在加载登录凭证...")
    credential = load_login_credentials()
    print(f"用户信息: {credential['phone_number']} (ID: {credential['stayUserId']})")
    print(f"Token前20位: {credential['stayToken'][:20]}...")
    
    # 红包参数（可以根据需要修改）
    amount = 20000      # 红包总金额（单位：分）
    count = 1           # 红包个数
    condition = 2       # 领取条件：2-普通
    distribute_type = 1 # 分发类型：1-即时
    
    print(f"\n红包参数:")
    print(f"  金额: {amount} 分")
    print(f"  个数: {count}")
    print(f"  领取条件: {condition} ({'拼手气' if condition == 1 else '普通'})")
    print(f"  分发类型: {distribute_type} ({'即时' if distribute_type == 1 else '定时'})")
    
    print(f"\n开始发送100个红包...")
    print("-" * 60)
    
    success_count = 0
    failure_count = 0
    start_time = time.time()
    
    for i in range(1, 31):
        try:
            success = send_single_red_packet(
                credential, 
                amount, 
                count, 
                condition, 
                distribute_type,
                i
            )
            
            if success:
                success_count += 1
            else:
                failure_count += 1
            
            # 添加延迟，避免请求过于频繁（可根据需要调整）
            if i < 100:  # 最后一个不需要等待
                time.sleep(0.5)  # 0.5秒延迟
            
        except Exception as e:
            print(f"[{i:3d}/100] ✗ 发送异常: {e}")
            failure_count += 1
            time.sleep(1)  # 异常后等待1秒
    
    elapsed_time = time.time() - start_time
    
    print("-" * 60)
    print("发送完成!")
    print(f"成功: {success_count}/100")
    print(f"失败: {failure_count}/100")
    print(f"总耗时: {elapsed_time:.1f}秒")
    print(f"平均每个红包: {elapsed_time/100:.2f}秒")
    
    if success_count == 100:
        print("✓ 所有100个红包发送成功!")
    else:
        print(f"⚠ 有{failure_count}个红包发送失败")
    
    return 0 if success_count > 0 else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n程序执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)