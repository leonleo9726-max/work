import json

import pytest

from common import auth_utils


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def restore_credential_cache():
    original = dict(auth_utils._LOGIN_CREDENTIALS)
    auth_utils._LOGIN_CREDENTIALS.clear()
    yield
    auth_utils._LOGIN_CREDENTIALS.clear()
    auth_utils._LOGIN_CREDENTIALS.update(original)


def test_store_credentials_writes_a_complete_json_document(tmp_path, monkeypatch):
    credentials_file = tmp_path / "login_credentials.json"
    monkeypatch.setattr(auth_utils, "LOGIN_CREDENTIALS_FILE", credentials_file)

    auth_utils.store_login_credentials(
        "13800138000",
        {"stayUserId": "1001", "stayToken": "test-token"},
    )

    assert json.loads(credentials_file.read_text(encoding="utf-8")) == {
        "1001": {
            "phone_number": "13800138000",
            "stayUserId": "1001",
            "stayToken": "test-token",
        }
    }
    assert not credentials_file.with_suffix(".json.tmp").exists()
