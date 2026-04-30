"""
抢红包测试模块。

支持多种测试场景：
1. 使用已知红包 ID 抢红包
2. 先发金币红包再抢（自动提取红包 ID）
3. 先发礼物红包再抢（自动提取红包 ID）
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import pytest

# conftest.py 已处理 sys.path
from common.api_paths import RECEIVE_RED_PACKET_PATH, SEND_COIN_RED_PACKET_PATH, SEND_GIFT_RED_PACKET_PATH
from common.auth_utils import build_business_headers_from_login
from common.http_utils import HttpUtils
from common.response_utils import (
    extract_error_message,
    extract_stay_red_packet_id,
    is_api_success,
)
from config import settings

logger = logging.getLogger(__name__)


def receive_red_packet(headers, credential, red_packet_id):
    """抢红包的辅助函数"""
    url = f"{settings.BASE_URL}{RECEIVE_RED_PACKET_PATH}"

    payload = {
        "redPacketId": red_packet_id
    }

    logger.info(f"发送请求到: {url}")
    logger.info(f"请求参数: {payload}")

    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )

    logger.info(f"完整响应: {response}")

    if response is None:
        raise AssertionError("抢红包接口未返回有效响应")
    if not isinstance(response, dict):
        raise AssertionError("抢红包接口返回值应为 JSON 对象")

    return response


def send_coin_red_packet(headers, credential, total_amount=20000, total_count=1, claim_condition=2, distribute_type=1):
    """发送金币红包的辅助函数"""
    url = f"{settings.BASE_URL}{SEND_COIN_RED_PACKET_PATH}"

    payload = {
        "roomId": credential["stayUserId"],
        "totalAmount": total_amount,
        "totalCount": total_count,
        "claimCondition": claim_condition,
        "distributeType": distribute_type,
    }

    logger.info(f"发送请求到: {url}")
    logger.info(f"请求参数: {payload}")

    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )

    logger.info(f"完整响应: {response}")

    if response is None:
        raise AssertionError("发送金币红包接口未返回有效响应")
    if not isinstance(response, dict):
        raise AssertionError("发送金币红包接口返回值应为 JSON 对象")

    return response


def send_gift_red_packet(headers, credential, gift_id=107, gift_count=7, total_amount=266, total_count=5, claim_condition=2, distribute_type=1):
    """发送礼物红包的辅助函数"""
    url = f"{settings.BASE_URL}{SEND_GIFT_RED_PACKET_PATH}"

    payload = {
        "roomId": credential["stayUserId"],
        "giftId": gift_id,
        "giftCount": gift_count,
        "totalAmount": total_amount,
        "totalCount": total_count,
        "claimCondition": claim_condition,
        "distributeType": distribute_type,
    }

    logger.info(f"发送请求到: {url}")
    logger.info(f"请求参数: {payload}")

    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )

    logger.info(f"完整响应: {response}")

    if response is None:
        raise AssertionError("发送礼物红包接口未返回有效响应")
    if not isinstance(response, dict):
        raise AssertionError("发送礼物红包接口返回值应为 JSON 对象")

    return response


def check_response_success(response, context="操作"):
    """检查接口响应是否成功，失败时抛出 pytest.fail"""
    if not is_api_success(response):
        error_message = extract_error_message(response)
        pytest.fail(f"{context}失败: {error_message}, 完整响应: {response}")
    return True


@pytest.mark.api
@pytest.mark.parametrize(
    "phone_number,red_packet_id",
    [
        ("15200711073", 1),  # 默认红包ID测试
        ("13710011001", 2),  # 自定义红包ID测试
    ],
    ids=["default_receive", "custom_receive"],
)
def test_receive_red_packet(request, phone_number, red_packet_id):
    """抢红包接口测试，从 login_credentials.json 读取登录凭证。

    注意：此测试使用硬编码的 red_packet_id，适用于已知红包ID的场景。
    推荐使用 test_send_coin_then_receive 或 test_send_gift_then_receive，
    它们会先发红包再抢，自动从发红包响应中提取 stayRedPacketId。
    """
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    assert credential["stayToken"], "读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "读取到的 stayUserId 不能为空"

    token = credential["stayToken"]
    logger.info(f"用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    response = receive_red_packet(headers, credential, red_packet_id)
    check_response_success(response, "抢红包")

    logger.info(f"用户 {credential['stayUserId']} 抢红包成功，红包ID: {red_packet_id}，响应: {response}")


@pytest.mark.api
@pytest.mark.parametrize(
    "phone_number,total_amount,total_count,claim_condition,distribute_type",
    [
        ("15200711073", 20000, 1, 2, 1),  # 默认值测试
        ("13710011001", 10000, 5, 1, 2),  # 自定义值测试
    ],
    ids=["coin_default_receive", "coin_custom_receive"],
)
def test_send_coin_then_receive(request, phone_number, total_amount, total_count, claim_condition, distribute_type):
    """先发送金币红包，再从响应中提取 stayRedPacketId，然后用该 ID 抢红包。"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    # 1. 获取登录凭证
    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    assert credential["stayToken"], "读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "读取到的 stayUserId 不能为空"

    token = credential["stayToken"]
    logger.info(f"用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    # 2. 发送金币红包
    logger.info("步骤1: 发送金币红包...")
    send_response = send_coin_red_packet(
        headers, credential,
        total_amount=total_amount,
        total_count=total_count,
        claim_condition=claim_condition,
        distribute_type=distribute_type,
    )
    check_response_success(send_response, "发送金币红包")

    # 3. 从响应中提取 stayRedPacketId
    red_packet_id = extract_stay_red_packet_id(send_response)
    assert red_packet_id is not None, (
        f"发送金币红包响应中未找到 stayRedPacketId，完整响应: {send_response}"
    )
    logger.info(f"步骤2: 从发红包响应中提取到 stayRedPacketId = {red_packet_id}")

    # 4. 使用提取到的 red_packet_id 抢红包
    logger.info(f"步骤3: 使用 red_packet_id={red_packet_id} 抢红包...")
    receive_response = receive_red_packet(headers, credential, red_packet_id)
    check_response_success(receive_response, "抢红包")

    logger.info(f"用户 {credential['stayUserId']} 发金币红包并抢红包成功，"
                f"red_packet_id={red_packet_id}，抢红包响应: {receive_response}")


@pytest.mark.api
@pytest.mark.parametrize(
    "phone_number,gift_id,gift_count,total_amount,total_count,claim_condition,distribute_type",
    [
        ("15200711073", 107, 7, 266, 5, 2, 1),  # 默认值测试
        ("13710011001", 107, 10, 500, 3, 2, 1),  # 自定义值测试
    ],
    ids=["gift_default_receive", "gift_custom_receive"],
)
def test_send_gift_then_receive(request, phone_number, gift_id, gift_count, total_amount, total_count, claim_condition, distribute_type):
    """先发送礼物红包，再从响应中提取 stayRedPacketId，然后用该 ID 抢红包。"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    # 1. 获取登录凭证
    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    assert credential["stayToken"], "读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "读取到的 stayUserId 不能为空"

    token = credential["stayToken"]
    logger.info(f"用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    # 2. 发送礼物红包
    logger.info("步骤1: 发送礼物红包...")
    send_response = send_gift_red_packet(
        headers, credential,
        gift_id=gift_id,
        gift_count=gift_count,
        total_amount=total_amount,
        total_count=total_count,
        claim_condition=claim_condition,
        distribute_type=distribute_type,
    )
    check_response_success(send_response, "发送礼物红包")

    # 3. 从响应中提取 stayRedPacketId
    red_packet_id = extract_stay_red_packet_id(send_response)
    assert red_packet_id is not None, (
        f"发送礼物红包响应中未找到 stayRedPacketId，完整响应: {send_response}"
    )
    logger.info(f"步骤2: 从发红包响应中提取到 stayRedPacketId = {red_packet_id}")

    # 4. 使用提取到的 red_packet_id 抢红包
    logger.info(f"步骤3: 使用 red_packet_id={red_packet_id} 抢红包...")
    receive_response = receive_red_packet(headers, credential, red_packet_id)
    check_response_success(receive_response, "抢红包")

    logger.info(f"用户 {credential['stayUserId']} 发礼物红包并抢红包成功，"
                f"red_packet_id={red_packet_id}，抢红包响应: {receive_response}")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="抢红包测试")
    parser.add_argument("--phone", type=str, default="15200711073",
                        help="手机号码，默认: 15200711073")
    parser.add_argument("--red-packet-id", type=int, default=1,
                        help="红包ID，默认: 1")
    parser.add_argument("--run-api", action="store_true",
                        help="执行真实API测试（需要此参数才会调用接口）")
    parser.add_argument("--verbose", action="store_true",
                        help="打印详细日志")
    return parser.parse_args()


def _receive_red_packet_direct(phone_number, red_packet_id):
    """直接运行模式下的抢红包函数"""
    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    if not credential.get("stayToken") or not credential.get("stayUserId"):
        print(f"错误: 用户 {phone_number} 登录凭证无效")
        sys.exit(1)

    token = credential["stayToken"]
    print(f"[直接运行] 用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    url = f"{settings.BASE_URL}{RECEIVE_RED_PACKET_PATH}"
    payload = {
        "redPacketId": red_packet_id
    }

    print(f"[直接运行] 抢红包参数: {payload}")
    print(f"[直接运行] 请求URL: {url}")

    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )

    print(f"[直接运行] 完整响应: {response}")

    if is_api_success(response):
        print(f"[直接运行] 抢红包成功")
        return True
    else:
        return False


if __name__ == "__main__":
    args = parse_args()
    print(f"[命令行参数] phone={args.phone}, red-packet-id={args.red_packet_id}, "
          f"run-api={args.run_api}, verbose={args.verbose}")

    if not args.run_api:
        print("警告: 需要 --run-api 参数才会执行真实API测试")
        print("示例: python tests/test_receive_red_packet.py --run-api --phone 15200711073 --red-packet-id 1")
        sys.exit(0)

    success = _receive_red_packet_direct(
        phone_number=args.phone,
        red_packet_id=args.red_packet_id,
    )

    if success:
        print("[直接运行] 测试通过")
        sys.exit(0)
    else:
        print("[直接运行] 测试失败")
        sys.exit(1)
