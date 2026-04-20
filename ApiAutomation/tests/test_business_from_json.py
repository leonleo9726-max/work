import time

import pytest

from common.http_utils import HttpUtils
from config import settings
from tests.test_login_phone import build_business_headers_from_login

# 请根据真实业务接口地址替换下面的示例路径
BUSINESS_SAMPLE_PATH = "/user/stay/business/operation"


@pytest.mark.api
def test_business_api_with_login_json():
    """示例：从 login_credentials.json 读取登录凭证，调用后续业务接口。"""
    phone_number = "15200711073"

    headers, credential = build_business_headers_from_login(phone_number=phone_number)
    assert credential["stayToken"], "读取到的 stayToken 不能为空"
    assert credential["stayUserId"], "读取到的 stayUserId 不能为空"

    url = f"{settings.BASE_URL}{BUSINESS_SAMPLE_PATH}"
    payload = {
        "userId": credential["stayUserId"],
        "phoneNumber": credential["phone_number"],
        "action": "queryStatus",
    }

    response = HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=settings.TEST_ENCRYPT_KEY,
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )

    assert response is not None, "业务接口未返回有效响应"
    assert isinstance(response, dict), "业务接口返回值应为 JSON 对象"
    print(f"[business] 使用用户 {credential['stayUserId']} 发起请求，响应: {response}")
