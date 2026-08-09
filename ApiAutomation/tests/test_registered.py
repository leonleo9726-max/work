"""用户注册 interface 测试。"""

import os

import pytest

from common.registration_operations import (
    create_register_params,
    create_send_code_params,
    register_user,
    send_verification_code,
)
from common.response_utils import extract_error_message, is_api_success


def test_create_send_code_params_contains_required_fields():
    params = create_send_code_params("13800138000")

    assert params["phoneNumber"] == "13800138000"
    assert params["areaCode"] == "86"
    assert params["userSmsType"] == 0
    assert "ipAddress" in params


def test_create_register_params_contains_required_fields():
    params = create_register_params("13800138000", verification_code="8888")

    assert params["phoneNumber"] == "13800138000"
    assert params["verificationCode"] == "8888"
    assert params["areaCode"] == "86"
    assert params["uniqueId"] == "example-device-id"


def _registration_environment() -> tuple[str, str]:
    phone_number = os.getenv("API_TEST_REGISTER_PHONE")
    unique_id = os.getenv("API_TEST_DEVICE_ID")
    if not phone_number or not unique_id:
        pytest.skip("需要 API_TEST_REGISTER_PHONE 和 API_TEST_DEVICE_ID")
    return phone_number, unique_id


@pytest.mark.api
def test_send_code_api(encrypt_key):
    phone_number, unique_id = _registration_environment()
    response = send_verification_code(
        create_send_code_params(phone_number, unique_id),
        encrypt_key,
    )

    assert is_api_success(response), extract_error_message(response)


@pytest.mark.api
def test_register_api(encrypt_key):
    phone_number, unique_id = _registration_environment()
    response = register_user(
        create_register_params(phone_number, unique_id),
        encrypt_key,
    )

    assert is_api_success(response), extract_error_message(response)
