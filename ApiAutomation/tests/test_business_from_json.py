"""
业务接口示例测试模块。

演示如何从 login_credentials.json 读取登录凭证，调用后续业务接口。
"""

import logging

import pytest

# conftest.py 已处理 sys.path
from common.api_paths import BUSINESS_SAMPLE_PATH
from common.api_client import EastPointClient
from common.auth_utils import build_business_headers_from_login
from common.response_utils import is_api_success

logger = logging.getLogger(__name__)


@pytest.mark.api
def test_business_api_with_login_json(request):
    """示例：从 login_credentials.json 读取登录凭证，调用后续业务接口。"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    phone_number = "15200711073"

    _, credential = build_business_headers_from_login(phone_number=phone_number)
    assert credential["stayToken"], "读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "读取到的 stayUserId 不能为空"

    payload = {
        "userId": credential["stayUserId"],
        "phoneNumber": credential["phone_number"],
        "action": "queryStatus",
    }

    response = EastPointClient(settings.TEST_ENCRYPT_KEY).post(
        BUSINESS_SAMPLE_PATH,
        payload,
        token=credential["stayToken"],
        locale="en",
    )

    assert response is not None, "业务接口未返回有效响应"
    assert isinstance(response, dict), "业务接口返回值应为 JSON 对象"
    assert is_api_success(response), "业务接口返回失败响应"
    logger.info(f"使用用户 {credential['stayUserId']} 发起请求，响应: {response}")
