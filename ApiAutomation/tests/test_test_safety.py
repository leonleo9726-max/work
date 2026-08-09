"""真实 API 测试门禁的离线契约测试。"""

import pytest

import conftest
from common.auth_utils import CredentialRepository, ensure_login_credentials
from common.batch_runner import BatchPolicy, BatchRunner
from common.http_utils import HttpClient, HttpRequestError
from common.logging_utils import redact_sensitive
from common.response_utils import extract_error_details
from common.sign_utils import SignUtils
from config import settings


class _Config:
    def __init__(self, run_api: bool):
        self._run_api = run_api

    def getoption(self, name: str) -> bool:
        assert name == "--run-api"
        return self._run_api


class _Item:
    def __init__(self, is_api: bool):
        self._is_api = is_api
        self.markers = []

    def get_closest_marker(self, name: str):
        return object() if name == "api" and self._is_api else None

    def add_marker(self, marker) -> None:
        self.markers.append(marker)


def test_api_tests_are_skipped_without_explicit_opt_in():
    api_item = _Item(is_api=True)
    offline_item = _Item(is_api=False)

    conftest.pytest_collection_modifyitems(
        _Config(run_api=False),
        [api_item, offline_item],
    )

    assert [marker.name for marker in api_item.markers] == ["skip"]
    assert offline_item.markers == []


def test_api_tests_run_only_with_explicit_opt_in():
    api_item = _Item(is_api=True)

    conftest.pytest_collection_modifyitems(_Config(run_api=True), [api_item])

    assert api_item.markers == []


def test_ensure_login_credentials_persists_login_result(tmp_path):
    repository = CredentialRepository(tmp_path / "credentials.json")
    login_calls = []

    def login(phone_number: str, encrypt_key: str) -> dict:
        login_calls.append((phone_number, encrypt_key))
        return {"stayUserId": "42", "stayToken": "secret-token"}

    credential = ensure_login_credentials(
        "13800138000",
        "test-key",
        login=login,
        repository=repository,
    )

    assert login_calls == [("13800138000", "test-key")]
    assert credential == {
        "phone_number": "13800138000",
        "stayUserId": "42",
        "stayToken": "secret-token",
    }
    assert CredentialRepository(repository.path).get_by_phone("13800138000") == credential


def test_credential_repository_finds_user_id_when_file_is_keyed_by_phone(tmp_path):
    path = tmp_path / "batch_credentials.json"
    path.write_text(
        '{"13800138000":{"phone_number":"13800138000",'
        '"stayUserId":"42","stayToken":"secret-token"}}',
        encoding="utf-8",
    )

    credential = CredentialRepository(path).get_by_user_id("42")

    assert credential is not None
    assert credential["stayUserId"] == "42"


def test_redact_sensitive_masks_nested_credentials():
    redacted = redact_sensitive(
        {
            "stayToken": "secret-token",
            "phone_number": "13800138000",
            "nested": {"uniqueId": "device-identifier", "status": "ok"},
        }
    )

    assert redacted == {
        "stayToken": "***",
        "phone_number": "138****8000",
        "nested": {"uniqueId": "***", "status": "ok"},
    }
    text = redact_sensitive(
        "stayToken='secret-token' uniqueId=device-identifier phone=13800138000"
    )
    assert "secret-token" not in text
    assert "device-identifier" not in text
    assert "13800138000" not in text


def test_encrypt_key_must_be_supplied_by_environment(monkeypatch):
    monkeypatch.delenv("API_AUTOMATION_ENCRYPT_KEY", raising=False)

    with pytest.raises(RuntimeError, match="API_AUTOMATION_ENCRYPT_KEY"):
        settings.require_encrypt_key()

    monkeypatch.setenv("API_AUTOMATION_ENCRYPT_KEY", "local-test-key")
    assert settings.require_encrypt_key() == "local-test-key"


def test_error_details_never_echo_credentials():
    details = extract_error_details({"stayToken": "secret-token"})

    assert "secret-token" not in details
    assert details == "未知错误"


def test_http_client_does_not_retry_post_implicitly():
    class FailingTransport:
        def __init__(self):
            self.calls = 0

        def request(self, method: str, url: str, **kwargs):
            self.calls += 1
            raise TimeoutError("network timeout")

        def close(self):
            pass

    transport = FailingTransport()
    client = HttpClient(transport)

    with pytest.raises(HttpRequestError, match="POST"):
        client.post("https://example.invalid/write", data={"value": 1})

    assert transport.calls == 1


def test_batch_runner_owns_retry_and_summary():
    attempts = {}

    def operation(item: str) -> dict:
        attempts[item] = attempts.get(item, 0) + 1
        return {"success": attempts[item] > 1, "item": item}

    summary = BatchRunner(sleep=lambda _: None).run(
        ["first", "second"],
        operation,
        BatchPolicy(workers=2, attempts=2, retry_delay=0, jitter=0),
    )

    assert summary.succeeded == 2
    assert summary.failed == 0
    assert attempts == {"first": 2, "second": 2}


def test_sign_generation_matches_fixed_vector():
    sign = SignUtils.generate_sign(
        {"stayUserId": "42", "empty": None},
        "en",
        "1700000000000",
        "00000000000000000000000000000000",
    )

    assert sign == "30d976a24dbcd0edb581095c641406989398f7ed4583763a3c522d381efdb719"
