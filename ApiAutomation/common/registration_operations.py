"""用户注册 module。"""

from typing import Any

from common.api_paths import REGISTER_PATH, SEND_CODE_PATH
from common.http_utils import HttpUtils
from config import settings


def create_send_code_params(
    phone_number: str,
    unique_id: str = "example-device-id",
    area_code: str = "86",
    user_sms_type: int = 0,
    **overrides: Any,
) -> dict:
    params = {
        "platformType": 0,
        "appType": 0,
        "variantType": 0,
        "appVersion": "2.1.4",
        "buildVersion": 317,
        "osModel": "example-device",
        "osVersion": "13",
        "language": "en",
        "uniqueId": unique_id,
        "userSmsType": user_sms_type,
        "areaCode": area_code,
        "phoneNumber": phone_number,
        "validate": None,
        "remoteIp": "127.0.0.1",
        "ipAddress": "127.0.0.1",
    }
    params.update(overrides)
    return params


def create_register_params(
    phone_number: str,
    unique_id: str = "example-device-id",
    verification_code: str = "8888",
    area_code: str = "86",
    **overrides: Any,
) -> dict:
    params = {
        "platformType": 0,
        "appType": 0,
        "variantType": 0,
        "appVersion": "2.1.4",
        "buildVersion": 317,
        "osModel": "example-device",
        "osVersion": "13",
        "language": "en",
        "uniqueId": unique_id,
        "uuid": "example-uuid",
        "deviceId": "example-device-id",
        "timezone": "Asia/Shanghai",
        "languageCountry": "CN",
        "appLanguage": "en",
        "ipAddress": "127.0.0.1",
        "areaCode": area_code,
        "phoneNumber": phone_number,
        "verificationCode": verification_code,
    }
    params.update(overrides)
    return params


def _post(path: str, params: dict, encrypt_key: str) -> dict:
    return HttpUtils.post(
        url=f"{settings.BASE_URL}{path}",
        data=params,
        headers=settings.build_common_encrypted_headers(),
        encrypt_key=encrypt_key,
    )


def send_verification_code(params: dict, encrypt_key: str) -> dict:
    return _post(SEND_CODE_PATH, params, encrypt_key)


def register_user(params: dict, encrypt_key: str) -> dict:
    return _post(REGISTER_PATH, params, encrypt_key)
