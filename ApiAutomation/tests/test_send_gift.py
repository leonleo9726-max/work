"""
批量发送礼物测试模块。

支持 pytest 参数化测试和直接运行模式。
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import pytest

# conftest.py 已处理 sys.path
from common.api_paths import BATCH_SEND_GIFT_PATH
from common.auth_utils import build_business_headers, build_business_headers_from_login, ensure_login_credentials
from common.http_utils import HttpUtils
from common.response_utils import extract_error_message, is_api_success
from config import settings

logger = logging.getLogger(__name__)


@pytest.mark.api
@pytest.mark.parametrize(
    "phone_number,recipients,gift_id,count,source_type,object_id,room_id",
    [
        ("15200711073", [15712], 93, 10, 1, 202604290000000003, "15712"),
        ("13710011001", [15712], 93, 5, 1, 202604290000000003, "15712"),
    ],
    ids=["send_gift_default", "send_gift_custom"],
)
def test_send_gift(
    request,
    phone_number,
    recipients,
    gift_id,
    count,
    source_type,
    object_id,
    room_id,
):
    """批量发送礼物接口测试，从 login_credentials.json 读取登录凭证。"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    assert credential["stayToken"], "读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "读取到的 stayUserId 不能为空"

    token = credential["stayToken"]
    logger.info(f"用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    url = f"{settings.BASE_URL}{BATCH_SEND_GIFT_PATH}"
    payload = {
        "recipients": recipients,
        "giftId": gift_id,
        "count": count,
        "sourceType": source_type,
        "objectId": object_id,
        "roomId": room_id,
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
        raise AssertionError("批量发送礼物接口未返回有效响应")
    if not isinstance(response, dict):
        raise AssertionError("批量发送礼物接口返回值应为 JSON 对象")

    if not is_api_success(response):
        error_message = extract_error_message(response)
        pytest.fail(f"批量发送礼物失败: {error_message}, 完整响应: {response}")

    logger.info(f"用户 {credential['stayUserId']} 发送礼物成功，参数: {payload}，响应: {response}")


@pytest.mark.api
def test_login_then_send_gift(request, encrypt_key):
    """先执行登录，再自动发送礼物。"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    phone_number = "15200711073"
    credential = ensure_login_credentials(phone_number, encrypt_key)
    assert credential["stayToken"], "登录后读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "登录后读取到的 stayUserId 不能为空"

    token = credential["stayToken"]
    logger.info(f"用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    url = f"{settings.BASE_URL}{BATCH_SEND_GIFT_PATH}"
    payload = {
        "recipients": [15712],
        "giftId": 93,
        "count": 10,
        "sourceType": 1,
        "objectId": 202604290000000003,
        "roomId": "15712",
    }

    headers = build_business_headers(credential['stayToken'])

    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )

    assert response is not None, "批量发送礼物接口未返回有效响应"
    assert isinstance(response, dict), "批量发送礼物接口返回值应为 JSON 对象"

    if not is_api_success(response):
        error_message = extract_error_message(response)
        pytest.fail(f"登录并发送礼物失败: {error_message}, 响应: {response}")

    logger.info(f"用户 {credential['stayUserId']} 登录并发送礼物成功，响应: {response}")


@pytest.mark.api
def test_batch_send_gifts(request):
    """批量发送礼物测试（多用户）"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    phone_numbers = ["15200711073", "13710011001"]
    results = {}

    for phone in phone_numbers:
        try:
            headers, credential = build_business_headers_from_login(phone_number=phone)
            assert credential["stayToken"], f"用户 {phone} 的 stayToken 不能为空"
            assert credential["stayUserId"], f"用户 {phone} 的 stayUserId 不能为空"

            token = credential["stayToken"]
            logger.info(f"用户 {phone} (ID: {credential['stayUserId']}) 的 token: {token[:20]}... (长度: {len(token)})")

            url = f"{settings.BASE_URL}{BATCH_SEND_GIFT_PATH}"
            payload = {
                "recipients": [15712],
                "giftId": 93,
                "count": 10,
                "sourceType": 1,
                "objectId": 202604290000000003,
                "roomId": "15712",
            }

            response = HttpUtils.post(
                url=url,
                data=payload,
                headers=headers,
                encrypt_key=settings.TEST_ENCRYPT_KEY,
                locale="en",
                timestamp=str(int(time.time() * 1000)),
            )

            assert response is not None, f"用户 {phone} 批量发送礼物接口未返回有效响应"
            assert isinstance(response, dict), f"用户 {phone} 批量发送礼物接口返回值应为 JSON 对象"

            if is_api_success(response):
                results[phone] = {"success": True, "response": response}
                logger.info(f"{phone} 发送成功: {response}")
            else:
                error_message = extract_error_message(response)
                results[phone] = {"success": False, "error": error_message}
                logger.info(f"{phone} 发送失败: {error_message}")

        except Exception as e:
            results[phone] = {"success": False, "error": str(e)}
            logger.error(f"{phone} 发送异常: {e}")

        time.sleep(1)

    successful_sends = sum(1 for result in results.values() if result["success"])
    assert successful_sends > 0, f"批量发送失败，所有结果: {results}"


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="批量发送礼物测试")
    parser.add_argument("--phone", type=str, default="15200711073",
                        help="手机号码，默认: 15200711073")
    parser.add_argument("--recipients", type=int, nargs="+", default=[15712],
                        help="接收者用户ID列表，可传多个值，默认: 15712")
    parser.add_argument("--gift-id", type=int, default=93,
                        help="礼物ID，默认: 93")
    parser.add_argument("--count", type=int, default=10,
                        help="礼物数量，默认: 10")
    parser.add_argument("--source-type", type=int, default=1, choices=[1, 2],
                        help="来源类型，默认: 1")
    parser.add_argument("--object-id", type=int, default=202604290000000003,
                        help="对象ID，默认: 202604290000000003")
    parser.add_argument("--room-id", type=str, default="15712",
                        help="房间ID，默认: 15712")
    parser.add_argument("--run-api", action="store_true",
                        help="执行真实API测试（需要此参数才会调用接口）")
    parser.add_argument("--verbose", action="store_true",
                        help="打印详细日志")
    return parser.parse_args()


def _send_gift_direct(phone_number, recipients, gift_id, count, source_type, object_id, room_id):
    """直接运行模式下的礼物发送函数"""
    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    if not credential.get("stayToken") or not credential.get("stayUserId"):
        print(f"错误: 用户 {phone_number} 登录凭证无效")
        sys.exit(1)

    token = credential["stayToken"]
    print(f"[直接运行] 用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    url = f"{settings.BASE_URL}{BATCH_SEND_GIFT_PATH}"
    payload = {
        "recipients": recipients,
        "giftId": gift_id,
        "count": count,
        "sourceType": source_type,
        "objectId": object_id,
        "roomId": room_id,
    }

    print(f"[直接运行] 发送礼物参数: {payload}")
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
        print(f"[直接运行] 礼物发送成功")
        return True
    else:
        return False


if __name__ == "__main__":
    args = parse_args()
    print(f"[命令行参数] phone={args.phone}, recipients={args.recipients}, gift_id={args.gift_id}, "
          f"count={args.count}, source_type={args.source_type}, object_id={args.object_id}, "
          f"room_id={args.room_id}, run-api={args.run_api}, verbose={args.verbose}")

    if not args.run_api:
        print("警告: 需要 --run-api 参数才会执行真实API测试")
        print("示例: python tests/test_send_gift.py --run-api --phone 15200722073 --recipients 15685 --gift-id 93 --count 10 --source-type 1 --object-id 202604290000000010 --room-id 15685")
        sys.exit(0)

    success = _send_gift_direct(
        phone_number=args.phone,
        recipients=args.recipients,
        gift_id=args.gift_id,
        count=args.count,
        source_type=args.source_type,
        object_id=args.object_id,
        room_id=args.room_id,
    )

    if success:
        print("[直接运行] 测试通过")
        sys.exit(0)
    else:
        print("[直接运行] 测试失败")
        sys.exit(1)
