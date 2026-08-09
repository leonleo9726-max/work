"""领取红包的真实 API 场景。"""

import os

import pytest

from common.api_paths import RECEIVE_RED_PACKET_PATH
from common.auth_utils import build_business_headers_from_login
from common.business_operations import encrypted_business_request
from common.response_utils import extract_error_message, is_api_success


@pytest.mark.api
def test_receive_red_packet():
    red_packet_id = os.getenv("API_TEST_RED_PACKET_ID")
    if not red_packet_id:
        pytest.skip("需要 API_TEST_RED_PACKET_ID 指定测试红包")
    phone_number = os.getenv("API_TEST_PHONE")
    if not phone_number:
        pytest.skip("需要 API_TEST_PHONE 指定本地测试账号")
    _, credential = build_business_headers_from_login(phone_number=phone_number)
    response = encrypted_business_request(
        RECEIVE_RED_PACKET_PATH,
        {"stayRedPacketId": red_packet_id},
        credential,
    )

    assert is_api_success(response), extract_error_message(response)
