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
    ).post("/demo", {"value": 1}, token="token-value")

    assert response == {"code": 0}
    assert _Transport.captured["url"] == "https://example.test/demo"
    assert _Transport.captured["headers"]["token"] == "token-value"
    assert _Transport.captured["encrypt_key"] == "12345678901234567890123456789012"


def test_client_requires_an_encryption_key():
    with pytest.raises(ValueError, match="EASTPOINT_TEST_ENCRYPT_KEY"):
        EastPointClient("")
