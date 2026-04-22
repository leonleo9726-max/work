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


SEND_GIFT_RED_PACKET_PATH = "/payer/redPacket/send/gift"


@pytest.mark.api
@pytest.mark.parametrize(
    "phone_number,room_id,gift_id,gift_count,total_amount,total_count,claim_condition,distribute_type",
    [
        ("15200711073", None, 107, 7, 266, 5, 2, 1),  # 默认值测试
        ("13710011001", None, 107, 10, 500, 3, 2, 1),  # 自定义值测试
    ],
    ids=["default_gift_red_packet", "custom_gift_red_packet"],
)
def send_gift_red_packet(headers, credential, payload):
    """发送礼物红包的辅助函数"""
    url = f"{settings.BASE_URL}{SEND_GIFT_RED_PACKET_PATH}"
    
    print(f"[send_gift_red_packet] 发送请求到: {url}")
    print(f"[send_gift_red_packet] 请求头: {headers}")
    print(f"[send_gift_red_packet] 请求参数: {payload}")
    
    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )
    
    print(f"[send_gift_red_packet] 完整响应: {response}")
    
    if response is None:
        raise AssertionError("发送礼物红包接口未返回有效响应")
    
    if not isinstance(response, dict):
        raise AssertionError("发送礼物红包接口返回值应为 JSON 对象")
    
    return response


def test_send_gift_red_packet(request, phone_number, room_id, gift_id, gift_count, total_amount, total_count, claim_condition, distribute_type):
    """发送礼物红包接口测试，从 login_credentials.json 读取登录凭证。"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    assert credential["stayToken"], "读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "读取到的 stayUserId 不能为空"

    # 记录请求头中的 token
    token = credential["stayToken"]
    print(f"[send_gift_red_packet] 用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    # 如果room_id为None，使用登录的userid作为roomId
    actual_room_id = room_id if room_id is not None else credential["stayUserId"]
    
    payload = {
        "roomId": actual_room_id,
        "giftId": gift_id,
        "giftCount": gift_count,
        "totalAmount": total_amount,
        "totalCount": total_count,
        "claimCondition": claim_condition,
        "distributeType": distribute_type,
    }

    # 发送红包并获取完整响应
    response = send_gift_red_packet(headers, credential, payload)

    # 检查响应是否成功
    success = (
        response.get("code") == 0
        or response.get("stayCode") == 200
        or response.get("stayIsSuccess") is True
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
        pytest.fail(f"发送礼物红包失败: {error_message}, 完整响应: {response}")

    print(f"[send_gift_red_packet] 用户 {credential['stayUserId']} 发送礼物红包成功，参数: {payload}，响应: {response}")


@pytest.mark.api
def test_login_then_send_gift_red_packet(request, encrypt_key):
    """先执行登录，再自动发送礼物红包。"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    phone_number = "15200711073"
    from tests.test_login_phone import ensure_login_credentials

    credential = ensure_login_credentials(phone_number, encrypt_key)
    assert credential["stayToken"], "登录后读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "登录后读取到的 stayUserId 不能为空"

    # 记录请求头中的 token
    token = credential["stayToken"]
    print(f"[login_then_send_gift] 用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    url = f"{settings.BASE_URL}{SEND_GIFT_RED_PACKET_PATH}"
    payload = {
        "roomId": credential["stayUserId"],
        "giftId": 107,
        "giftCount": 7,
        "totalAmount": 266,
        "totalCount": 5,
        "claimCondition": 2,
        "distributeType": 1,
    }

    # 构建正确的headers，使用token字段而不是Authorization
    headers = settings.build_common_encrypted_headers()
    headers["token"] = credential['stayToken']
    
    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )

    assert response is not None, "发送礼物红包接口未返回有效响应"
    assert isinstance(response, dict), "发送礼物红包接口返回值应为 JSON 对象"

    success = (
        response.get("code") == 0
        or response.get("stayCode") == 200
        or response.get("stayIsSuccess") is True
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
        pytest.fail(f"登录并发送礼物红包失败: {error_message}, 响应: {response}")

    print(f"[login_then_send_gift] 用户 {credential['stayUserId']} 登录并发送礼物红包成功，响应: {response}")


@pytest.mark.api
def test_batch_send_gift_red_packets(request):
    """批量发送礼物红包测试"""
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
            print(f"[batch_gift_red_packet] 用户 {phone} (ID: {credential['stayUserId']}) 的 token: {token[:20]}... (长度: {len(token)})")

            url = f"{settings.BASE_URL}{SEND_GIFT_RED_PACKET_PATH}"
            payload = {
                "roomId": credential["stayUserId"],
                "giftId": 107,
                "giftCount": 7,
                "totalAmount": 266,
                "totalCount": 5,
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

            assert response is not None, f"用户 {phone} 发送礼物红包接口未返回有效响应"
            assert isinstance(response, dict), f"用户 {phone} 发送礼物红包接口返回值应为 JSON 对象"

            success = (
                response.get("code") == 0
                or response.get("stayCode") == 200
                or response.get("stayIsSuccess") is True
                or response.get("success") is True
                or response.get("status") == "success"
            )

            if success:
                results[phone] = {"success": True, "response": response}
                print(f"[batch_gift_red_packet] {phone} 发送成功: {response}")
            else:
                error_message = (
                    response.get("message")
                    or response.get("errorMessage")
                    or response.get("msg")
                    or "未知错误"
                )
                results[phone] = {"success": False, "error": error_message}
                print(f"[batch_gift_red_packet] {phone} 发送失败: {error_message}")

        except Exception as e:
            results[phone] = {"success": False, "error": str(e)}
            print(f"[batch_gift_red_packet] {phone} 发送异常: {e}")

        time.sleep(1)  # 避免请求过于频繁

    # 至少有一个成功
    successful_sends = sum(1 for result in results.values() if result["success"])
    assert successful_sends > 0, f"批量发送失败，所有结果: {results}"


def parse_args():
    """解析命令行参数"""
    import argparse
    parser = argparse.ArgumentParser(description="发送礼物红包测试")
    parser.add_argument("--phone", type=str, default="15200711073",
                       help="手机号码，默认: 15200711073")
    parser.add_argument("--room-id", type=str, default=None,
                       help="房间ID，默认使用登录用户的ID")
    parser.add_argument("--gift-id", type=int, default=107,
                       help="礼物ID，默认: 107")
    parser.add_argument("--gift-count", type=int, default=7,
                       help="礼物数量，默认: 7")
    parser.add_argument("--total-amount", type=int, default=266,
                       help="红包总金额，默认: 266")
    parser.add_argument("--total-count", type=int, default=5,
                       help="红包个数，默认: 5")
    parser.add_argument("--claim-condition", type=int, default=2,
                       help="领取条件，默认: 2")
    parser.add_argument("--distribute-type", type=int, default=1,
                       help="分发类型：1-即时，2-定时，默认: 1")
    parser.add_argument("--run-api", action="store_true",
                       help="执行真实API测试（需要此参数才会调用接口）")
    parser.add_argument("--verbose", action="store_true",
                       help="打印详细日志")
    return parser.parse_args()


def _send_gift_red_packet_direct(phone_number, room_id, gift_id, gift_count, total_amount, total_count, claim_condition, distribute_type):
    """直接运行模式下的礼物红包发送函数"""
    import sys
    from tests.test_login_phone import build_business_headers_from_login
    from config import settings
    from common.http_utils import HttpUtils
    
    # 获取登录凭证
    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    if not credential.get("stayToken") or not credential.get("stayUserId"):
        print(f"错误: 用户 {phone_number} 登录凭证无效")
        sys.exit(1)
    
    # 记录请求头中的 token
    token = credential["stayToken"]
    print(f"[直接运行] 用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")
    
    # 如果room_id为None，使用登录的userid作为roomId
    actual_room_id = room_id if room_id is not None else credential["stayUserId"]
    
    url = f"{settings.BASE_URL}{SEND_GIFT_RED_PACKET_PATH}"
    payload = {
        "roomId": actual_room_id,
        "giftId": gift_id,
        "giftCount": gift_count,
        "totalAmount": total_amount,
        "totalCount": total_count,
        "claimCondition": claim_condition,
        "distributeType": distribute_type,
    }
    
    print(f"[直接运行] 发送礼物红包参数: {payload}")
    print(f"[直接运行] 请求URL: {url}")
    
    # 发送请求
    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )
    
    print(f"[直接运行] 完整响应: {response}")
    
    success = (
        response.get("code") == 0
        or response.get("stayCode") == 200
        or response.get("stayIsSuccess") is True
        or response.get("success") is True
        or response.get("status") == "success"
    )
    
    if success:
        print(f"[直接运行] 礼物红包发送成功")
        return True
    else:
        # 不打印详细错误信息，只返回False
        return False


if __name__ == "__main__":
    args = parse_args()
    print(f"[命令行参数] phone={args.phone}, room-id={args.room_id}, gift-id={args.gift_id}, "
          f"gift-count={args.gift_count}, total-amount={args.total_amount}, total-count={args.total_count}, "
          f"claim-condition={args.claim_condition}, distribute-type={args.distribute_type}, "
          f"run-api={args.run_api}, verbose={args.verbose}")
    
    if not args.run_api:
        print("警告: 需要 --run-api 参数才会执行真实API测试")
        print("示例: python test_gift_red_packet.py --run-api --phone 15200711073 --gift-id 107 --gift-count 7 --total-amount 266 --total-count 5 --claim-condition 2 --distribute-type 1")
        sys.exit(0)
    
    success = _send_gift_red_packet_direct(
        phone_number=args.phone,
        room_id=args.room_id,
        gift_id=args.gift_id,
        gift_count=args.gift_count,
        total_amount=args.total_amount,
        total_count=args.total_count,
        claim_condition=args.claim_condition,
        distribute_type=args.distribute_type,
    )
    
    if success:
        print("[直接运行] 测试通过")
        sys.exit(0)
    else:
        print("[直接运行] 测试失败")
        sys.exit(1)

# python tests/test_gift_red_packet.py --run-api --phone 15200711071 --gift-id 107 --gift-count 7 --total-amount 266 --total-count 5 --claim-condition 2 --distribute-type 1