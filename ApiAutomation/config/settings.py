"""Centralized project settings for API automation."""

import os

BASE_URL = "https://api.eastpointtest.com"

DEFAULT_HEADERS = {
    "content-type": "application/json",
    "locale": "zh",
    "appLanguage": "en",
    "app-type": "0",
    "content-sign": "sat1",
    "content-status": "1",
    "platform-type": "0",
    "variant-type": "0",
    "build-version": "317",
}

# Login-related defaults — populated at runtime or via env vars.
# These are examples only; production credentials must come from secure storage.
LOGIN_USER_INFO = ""
LOGIN_LANGUAGE_CODE = "en"
LOGIN_TOKEN = ""
LOGIN_PLATFORM = "android"


def require_encrypt_key() -> str:
    """读取运行时加密密钥，未配置时立即停止真实请求。"""
    encrypt_key = os.getenv("API_AUTOMATION_ENCRYPT_KEY", "")
    if not encrypt_key:
        raise RuntimeError(
            "缺少 API_AUTOMATION_ENCRYPT_KEY；真实 API 请求必须通过环境变量提供密钥"
        )
    return encrypt_key


def build_common_encrypted_headers():
    headers = DEFAULT_HEADERS.copy()
    headers["app-language"] = headers["appLanguage"]
    return headers


def build_login_headers():
    headers = build_common_encrypted_headers()
    headers.update(
        {
            "User-Info": LOGIN_USER_INFO,
            "languageCode": LOGIN_LANGUAGE_CODE,
            "Token": LOGIN_TOKEN,
            "platform": LOGIN_PLATFORM,
            "Content-Type": "application/json",
        }
    )
    return headers
