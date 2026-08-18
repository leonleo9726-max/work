import pytest

from common.http_utils import HttpUtils


pytestmark = pytest.mark.unit


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def post(self, **kwargs):
        self.calls += 1
        return _Response(next(self.responses))


def test_retries_business_jitter_code(monkeypatch):
    session = _Session([{"code": 980003000}, {"code": 0}])
    monkeypatch.setattr(HttpUtils, "get_session", classmethod(lambda cls: session))
    monkeypatch.setattr("common.http_utils.time.sleep", lambda _: None)
    monkeypatch.setattr("common.http_utils.random.uniform", lambda _min, _max: 0.5)

    response = HttpUtils.post(
        "https://example.test/path",
        data={"value": 1},
        encrypt_key="12345678901234567890123456789012",
    )

    assert response == {"code": 0}
    assert session.calls == 2


def test_rejects_an_explicit_empty_encryption_key():
    with pytest.raises(ValueError, match="EASTPOINT_TEST_ENCRYPT_KEY"):
        HttpUtils.post("https://example.test/path", data={"value": 1}, encrypt_key="")
