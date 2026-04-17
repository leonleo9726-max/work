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

LOGIN_USER_INFO = "1101656%2C116724380944632386574%2C%2C%2C-1%2Cnull%2C1%2C-1"
LOGIN_LANGUAGE_CODE = "en"
LOGIN_TOKEN = "iOaCQ0AXv5hFeLk75Jng8mXOnurm+FHeQ0u6qOsmiHLwfLck5DcXLzCyElXO67UakUgYRlGcfiX6VHGNIaLyOg=="
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
