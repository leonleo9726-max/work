import time

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