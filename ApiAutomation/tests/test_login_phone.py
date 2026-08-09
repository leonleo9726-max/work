"""手机号登录 interface 测试。"""

import csv
import logging
import os
from pathlib import Path

import pytest

from common.auth_utils import store_login_credentials
from common.logging_utils import redact_sensitive
from common.login_operations import create_login_phone_params, login_with_phone
from common.response_utils import extract_error_message, extract_login_info, is_api_success

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_phones_from_csv() -> list[str]:
    data_file = PROJECT_ROOT / "data" / "local" / "login_phone.csv"
    if not data_file.exists():
        return []
    with data_file.open("r", encoding="utf-8-sig", newline="") as file:
        return [
            phone
            for row in csv.DictReader(file)
            if (phone := (row.get("phone_number") or "").strip())
        ]


PHONE_CASES = load_phones_from_csv()


def test_create_login_phone_params_contains_required_fields():
    payload = create_login_phone_params(
        phone_number="13800138000",
        verification_code="8888",
        area_code="86",
    )

    assert payload["phoneNumber"] == "13800138000"
    assert payload["verificationCode"] == "8888"
    assert payload["areaCode"] == "86"
    assert payload["platformType"] == 0
    assert payload["password"] == "YTEyMzQ1Ng=="


def _assert_login_succeeded(phone_number: str, response: dict) -> None:
    login_info = extract_login_info(response)
    if login_info:
        store_login_credentials(phone_number, login_info)
    if not is_api_success(response):
        pytest.fail(f"登录失败: {extract_error_message(response)}")
    assert login_info is not None, "登录成功响应必须包含用户 ID 和 token"
    logger.info("登录成功: %s", redact_sensitive(login_info))


@pytest.mark.api
def test_login_phone_api_single(encrypt_key):
    phone_number = os.getenv("API_TEST_PHONE")
    if not phone_number:
        pytest.skip("需要 API_TEST_PHONE 指定本地测试账号")
    unique_id = os.getenv("API_TEST_DEVICE_ID", "example-device-id")
    response = login_with_phone(
        create_login_phone_params(phone_number, uniqueId=unique_id),
        encrypt_key,
    )
    _assert_login_succeeded(phone_number, response)


@pytest.mark.api
@pytest.mark.parametrize("phone_number", PHONE_CASES, ids=lambda value: "phone=***")
def test_login_phone_api_batch(encrypt_key, phone_number):
    response = login_with_phone(create_login_phone_params(phone_number), encrypt_key)
    _assert_login_succeeded(phone_number, response)
