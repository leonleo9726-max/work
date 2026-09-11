"""Centralized project settings for API automation."""

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.getenv("EASTPOINT_BASE_URL", "https://api.eastpointtest.com").rstrip("/")
LIVE_BASE_URL = os.getenv(
    "EASTPOINT_LIVE_BASE_URL", "https://internal.eastpointtest.com:30082/live"
).rstrip("/")
# An empty value is intentional: HttpUtils rejects it when encrypted transport is requested.
TEST_ENCRYPT_KEY = os.getenv("EASTPOINT_TEST_ENCRYPT_KEY", "")

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

SEND_CODE_PATH = "/user/stay/send-code"
REGISTER_PATH = "/user/stay/login/phone"
LOGIN_PHONE_PATH = "/user/stay/login/password"

# Login-related defaults — populated at runtime or via env vars.
# These are examples only; production credentials must come from secure storage.
LOGIN_USER_INFO = os.getenv("EASTPOINT_LOGIN_USER_INFO", "")
LOGIN_LANGUAGE_CODE = os.getenv("EASTPOINT_LOGIN_LANGUAGE_CODE", "en")
LOGIN_TOKEN = os.getenv("EASTPOINT_LOGIN_TOKEN", "")
LOGIN_PLATFORM = os.getenv("EASTPOINT_LOGIN_PLATFORM", "android")


def build_common_encrypted_headers():
    headers = DEFAULT_HEADERS.copy()
    headers["app-language"] = headers["appLanguage"]
    return headers


def build_live_service_headers():
    """构建直播服务请求使用的设备与地域请求头。"""
    headers = build_common_encrypted_headers()
    headers.update(
        {
            "locale": "zh",
            "appLanguage": "zh-CN",
            "app-language": "zh-CN",
            "build-version": "335",
            "client-ip-address": "127.0.0.1",
        }
    )
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
