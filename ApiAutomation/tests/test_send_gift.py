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

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.api_paths import BATCH_SEND_GIFT_PATH
from common.auth_utils import build_business_headers_from_login, ensure_login_credentials
from common.live_gift import (
    GIFT_SOURCE_TYPES,
    LIVE_GIFT_SOURCE_TYPE,
    RECIPIENT_MODES,
    build_live_gift_headers,
    build_live_gift_payload,
    post_live_gift,
)
from common.live_heartbeat import LiveHeartbeatLoop
from common.response_utils import extract_error_message, is_api_success
from config import settings

logger = logging.getLogger(__name__)
DEFAULT_HEARTBEAT_LIVE_ID = 0
HEARTBEAT_INTERVAL_SECONDS = 15.0
def _start_heartbeat(credential, live_id=DEFAULT_HEARTBEAT_LIVE_ID):
    """启动直播心跳；送礼流程仅依赖心跳与批量送礼两个接口。"""
    heartbeat_loop = LiveHeartbeatLoop(
        [credential],
        live_id=live_id,
        interval_seconds=HEARTBEAT_INTERVAL_SECONDS,
    )
    heartbeat_loop.start()
    return heartbeat_loop


@pytest.mark.unit
def test_start_heartbeat_uses_sender_credential(monkeypatch):
    events = []

    def fake_init(self, credentials, live_id, interval_seconds):
        events.append(("init_heartbeat", credentials, live_id, interval_seconds))

    def fake_start(self):
        events.append(("start_heartbeat",))

    monkeypatch.setattr(LiveHeartbeatLoop, "__init__", fake_init)
    monkeypatch.setattr(LiveHeartbeatLoop, "start", fake_start)

    result = _start_heartbeat(
        {"stayUserId": "100", "stayToken": "test-token"},
    )

    assert events == [
        ("init_heartbeat", [{"stayUserId": "100", "stayToken": "test-token"}], 0, 15.0),
        ("start_heartbeat",),
    ]
    assert result is not None


@pytest.mark.unit
def test_build_live_gift_headers_uses_sender_and_curl_device_headers():
    headers = build_live_gift_headers(
        {"stayUserId": "16515", "stayToken": "sender-token"}
    )

    assert headers["token"] == "sender-token"
    assert headers["user-id"] == "16515"
    assert headers["user-agent"] == "Dart/3.7 (dart:io)"
    assert headers["client-ip-address"] == "127.0.0.1"
    assert headers["app-language"] == "zh-CN"
    assert headers["build-version"] == "335"


@pytest.mark.unit
def test_post_live_gift_sends_plain_json(monkeypatch):
    captured = {}

    def fake_post(**kwargs):
        captured.update(kwargs)
        return {"code": 200}

    monkeypatch.setattr("common.live_gift.HttpUtils.post", fake_post)

    response = post_live_gift("https://example.test/live/gift/batch-send", {"giftId": 63}, {})

    assert response == {"code": 200}
    assert captured["encrypt_key"] is None
    assert captured["locale"] == "zh"


@pytest.mark.unit
def test_build_gift_payload_only_includes_specified_optional_fields():
    assert build_live_gift_payload([15712], source_type=3) == {
        "recipients": [15712],
        "sourceType": 3,
    }


@pytest.mark.unit
def test_build_gift_payload_uses_recipient_mode_without_recipients():
    assert build_live_gift_payload(None, recipient_mode="ALL_MIC") == {
        "recipientMode": "ALL_MIC"
    }


@pytest.mark.unit
def test_build_gift_payload_rejects_both_recipient_selectors():
    with pytest.raises(ValueError, match="只能指定其中一种"):
        build_live_gift_payload([15712], recipient_mode="ALL_MIC")


@pytest.mark.unit
def test_build_gift_payload_supports_updated_optional_fields():
    assert build_live_gift_payload(
        [15712],
        gift_id=63,
        payload="gift-payload",
        count=1,
        source_type=3,
        object_id=202609100000000007,
        backpack_id=9,
        room_id="15712",
    ) == {
        "recipients": [15712],
        "giftId": 63,
        "payload": "gift-payload",
        "count": 1,
        "sourceType": 3,
        "objectId": 202609100000000007,
        "backpackId": 9,
        "roomId": "15712",
    }


@pytest.mark.api
@pytest.mark.parametrize(
    "phone_number,recipients,gift_id,count,source_type,object_id,room_id",
    [
        ("15200711073", [15712], 93, 10, 3, 202604290000000003, "15712"),
        ("13710011001", [15712], 93, 5, 3, 202604290000000003, "15712"),
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

    _, credential = build_business_headers_from_login(phone_number=phone_number)
    headers = build_live_gift_headers(credential)
    assert credential["stayToken"], "读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "读取到的 stayUserId 不能为空"

    token = credential["stayToken"]
    logger.info(f"用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    heartbeat_loop = _start_heartbeat(credential)
    try:
        url = f"{settings.LIVE_BASE_URL}{BATCH_SEND_GIFT_PATH}"
        payload = build_live_gift_payload(
            recipients,
            gift_id=gift_id,
            count=count,
            source_type=source_type,
            object_id=object_id,
            room_id=room_id,
        )

        logger.info(f"发送请求到: {url}")
        logger.info(f"请求参数: {payload}")

        response = post_live_gift(url, payload, headers)

        logger.info(f"完整响应: {response}")

        if response is None:
            raise AssertionError("批量发送礼物接口未返回有效响应")
        if not isinstance(response, dict):
            raise AssertionError("批量发送礼物接口返回值应为 JSON 对象")

        if not is_api_success(response):
            error_message = extract_error_message(response)
            pytest.fail(f"批量发送礼物失败: {error_message}, 完整响应: {response}")
    finally:
        if heartbeat_loop:
            heartbeat_loop.stop()

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

    url = f"{settings.LIVE_BASE_URL}{BATCH_SEND_GIFT_PATH}"
    payload = build_live_gift_payload(
        [15712],
        gift_id=93,
        count=10,
        source_type=3,
        object_id=202604290000000003,
        room_id="15712",
    )

    headers = build_live_gift_headers(credential)
    heartbeat_loop = _start_heartbeat(credential)
    try:
        response = post_live_gift(url, payload, headers)

        assert response is not None, "批量发送礼物接口未返回有效响应"
        assert isinstance(response, dict), "批量发送礼物接口返回值应为 JSON 对象"

        if not is_api_success(response):
            error_message = extract_error_message(response)
            pytest.fail(f"登录并发送礼物失败: {error_message}, 响应: {response}")
    finally:
        if heartbeat_loop:
            heartbeat_loop.stop()

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
            _, credential = build_business_headers_from_login(phone_number=phone)
            headers = build_live_gift_headers(credential)
            assert credential["stayToken"], f"用户 {phone} 的 stayToken 不能为空"
            assert credential["stayUserId"], f"用户 {phone} 的 stayUserId 不能为空"

            token = credential["stayToken"]
            logger.info(f"用户 {phone} (ID: {credential['stayUserId']}) 的 token: {token[:20]}... (长度: {len(token)})")

            url = f"{settings.LIVE_BASE_URL}{BATCH_SEND_GIFT_PATH}"
            payload = build_live_gift_payload(
                [15712],
                gift_id=93,
                count=10,
                source_type=3,
                object_id=202604290000000003,
                room_id="15712",
            )

            heartbeat_loop = _start_heartbeat(credential)
            try:
                response = post_live_gift(url, payload, headers)

                assert response is not None, f"用户 {phone} 批量发送礼物接口未返回有效响应"
                assert isinstance(response, dict), f"用户 {phone} 批量发送礼物接口返回值应为 JSON 对象"

                if is_api_success(response):
                    results[phone] = {"success": True, "response": response}
                    logger.info(f"{phone} 发送成功: {response}")
                else:
                    error_message = extract_error_message(response)
                    results[phone] = {"success": False, "error": error_message}
                    logger.info(f"{phone} 发送失败: {error_message}")
            finally:
                if heartbeat_loop:
                    heartbeat_loop.stop()

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
    recipients = parser.add_mutually_exclusive_group()
    recipients.add_argument("--recipients", type=int, nargs="+",
                            help="接收者用户ID列表，可传多个")
    recipients.add_argument("--recipient-mode", choices=RECIPIENT_MODES,
                            help="收礼模式：ALL_MIC 或 ALL_ROOM")
    parser.add_argument("--gift-id", type=int,
                        help="礼物ID（可选）")
    parser.add_argument("--payload", type=str,
                        help="礼物负载信息（可选）")
    parser.add_argument("--count", type=int,
                        help="礼物数量（可选）")
    parser.add_argument("--source-type", type=int, default=LIVE_GIFT_SOURCE_TYPE,
                        choices=GIFT_SOURCE_TYPES,
                        help="来源类型，默认: 1（直播）")
    parser.add_argument("--object-id", type=int,
                        help="并联ID（可选）")
    parser.add_argument("--backpack-id", type=int,
                        help="背包礼物ID（可选）")
    parser.add_argument("--room-id", type=str,
                        help="房间ID（可选）")
    parser.add_argument("--live-id", type=int, required=True,
                        help="直播心跳 liveId，例如 0")
    parser.add_argument("--run-api", action="store_true",
                        help="执行真实API测试（需要此参数才会调用接口）")
    parser.add_argument("--verbose", action="store_true",
                        help="打印详细日志")
    args = parser.parse_args()
    if args.recipients is None and args.recipient_mode is None:
        parser.error("必须指定 --recipients 或 --recipient-mode")
    return args


@pytest.mark.unit
def test_parse_args_uses_live_source_type_by_default(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["test_send_gift.py", "--live-id", "0", "--recipients", "15712"]
    )

    args = parse_args()

    assert args.source_type == LIVE_GIFT_SOURCE_TYPE
    assert args.recipients == [15712]
    assert args.recipient_mode is None


@pytest.mark.unit
def test_parse_args_requires_explicit_recipient_selection(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test_send_gift.py", "--live-id", "0"])

    with pytest.raises(SystemExit):
        parse_args()


def _send_gift_direct(
    phone_number,
    recipients,
    gift_id,
    payload,
    count,
    source_type,
    object_id,
    backpack_id,
    room_id,
    recipient_mode,
    live_id,
):
    """直接运行模式下的礼物发送函数"""
    _, credential = build_business_headers_from_login(phone_number=phone_number)
    headers = build_live_gift_headers(credential)
    if not credential.get("stayToken") or not credential.get("stayUserId"):
        print(f"错误: 用户 {phone_number} 登录凭证无效")
        sys.exit(1)

    token = credential["stayToken"]
    print(f"[直接运行] 用户 {credential['stayUserId']} 的 token: {token[:20]}... (长度: {len(token)})")

    url = f"{settings.LIVE_BASE_URL}{BATCH_SEND_GIFT_PATH}"
    request_payload = build_live_gift_payload(
        recipients,
        gift_id=gift_id,
        payload=payload,
        count=count,
        source_type=source_type,
        object_id=object_id,
        backpack_id=backpack_id,
        room_id=room_id,
        recipient_mode=recipient_mode,
    )

    print(f"[直接运行] 发送礼物参数: {request_payload}")
    print(f"[直接运行] 请求URL: {url}")

    heartbeat_loop = _start_heartbeat(credential, live_id=live_id)
    try:
        response = post_live_gift(url, request_payload, headers)
    finally:
        if heartbeat_loop:
            heartbeat_loop.stop()

    print(f"[直接运行] 完整响应: {response}")

    if is_api_success(response):
        print(f"[直接运行] 礼物发送成功")
        return True
    else:
        return False


if __name__ == "__main__":
    args = parse_args()
    print(f"[命令行参数] phone={args.phone}, recipients={args.recipients}, gift_id={args.gift_id}, "
          f"payload={args.payload}, count={args.count}, source_type={args.source_type}, "
          f"object_id={args.object_id}, backpack_id={args.backpack_id}, room_id={args.room_id}, "
          f"recipient_mode={args.recipient_mode}, live_id={args.live_id}, run-api={args.run_api}, verbose={args.verbose}")

    if not args.run_api:
        print("警告: 需要 --run-api 参数才会执行真实API测试")
        print("示例: python tests/test_send_gift.py --run-api --phone 15200722073 --recipients 15685 --gift-id 93 --count 1 --object-id 202604290000000010 --live-id 202604290000000010")
        sys.exit(0)

    success = _send_gift_direct(
        phone_number=args.phone,
        recipients=args.recipients,
        gift_id=args.gift_id,
        payload=args.payload,
        count=args.count,
        source_type=args.source_type,
        object_id=args.object_id,
        backpack_id=args.backpack_id,
        room_id=args.room_id,
        recipient_mode=args.recipient_mode,
        live_id=args.live_id,
    )

    if success:
        print("[直接运行] 测试通过")
        sys.exit(0)
    else:
        print("[直接运行] 测试失败")
        sys.exit(1)
