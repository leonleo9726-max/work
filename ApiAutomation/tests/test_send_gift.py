"""批量发送礼物的真实 API 场景。"""

import os

import pytest

from common.api_paths import BATCH_SEND_GIFT_PATH
from common.auth_utils import build_business_headers_from_login
from common.business_operations import encrypted_business_request
from common.response_utils import extract_error_message, is_api_success


@pytest.mark.api
@pytest.mark.parametrize("gift_count", [5, 10])
def test_send_gift(gift_count):
    phone_number = os.getenv("API_TEST_PHONE")
    recipient = os.getenv("API_TEST_RECIPIENT_ID")
    if not phone_number or not recipient:
        pytest.skip("需要 API_TEST_PHONE 和 API_TEST_RECIPIENT_ID")
    _, credential = build_business_headers_from_login(phone_number=phone_number)
    response = encrypted_business_request(
        BATCH_SEND_GIFT_PATH,
        {
            "recipients": [recipient],
            "giftId": 93,
            "count": gift_count,
            "sourceType": 1,
            "objectId": os.getenv("API_TEST_OBJECT_ID", recipient),
            "roomId": os.getenv("API_TEST_ROOM_ID", recipient),
        },
        credential,
    )

    assert is_api_success(response), extract_error_message(response)
