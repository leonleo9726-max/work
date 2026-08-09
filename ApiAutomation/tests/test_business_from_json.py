"""
业务接口示例测试模块。

演示如何从 login_credentials.json 读取登录凭证，调用后续业务接口。
"""

import os

import pytest

# conftest.py 已处理 sys.path
from common.api_paths import BUSINESS_SAMPLE_PATH
from common.auth_utils import build_business_headers_from_login
from common.business_operations import encrypted_business_request
from common.response_utils import extract_error_message, is_api_success


@pytest.mark.api
def test_business_api_with_login_json():
    """示例：从 login_credentials.json 读取登录凭证，调用后续业务接口。"""
    phone_number = os.getenv("API_TEST_PHONE")
    if not phone_number:
        pytest.skip("需要 API_TEST_PHONE 指定本地测试账号")

    _, credential = build_business_headers_from_login(phone_number=phone_number)
    assert credential["stayToken"], "读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "读取到的 stayUserId 不能为空"

    payload = {
        "userId": credential["stayUserId"],
        "phoneNumber": credential["phone_number"],
        "action": "queryStatus",
    }

    response = encrypted_business_request(BUSINESS_SAMPLE_PATH, payload, credential)

    assert response is not None, "业务接口未返回有效响应"
    assert isinstance(response, dict), "业务接口返回值应为 JSON 对象"
    assert is_api_success(response), extract_error_message(response)
