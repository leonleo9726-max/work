#!/usr/bin/env python3
"""测试单线程登录，避免并发问题"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from batch_login import (
    load_csv_values,
    allocate_unique_ids,
    create_login_params,
    execute_login
)
from config import settings

def test_single_login():
    """测试单个手机号登录"""
    print("测试单线程登录...")
    print("=" * 60)
    
    # 加载数据
    phones = load_csv_values(PROJECT_ROOT / "data" / "login_phone.csv", "phone_number")
    unique_ids = load_csv_values(PROJECT_ROOT / "data" / "device_ids.csv", "uniqueId")
    
    if not phones:
        print("错误: 没有找到手机号")
        return
    
    # 只测试前3个手机号
    test_phones = phones[:3]
    test_cases = allocate_unique_ids(test_phones, unique_ids)
    
    print(f"测试 {len(test_cases)} 个手机号")
    print(f"使用设备ID: {unique_ids[:3] if unique_ids else '默认'}")
    print()
    
    success_count = 0
    for i, test_case in enumerate(test_cases):
        print(f"测试 {i+1}/{len(test_cases)}: {test_case['phone_number']}")
        print(f"  设备ID: {test_case['uniqueId']}")
        
        # 使用较长的延迟：3秒
        result = execute_login(
            test_case,
            settings.TEST_ENCRYPT_KEY,
            delay=3.0,  # 3秒延迟
            verbose=True,
            retry=2,
            retry_delay=5.0,
            jitter=0.2
        )
        
        if result["ok"]:
            success_count += 1
            print(f"  ✓ 登录成功")
            if result.get("login_info"):
                print(f"    stayUserId: {result['login_info']['stayUserId']}")
        else:
            print(f"  ✗ 登录失败")
            print(f"    阶段: {result['stage']}")
            print(f"    响应: {result['response']}")
        
        print()
        # 测试之间等待更长时间
        if i < len(test_cases) - 1:
            wait_time = 5.0
            print(f"等待 {wait_time} 秒后进行下一个测试...")
            time.sleep(wait_time)
    
    print("=" * 60)
    print(f"测试完成: 成功 {success_count}/{len(test_cases)}")
    
    # 建议的批量登录参数
    print("\n建议的批量登录参数:")
    print("1. 保守模式 (高成功率):")
    print("   python batch_login.py --workers 2 --delay 2.0 --retry 2 --retry-delay 3.0 --jitter 0.4")
    print()
    print("2. 平衡模式:")
    print("   python batch_login.py --workers 3 --delay 1.5 --retry 2 --retry-delay 2.5 --jitter 0.3")
    print()
    print("3. 快速模式 (可能有失败):")
    print("   python batch_login.py --workers 5 --delay 0.8 --retry 1 --retry-delay 1.5 --jitter 0.2")

if __name__ == "__main__":
    test_single_login()