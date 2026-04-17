import pytest
import base64
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.http_utils import HttpUtils
from config import settings


def _to_base64(value):
    """将字符串转为 base64 文本。"""
    if value is None:
        return None
    return base64.b64encode(str(value).encode("utf-8")).decode("utf-8")


def create_login_phone_params(
    phone_number="15200711073",
    verification_code="8888",
    area_code="86",
    **kwargs,
):
    """创建登录参数，统一对齐项目加密请求字段。"""
    params = {
        "platformType": 0,
        "appType": 0,
        "variantType": 0,
        "appVersion": "2.1.4",
        "buildVersion": 317,
        "osModel": "V2278A",
        "osVersion": "13",
        "language": "en",
        "uniqueId": "bac1131e82cd4c738e3199375ffe77b4",
        "uuid": "9fcd8047c27442138fdbdcddcb026ebd",
        "deviceId": "be825900787d419f9872eed48566f45c",
        "widevineId": None,
        "idfv": None,
        "idfa": None,
        "mcc": None,
        "mnc": None,
        "networkName": None,
        "inviteCode": None,
        "downloadChannel": None,
        "ipAddress": "41.235.64.230",
        "remoteIp": "41.235.64.230",
        "languageCountry": "en",
        "appLanguage": "en",
        "areaCode": area_code,
        "phoneNumber": phone_number,
        "verificationCode": verification_code,
        "captchaType": 0,
        "loginPwdType": 0,
        "password": "a123456",
        "tablet": 0,
        "simulator": 0,
        "useVpn": 0,
        "useRoot": 0,
        "useDebug": 0,
        "mockLocation": 0,
        "timezone":  "Asia/Shanghai",
        "languageCountry": "en",
        "appLanguage": "en",
        "areaCode": area_code,
        "phoneNumber": phone_number,
        "password": "a123456",
        "verificationCode": verification_code,
        "captchaType": 0,
        "loginPwdType": 0,
    }
    params.update(kwargs)
    params["password"] = _to_base64(params.get("password"))
    return params


def login_with_phone(payload, encrypt_key):
    """调用手机登录接口（统一使用一种 header 模式）。"""
    locale = str(payload.get("language", "en"))
    timestamp = str(int(time.time() * 1000))
    url = f"{settings.BASE_URL}{settings.LOGIN_PHONE_PATH}"
    headers = settings.build_common_encrypted_headers()
    return HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=encrypt_key,
        locale=locale,
        timestamp=timestamp,
    )


def _is_login_success(response):
    """根据常见返回结构判断是否登录成功。"""
    if not isinstance(response, dict):
        return False

    if response.get("stayCode") in (0, "0", 200, "200"):
        return True
    if response.get("stayIsSuccess") is True:
        return True

    if response.get("code") in (0, "0", 200, "200"):
        return True
    if response.get("success") is True:
        return True
    if response.get("status") in ("success", "ok", "SUCCESS", "OK"):
        return True

    data = response.get("data")
    if isinstance(data, dict):
        if data.get("token") or data.get("accessToken") or data.get("jwt"):
            return True

    return False


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


@pytest.mark.api
def test_login_phone_api(request, encrypt_key):
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    payload = create_login_phone_params()
    response = login_with_phone(payload, encrypt_key)

    assert response is not None
    assert isinstance(response, dict)

    login_success = _is_login_success(response)

    print(f"[login_phone] 响应: {response}")
    print(f"[login_phone] 登录结果: success={login_success}")

    if not login_success:
        error_message = (
            response.get("stayErrorMessage")
            or response.get("stayMessage")
            or response.get("errorMessage")
            or response.get("message")
            or response.get("msg")
            or "未知错误"
        )
        pytest.fail(
            f"登录失败: code={response.get('code')}, "
            f"stayCode={response.get('stayCode')}, message={error_message}, response={response}"
        )


def _build_debug_payload():
    """右上角直接运行文件时，复用同一套测试参数。"""
    return create_login_phone_params()


if __name__ == "__main__":
    payload = _build_debug_payload()
    print("[login_phone][debug] direct run mode enabled")
    response = login_with_phone(payload, settings.TEST_ENCRYPT_KEY)
    print(f"[login_phone] 响应: {response}")
    print(f"[login_phone] 登录结果: success={_is_login_success(response)}")
