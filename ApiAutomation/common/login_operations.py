"""手机号登录 module。"""

import base64
import time
from typing import Any

from common.api_paths import LOGIN_PHONE_PATH
from common.http_utils import HttpUtils
from common.response_utils import extract_error_message, extract_login_info, is_api_success
from config import settings


def to_base64(value: str) -> str:
    return base64.b64encode(str(value).encode("utf-8")).decode("utf-8")


def create_login_phone_params(
    phone_number: str,
    verification_code: str = "8888",
    area_code: str = "86",
    **overrides: Any,
) -> dict:
    """构造登录请求参数。"""
    params = {
        "platformType": 0,
        "appType": 0,
        "variantType": 0,
        "appVersion": "2.1.4",
        "buildVersion": 317,
        "osModel": "V2278A",
        "osVersion": "13",
        "language": "en",
        "uniqueId": "example-device-id",
        "uuid": "example-uuid",
        "deviceId": "example-device-id",
        "widevineId": None,
        "idfv": None,
        "idfa": None,
        "mcc": None,
        "mnc": None,
        "networkName": None,
        "inviteCode": None,
        "downloadChannel": None,
        "ipAddress": "127.0.0.1",
        "remoteIp": "127.0.0.1",
        "timezone": "Asia/Shanghai",
        "tablet": 0,
        "simulator": 0,
        "useVpn": 0,
        "useRoot": 0,
        "useDebug": 0,
        "mockLocation": 0,
        "languageCountry": "en",
        "appLanguage": "en",
        "areaCode": area_code,
        "phoneNumber": phone_number,
        "password": "a123456",
        "verificationCode": verification_code,
        "captchaType": 0,
        "loginPwdType": 0,
    }
    params.update(overrides)
    params["password"] = to_base64(params["password"])
    return params


def login_with_phone(payload: dict, encrypt_key: str) -> dict:
    """调用手机号登录 interface，并返回原始 JSON 响应。"""
    response = HttpUtils.post(
        url=f"{settings.BASE_URL}{LOGIN_PHONE_PATH}",
        data=payload,
        headers=settings.build_common_encrypted_headers(),
        encrypt_key=encrypt_key,
        locale=str(payload.get("language", "en")),
        timestamp=str(int(time.time() * 1000)),
    )
    if not isinstance(response, dict):
        raise RuntimeError("登录接口未返回 JSON 对象")
    return response


def login_phone(phone_number: str, encrypt_key: str) -> dict:
    """登录并返回可由凭证 repository 保存的信息。"""
    response = login_with_phone(create_login_phone_params(phone_number), encrypt_key)
    if not is_api_success(response):
        raise RuntimeError(f"登录失败: {extract_error_message(response)}")
    login_info = extract_login_info(response)
    if login_info is None:
        raise RuntimeError("登录成功但响应缺少用户 ID 或 token")
    return login_info
