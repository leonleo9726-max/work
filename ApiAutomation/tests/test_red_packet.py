"""发送金币红包的真实 API 场景。"""

import os

import pytest

from common.api_paths import SEND_COIN_RED_PACKET_PATH
from common.auth_utils import build_business_headers_from_login
from common.business_operations import encrypted_business_request
from common.response_utils import extract_error_message, is_api_success


@pytest.mark.api
def test_send_coin_red_packet():
    phone_number = os.getenv("API_TEST_PHONE")
    if not phone_number:
        pytest.skip("需要 API_TEST_PHONE 指定本地测试账号")
    _, credential = build_business_headers_from_login(phone_number=phone_number)
    response = encrypted_business_request(
        SEND_COIN_RED_PACKET_PATH,
        {
            "roomId": credential["stayUserId"],
            "totalAmount": 100,
            "totalCount": 1,
            "claimCondition": 2,
            "distributeType": 1,
        },
        credential,
    )

    assert is_api_success(response), extract_error_message(response)
