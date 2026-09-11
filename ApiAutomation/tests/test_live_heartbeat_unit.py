import pytest

from common.live_heartbeat import LiveHeartbeatLoop, post_live_heartbeat


pytestmark = pytest.mark.unit


def test_post_live_heartbeat_uses_live_id_and_sender_credentials(monkeypatch):
    captured = {}

    class Client:
        def __init__(self, encrypt_key, base_url=None):
            captured["encrypt_key"] = encrypt_key
            captured["base_url"] = base_url

        def post(self, path, payload, **kwargs):
            captured.update(path=path, payload=payload, **kwargs)
            return {"code": 0}

    monkeypatch.setattr("common.live_heartbeat.settings.TEST_ENCRYPT_KEY", "a" * 32)

    response = post_live_heartbeat(
        {"stayUserId": "16515", "stayToken": "sender-token"},
        live_id=0,
        client_factory=Client,
    )

    assert response == {"code": 0}
    assert captured["path"] == "/live/heartbeat"
    assert captured["payload"] == {"liveId": 0}
    assert captured["token"] == "sender-token"
    assert captured["user_id"] == "16515"
    assert captured["base_url"] == "https://internal.eastpointtest.com:30082/live"
    assert captured["extra_headers"]["client-ip-address"] == "127.0.0.1"


def test_heartbeat_loop_sends_an_initial_heartbeat_for_every_sender():
    calls = []

    def post_heartbeat(credential, live_id):
        calls.append((credential["stayUserId"], live_id))
        return {"code": 0}

    loop = LiveHeartbeatLoop(
        [
            {"stayUserId": "100", "stayToken": "token-100"},
            {"stayUserId": "101", "stayToken": "token-101"},
        ],
        live_id=0,
        interval_seconds=60,
        post_heartbeat=post_heartbeat,
    )

    loop.start()
    loop.stop()

    assert calls == [("100", 0), ("101", 0)]
    assert loop.failures == []


def test_heartbeat_loop_rejects_unsuccessful_initial_heartbeat():
    loop = LiveHeartbeatLoop(
        [{"stayUserId": "100", "stayToken": "token-100"}],
        live_id=0,
        interval_seconds=60,
        post_heartbeat=lambda _credential, _live_id: {"code": 500, "message": "not in room"},
    )

    with pytest.raises(RuntimeError, match="心跳失败"):
        loop.start()
