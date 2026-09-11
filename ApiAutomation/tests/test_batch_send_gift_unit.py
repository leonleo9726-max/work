import pytest

from batch_send_gift import distribute_request_counts, execute_send_gift_repeated, post_batch_gift
from common.api_paths import BATCH_SEND_GIFT_PATH
from common.live_gift import build_live_gift_payload
from config import settings


pytestmark = pytest.mark.unit


def test_build_gift_payload_for_specific_recipients():
    assert build_live_gift_payload(
        [100, 101], gift_id=63, count=1, source_type=1, object_id=202609070000000005
    ) == {
        "giftId": 63,
        "count": 1,
        "sourceType": 1,
        "objectId": 202609070000000005,
        "recipients": [100, 101],
    }


def test_build_gift_payload_for_recipient_mode():
    payload = build_live_gift_payload(
        None,
        gift_id=63,
        count=1,
        source_type=1,
        object_id=202609070000000005,
        recipient_mode="ALL_MIC",
    )

    assert payload["recipientMode"] == "ALL_MIC"
    assert "recipients" not in payload


@pytest.mark.parametrize(
    "recipients,recipient_mode",
    [([100], "ALL_ROOM"), (None, None), ([], None), (None, "INVALID")],
)
def test_build_gift_payload_rejects_invalid_recipient_selection(recipients, recipient_mode):
    with pytest.raises(ValueError):
        build_live_gift_payload(
            recipients,
            gift_id=63,
            count=1,
            source_type=1,
            object_id=202609070000000005,
            recipient_mode=recipient_mode,
        )


def test_build_gift_payload_includes_optional_fields_when_specified():
    assert build_live_gift_payload(
        [100],
        gift_id=63,
        count=1,
        source_type=1,
        object_id=202609070000000005,
        payload="gift-payload",
        backpack_id=9,
        room_id="100",
    ) == {
        "giftId": 63,
        "count": 1,
        "sourceType": 1,
        "objectId": 202609070000000005,
        "recipients": [100],
        "payload": "gift-payload",
        "backpackId": 9,
        "roomId": "100",
    }


def test_post_batch_gift_uses_sender_token_and_user_id(monkeypatch):
    captured = {}

    def fake_post(url, payload, headers):
        captured.update(url=url, payload=payload, headers=headers)
        return {"code": 0}

    monkeypatch.setattr("batch_send_gift.post_live_gift", fake_post)
    response = post_batch_gift(
        {"stayUserId": "16515", "stayToken": "sender-token"},
        {"giftId": 63},
    )

    assert response == {"code": 0}
    assert captured["url"] == f"{settings.LIVE_BASE_URL}{BATCH_SEND_GIFT_PATH}"
    assert captured["headers"]["token"] == "sender-token"
    assert captured["headers"]["user-id"] == "16515"


def test_distribute_request_counts_evenly_and_preserves_total():
    request_counts = distribute_request_counts(100_000, 10)

    assert request_counts == [10_000] * 10
    assert sum(request_counts) == 100_000


def test_distribute_request_counts_assigns_remainder_to_earlier_senders():
    assert distribute_request_counts(10, 3) == [4, 3, 3]


def test_execute_send_gift_repeated_counts_each_attempt(monkeypatch):
    sent_payloads = []

    def fake_post(credential, payload):
        sent_payloads.append((credential, payload))
        return {"code": 200, "isSuccess": True}

    monkeypatch.setattr("batch_send_gift.post_batch_gift", fake_post)
    monkeypatch.setattr("batch_send_gift.HttpUtils.close_session", lambda: None)

    result = execute_send_gift_repeated(
        {"stayUserId": "16515", "stayToken": "sender-token"},
        {"giftId": 63},
        request_count=3,
    )

    assert len(sent_payloads) == 3
    assert result["attempted_count"] == 3
    assert result["success_count"] == 3
    assert result["failure_count"] == 0
    assert result["skipped_count"] == 0
    assert result["ok"] is True
