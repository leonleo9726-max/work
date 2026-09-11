import pytest

from common.api_client import EastPointClient


pytestmark = pytest.mark.unit


class _Transport:
    captured = None

    @classmethod
    def post(cls, **kwargs):
        cls.captured = kwargs
        return {"code": 0}


def test_client_hides_url_headers_and_encryption_details():
    response = EastPointClient(
        "12345678901234567890123456789012",
        transport=_Transport,
        base_url="https://example.test/",
    ).post("/demo", {"value": 1}, token="token-value", user_id="16515")

    assert response == {"code": 0}
    assert _Transport.captured["url"] == "https://example.test/demo"
    assert _Transport.captured["headers"]["token"] == "token-value"
    assert _Transport.captured["headers"]["user-id"] == "16515"
    assert _Transport.captured["encrypt_key"] == "12345678901234567890123456789012"


def test_client_requires_an_encryption_key():
    with pytest.raises(ValueError, match="EASTPOINT_TEST_ENCRYPT_KEY"):
        EastPointClient("")


def test_client_merges_extra_headers():
    EastPointClient(
        "12345678901234567890123456789012",
        transport=_Transport,
        base_url="https://example.test/",
    ).post("/demo", {}, extra_headers={"client-ip-address": "127.0.0.1"})

    assert _Transport.captured["headers"]["client-ip-address"] == "127.0.0.1"


def test_client_can_send_plain_json_for_an_endpoint_exception():
    EastPointClient(
        "12345678901234567890123456789012",
        transport=_Transport,
        base_url="https://example.test/",
    ).post("/demo", {"value": 1}, plain_json=True)

    assert _Transport.captured["encrypt_key"] is None
