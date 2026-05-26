"""Centralized project settings for API automation."""

BASE_URL = "https://api.eastpointtest.com"
TEST_ENCRYPT_KEY = "kGJGJBTNcPI3t0NnWWe60hOcKXuxpyo7"

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
LOGIN_USER_INFO = ""
LOGIN_LANGUAGE_CODE = "en"
LOGIN_TOKEN = ""
LOGIN_PLATFORM = "android"


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
