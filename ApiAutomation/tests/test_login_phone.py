import pytest
import base64
import json
import time
import sys
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.http_utils import HttpUtils
from config import settings

LOGIN_CREDENTIALS_FILE = PROJECT_ROOT / "data" / "login_credentials.json"


def load_phones_from_csv():
    """从 CSV 文件加载手机号列表。"""
    data_file = PROJECT_ROOT / "data" / "login_phone.csv"
    phones = []
    with data_file.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            phone = (row.get("phone_number") or "").strip()
            if phone:
                phones.append(phone)
    return phones


PHONE_CASES = load_phones_from_csv()


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


LOGIN_CREDENTIALS = {}


def extract_login_user_info(response):
    """从登录响应中提取 stayUserId 和 stayToken。"""
    if not isinstance(response, dict):
        return None

    data = response.get("data") if isinstance(response.get("data"), dict) else response
    stay_user_id = data.get("stayUserId")
    stay_token = data.get("stayToken")
    if stay_user_id and stay_token:
        return {
            "stayUserId": str(stay_user_id),
            "stayToken": str(stay_token),
        }
    return None


def store_login_credentials(phone_number, login_info):
    """存储登录凭证，保证 stayUserId 与 stayToken 一一对应。"""
    if not login_info:
        return

    user_id = login_info["stayUserId"]
    token = login_info["stayToken"]

    existing = LOGIN_CREDENTIALS.get(user_id)
    if existing and existing["stayToken"] != token:
        raise AssertionError(
            f"用户ID {user_id} 已存在不同 token：{existing['stayToken']} vs {token}"
        )

    LOGIN_CREDENTIALS[user_id] = {
        "phone_number": phone_number,
        "stayUserId": user_id,
        "stayToken": token,
    }
    save_login_credentials_to_json()


def _ensure_login_credentials_file():
    if not LOGIN_CREDENTIALS_FILE.parent.exists():
        LOGIN_CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)


def save_login_credentials_to_json():
    _ensure_login_credentials_file()
    with LOGIN_CREDENTIALS_FILE.open("w", encoding="utf-8") as file:
        json.dump(LOGIN_CREDENTIALS, file, ensure_ascii=False, indent=2)


def load_login_credentials_from_json():
    if not LOGIN_CREDENTIALS_FILE.exists():
        return {}
    try:
        with LOGIN_CREDENTIALS_FILE.open("r", encoding="utf-8") as file:
            return json.load(file) or {}
    except (json.JSONDecodeError, IOError):
        return {}


def get_login_credentials_by_user_id(stay_user_id):
    user_id = str(stay_user_id)
    if user_id in LOGIN_CREDENTIALS:
        return LOGIN_CREDENTIALS[user_id]
    persisted = load_login_credentials_from_json()
    return persisted.get(user_id)


def get_login_credentials_by_phone(phone_number):
    for value in LOGIN_CREDENTIALS.values():
        if value["phone_number"] == phone_number:
            return value
    persisted = load_login_credentials_from_json()
    for value in persisted.values():
        if value.get("phone_number") == phone_number:
            return value
    return None


def build_business_headers_from_login(phone_number=None, stay_user_id=None):
    """从持久化登录 token 构建后续业务请求的 headers。"""
    credential = None
    if phone_number:
        credential = get_login_credentials_by_phone(phone_number)
    elif stay_user_id:
        credential = get_login_credentials_by_user_id(stay_user_id)

    if credential is None:
        raise ValueError(
            "未找到登录凭证，请先执行登录并生成 data/login_credentials.json。"
        )

    headers = settings.build_common_encrypted_headers()
    headers["Authorization"] = f"Bearer {credential['stayToken']}"
    return headers, credential


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
@pytest.mark.parametrize("phone_number", PHONE_CASES, ids=lambda x: f"phone={x}")
def test_login_phone_api(request, encrypt_key, phone_number):
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    payload = create_login_phone_params(phone_number=phone_number)
    response = login_with_phone(payload, encrypt_key)

    assert response is not None
    assert isinstance(response, dict)

    login_success = _is_login_success(response)

    login_info = extract_login_user_info(response)
    if login_info:
        store_login_credentials(phone_number, login_info)
    
    print(f"[login_phone] phone={phone_number}, 响应: {response}")
    print(f"[login_phone] phone={phone_number}, 登录结果: success={login_success}")
    if login_info:
        print(f"[login_phone] phone={phone_number}, stayUserId={login_info['stayUserId']} stayToken={login_info['stayToken']}")

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
            f"登录失败: phone={phone_number}, code={response.get('code')}, "
            f"stayCode={response.get('stayCode')}, message={error_message}, response={response}"
        )

    # 避免接口请求过于频繁，等待2秒
    time.sleep(2)


def _build_debug_payload():
    """右上角直接运行文件时，复用同一套测试参数。"""
    return create_login_phone_params()


if __name__ == "__main__":
    payload = _build_debug_payload()
    print("[login_phone][debug] direct run mode enabled")
    response = login_with_phone(payload, settings.TEST_ENCRYPT_KEY)
    print(f"[login_phone] 响应: {response}")
    print(f"[login_phone] 登录结果: success={_is_login_success(response)}")
