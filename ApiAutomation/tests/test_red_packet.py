import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from common.http_utils import HttpUtils
from config import settings
from tests.test_login_phone import build_business_headers_from_login


SEND_COIN_RED_PACKET_PATH = "/redPacket/send/coin"


@pytest.mark.api
@pytest.mark.parametrize(
    "phone_number,total_amount,total_count,claim_condition,distribute_type",
    [
        ("15200711073", 20000, 1, 2, 1),  # 默认值测试
        ("13710011001", 10000, 5, 1, 2),  # 自定义值测试
    ],
    ids=["default_red_packet", "custom_red_packet"],
)
def test_send_coin_red_packet(request, phone_number, total_amount, total_count, claim_condition, distribute_type):
    """发送金币红包接口测试，从 login_credentials.json 读取登录凭证。"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    assert credential["stayToken"], "读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "读取到的 stayUserId 不能为空"

    # 记录请求头中的 token
    token = credential["stayToken"]
    print(f"[send_coin_red_packet] 用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    url = f"{settings.BASE_URL}{SEND_COIN_RED_PACKET_PATH}"
    payload = {
        "roomId": credential["stayUserId"],  # 使用登录的 userid 作为 roomId
        "totalAmount": total_amount,
        "totalCount": total_count,
        "claimCondition": claim_condition,
        "distributeType": distribute_type,
    }

    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )

    assert response is not None, "发送金币红包接口未返回有效响应"
    assert isinstance(response, dict), "发送金币红包接口返回值应为 JSON 对象"

    # 检查响应是否成功（可根据实际接口调整）
    success = (
        response.get("code") == 0
        or response.get("stayCode") == 0
        or response.get("success") is True
        or response.get("status") == "success"
    )

    if not success:
        error_message = (
            response.get("message")
            or response.get("errorMessage")
            or response.get("msg")
            or "未知错误"
        )
        pytest.fail(f"发送金币红包失败: {error_message}, 响应: {response}")

    print(f"[send_coin_red_packet] 用户 {credential['stayUserId']} 发送红包，参数: {payload}，响应: {response}")


@pytest.mark.api
def test_login_then_send_red_packet(request, encrypt_key):
    """先执行登录，再自动发送金币红包。"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    phone_number = "15200711073"
    from tests.test_login_phone import ensure_login_credentials

    credential = ensure_login_credentials(phone_number, encrypt_key)
    assert credential["stayToken"], "登录后读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "登录后读取到的 stayUserId 不能为空"

    # 记录请求头中的 token
    token = credential["stayToken"]
    print(f"[login_then_send] 用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    url = f"{settings.BASE_URL}{SEND_COIN_RED_PACKET_PATH}"
    payload = {
        "roomId": credential["stayUserId"],
        "totalAmount": 20000,
        "totalCount": 1,
        "claimCondition": 2,
        "distributeType": 1,
    }

    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=settings.build_common_encrypted_headers() | {"Authorization": f"Bearer {credential['stayToken']}"},
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )

    assert response is not None, "发送金币红包接口未返回有效响应"
    assert isinstance(response, dict), "发送金币红包接口返回值应为 JSON 对象"

    success = (
        response.get("code") == 0
        or response.get("stayCode") == 0
        or response.get("success") is True
        or response.get("status") == "success"
    )
    if not success:
        error_message = (
            response.get("message")
            or response.get("errorMessage")
            or response.get("msg")
            or "未知错误"
        )
        pytest.fail(f"登录并发送红包失败: {error_message}, 响应: {response}")

    print(f"[login_then_send] 用户 {credential['stayUserId']} 登录并发送红包成功，响应: {response}")


@pytest.mark.api
def test_batch_send_red_packets(request):
    """批量发送金币红包测试"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    phone_numbers = ["15200711073", "13710011001"]
    results = {}

    for phone in phone_numbers:
        try:
            headers, credential = build_business_headers_from_login(phone_number=phone)
            assert credential["stayToken"], f"用户 {phone} 的 stayToken 不能为空"
            assert credential["stayUserId"], f"用户 {phone} 的 stayUserId 不能为空"

            # 记录请求头中的 token
            token = credential["stayToken"]
            print(f"[batch_red_packet] 用户 {phone} (ID: {credential['stayUserId']}) 的 token: {token[:20]}... (长度: {len(token)})")

            url = f"{settings.BASE_URL}{SEND_COIN_RED_PACKET_PATH}"
            payload = {
                "roomId": credential["stayUserId"],
                "totalAmount": 20000,
                "totalCount": 1,
                "claimCondition": 2,
                "distributeType": 1,
            }

            response = HttpUtils.post(
                url=url,
                data=payload,
                headers=headers,
                encrypt_key=settings.TEST_ENCRYPT_KEY,
                locale="en",
                timestamp=str(int(time.time() * 1000)),
            )

            assert response is not None, f"用户 {phone} 发送金币红包接口未返回有效响应"
            assert isinstance(response, dict), f"用户 {phone} 发送金币红包接口返回值应为 JSON 对象"

            success = (
                response.get("code") == 0
                or response.get("stayCode") == 0
                or response.get("success") is True
                or response.get("status") == "success"
            )

            if success:
                results[phone] = {"success": True, "response": response}
                print(f"[batch_red_packet] {phone} 发送成功: {response}")
            else:
                error_message = (
                    response.get("message")
                    or response.get("errorMessage")
                    or response.get("msg")
                    or "未知错误"
                )
                results[phone] = {"success": False, "error": error_message}
                print(f"[batch_red_packet] {phone} 发送失败: {error_message}")

        except Exception as e:
            results[phone] = {"success": False, "error": str(e)}
            print(f"[batch_red_packet] {phone} 发送异常: {e}")

        time.sleep(1)  # 避免请求过于频繁

    # 至少有一个成功
    successful_sends = sum(1 for result in results.values() if result["success"])
    assert successful_sends > 0, f"批量发送失败，所有结果: {results}"


def parse_args():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(description="发送金币红包测试")
    parser.add_argument("--phone", type=str, default="15200711073",
                       help="手机号码，默认: 15200711073")
    parser.add_argument("--amount", type=int, default=20000,
                       help="红包总金额（单位：分），默认: 20000")
    parser.add_argument("--count", type=int, default=1,
                       help="红包个数，默认: 1")
    parser.add_argument("--condition", type=int, default=2, choices=[1, 2],
                       help="领取条件：1-拼手气，2-普通，默认: 2")
    parser.add_argument("--distribute-type", type=int, default=1, choices=[1, 2],
                       help="分发类型：1-即时，2-定时，默认: 1")
    parser.add_argument("--run-api", action="store_true",
                       help="执行真实API测试（需要此参数才会调用接口）")
    parser.add_argument("--verbose", action="store_true",
                       help="打印详细日志")
    return parser.parse_args()


def _send_red_packet_direct(phone_number, total_amount, total_count, claim_condition, distribute_type):
    """直接运行模式下的红包发送函数"""
    import sys
    from tests.test_login_phone import build_business_headers_from_login
    from config import settings
    from common.http_utils import HttpUtils
    import time
    
    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    if not credential.get("stayToken") or not credential.get("stayUserId"):
        print(f"错误: 用户 {phone_number} 登录凭证无效")
        sys.exit(1)
    
    # 记录请求头中的 token
    token = credential["stayToken"]
    print(f"[直接运行] 用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")
    
    url = f"{settings.BASE_URL}{SEND_COIN_RED_PACKET_PATH}"
    payload = {
        "roomId": credential["stayUserId"],
        "totalAmount": total_amount,
        "totalCount": total_count,
        "claimCondition": claim_condition,
        "distributeType": distribute_type,
    }
    
    print(f"[直接运行] 发送红包参数: {payload}")
    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )
    
    print(f"[直接运行] 响应: {response}")
    
    success = (
        response.get("code") == 0
        or response.get("stayCode") == 0
        or response.get("success") is True
        or response.get("status") == "success"
    )
    
    if success:
        print(f"[直接运行] 红包发送成功")
        return True
    else:
        error_message = (
            response.get("message")
            or response.get("errorMessage")
            or response.get("msg")
            or "未知错误"
        )
        print(f"[直接运行] 红包发送失败: {error_message}")
        return False


if __name__ == "__main__":
    args = parse_args()
    print(f"[命令行参数] phone={args.phone}, amount={args.amount}, count={args.count}, "
          f"condition={args.condition}, distribute-type={args.distribute_type}, "
          f"run-api={args.run_api}, verbose={args.verbose}")
    
    if not args.run_api:
        print("警告: 需要 --run-api 参数才会执行真实API测试")
        print("示例: python test_red_packet.py --run-api --phone 15200711073 --amount 20000 --count 1 --condition 2 --distribute-type 1")
        sys.exit(0)
    
    success = _send_red_packet_direct(
        phone_number=args.phone,
        total_amount=args.amount,
        total_count=args.count,
        claim_condition=args.condition,
        distribute_type=args.distribute_type,
    )
    
    if success:
        print("[直接运行] 测试通过")
        sys.exit(0)
    else:
        print("[直接运行] 测试失败")
        sys.exit(1)

# python tests/test_red_packet.py --run-api --phone 15200711071 --amount 20000 --count 1