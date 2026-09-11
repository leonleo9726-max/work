"""直播礼物请求的公共构造与发送函数。"""

from common.http_utils import HttpUtils
from config import settings


RECIPIENT_MODES = ("ALL_MIC", "ALL_ROOM")
GIFT_SOURCE_TYPES = (1, 2, 3, 4)
LIVE_GIFT_SOURCE_TYPE = 1


def build_live_gift_payload(
    recipients: list[int] | None,
    *,
    gift_id: int | None = None,
    payload: str | None = None,
    count: int | None = None,
    source_type: int | None = None,
    object_id: int | None = None,
    backpack_id: int | None = None,
    room_id: str | None = None,
    recipient_mode: str | None = None,
) -> dict:
    """构建直播批量送礼载荷，并保证收礼方式和字段值有效。"""
    if recipients is not None and recipient_mode is not None:
        raise ValueError("recipients 与 recipient_mode 只能指定其中一种")
    if recipients is None and recipient_mode is None:
        raise ValueError("必须指定 recipients 或 recipient_mode")
    if recipients is not None:
        if not recipients or any(user_id <= 0 for user_id in recipients):
            raise ValueError("recipients 必须包含至少一个正整数 user_id")
        request_payload = {"recipients": recipients}
    else:
        if recipient_mode not in RECIPIENT_MODES:
            raise ValueError(f"recipient_mode 必须为以下值之一: {', '.join(RECIPIENT_MODES)}")
        request_payload = {"recipientMode": recipient_mode}

    positive_fields = {
        "giftId": gift_id,
        "count": count,
        "objectId": object_id,
        "backpackId": backpack_id,
    }
    if any(value is not None and value <= 0 for value in positive_fields.values()):
        raise ValueError("gift_id、count、object_id 和 backpack_id 必须为正整数")
    if source_type is not None and source_type not in GIFT_SOURCE_TYPES:
        raise ValueError(f"source_type 必须为以下值之一: {GIFT_SOURCE_TYPES}")

    request_payload.update(
        {
            key: value
            for key, value in {
                **positive_fields,
                "payload": payload,
                "sourceType": source_type,
                "roomId": room_id,
            }.items()
            if value is not None
        }
    )
    return request_payload


def build_live_gift_headers(credential: dict) -> dict:
    """构建直播批量送礼所需的认证和设备请求头。"""
    headers = settings.build_live_service_headers()
    headers.update(
        {
            "token": credential["stayToken"],
            "user-id": str(credential["stayUserId"]),
            "user-agent": "Dart/3.7 (dart:io)",
        }
    )
    return headers


def post_live_gift(url: str, payload: dict, headers: dict):
    """向直播服务发送明文 JSON 的批量送礼请求。"""
    return HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=None,
        locale="zh",
    )
