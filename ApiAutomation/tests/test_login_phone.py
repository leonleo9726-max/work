"""
手机登录测试模块。

提供手机号密码登录的测试用例和辅助函数。
登录凭证管理已统一迁移至 common/auth_utils.py。
"""

import argparse
import csv
import logging
import sys
import time
from pathlib import Path

import pytest

# conftest.py 已处理 sys.path，此处不再需要
from common.api_paths import LOGIN_PHONE_PATH
from common.auth_utils import (
    get_login_credentials_by_phone,
    load_login_credentials_from_json,
    store_login_credentials,
    to_base64,
)
from common.http_utils import HttpUtils
from common.response_utils import extract_login_info, is_api_success
from config import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGIN_CREDENTIALS_FILE = PROJECT_ROOT / "data" / "login_credentials.json"


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="单用户手机登录测试")
    parser.add_argument("--phone", type=str, default="15200711073",
                        help="手机号码，默认: 15200711073")
    parser.add_argument("--code", type=str, default="8888",
                        help="验证码，默认: 8888")
    parser.add_argument("--area", type=str, default="86",
                        help="区号，默认: 86")
    parser.add_argument("--password", type=str, default="a123456",
                        help="密码，默认: a123456（会自动进行base64编码）")
    parser.add_argument("--run-api", action="store_true",
                        help="执行真实API测试（需要此参数才会调用接口）")
    parser.add_argument("--verbose", action="store_true",
                        help="打印详细日志")
    return parser.parse_args()


def load_phones_from_csv():
    """从 CSV 文件加载手机号列表。"""
    data_file = PROJECT_ROOT / "data" / "login_phone.csv"
    phones = []
    if data_file.exists():
        with data_file.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                phone = (row.get("phone_number") or "").strip()
                if phone:
                    phones.append(phone)
    return phones


# 为了向后兼容，保留 PHONE_CASES 变量
PHONE_CASES = load_phones_from_csv()


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
        "timezone": "Asia/Shanghai",
    }
    params.update(kwargs)
    params["password"] = to_base64(params.get("password"))
    return params


def login_with_phone(payload, encrypt_key):
    """调用手机登录接口（统一使用一种 header 模式）。"""
    locale = str(payload.get("language", "en"))
    timestamp = str(int(time.time() * 1000))
    url = f"{settings.BASE_URL}{LOGIN_PHONE_PATH}"
    headers = settings.build_common_encrypted_headers()
    return HttpUtils.post(
        url=url,
        data=payload,
        headers=headers,
        encrypt_key=encrypt_key,
        locale=locale,
        timestamp=timestamp,
    )


def login_phone_and_store(phone_number, encrypt_key, verification_code="8888", area_code="86", **kwargs):
    """执行登录并存储登录凭证。"""
    payload = create_login_phone_params(
        phone_number=phone_number,
        verification_code=verification_code,
        area_code=area_code,
        **kwargs,
    )
    response = login_with_phone(payload, encrypt_key)

    if response is None or not isinstance(response, dict):
        raise RuntimeError("登录接口返回为空或非 JSON 数据")

    login_success = is_api_success(response)
    login_info = extract_login_info(response)
    if login_info:
        store_login_credentials(phone_number, login_info)

    if not login_success:
        from common.response_utils import extract_error_message
        error_message = extract_error_message(response)
        raise RuntimeError(
            f"登录失败: phone={phone_number}, message={error_message}, response={response}"
        )

    return get_login_credentials_by_phone(phone_number)


def ensure_login_credentials(phone_number, encrypt_key):
    """确保存在指定手机号的登录凭证，必要时执行登录。"""
    credential = get_login_credentials_by_phone(phone_number)
    if credential:
        return credential
    return login_phone_and_store(phone_number, encrypt_key)


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
def test_login_phone_api_single(request, encrypt_key):
    """单用户登录测试，支持命令行参数"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    # 解析命令行参数
    args = parse_args()
    phone_number = args.phone
    verification_code = args.code
    area_code = args.area
    password = args.password
    verbose = args.verbose

    if verbose:
        logger.info(f"phone={phone_number}, code={verification_code}, area={area_code}, password={password}")

    payload = create_login_phone_params(
        phone_number=phone_number,
        verification_code=verification_code,
        area_code=area_code,
        password=password,
    )
    response = login_with_phone(payload, encrypt_key)

    assert response is not None
    assert isinstance(response, dict)

    login_success = is_api_success(response)

    login_info = extract_login_info(response)
    if login_info:
        store_login_credentials(phone_number, login_info)

    logger.info(f"phone={phone_number}, 响应: {response}")
    logger.info(f"phone={phone_number}, 登录结果: success={login_success}")
    if login_info:
        logger.info(f"phone={phone_number}, stayUserId={login_info['stayUserId']} stayToken={login_info['stayToken']}")

    if not login_success:
        from common.response_utils import extract_error_message
        error_message = extract_error_message(response)
        pytest.fail(
            f"登录失败: phone={phone_number}, code={response.get('code')}, "
            f"stayCode={response.get('stayCode')}, message={error_message}, response={response}"
        )

    # 避免接口请求过于频繁，等待2秒
    time.sleep(2)


@pytest.mark.api
@pytest.mark.parametrize("phone_number", PHONE_CASES, ids=lambda x: f"phone={x}")
def test_login_phone_api_batch(request, encrypt_key, phone_number):
    """批量登录测试（向后兼容）"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    payload = create_login_phone_params(phone_number=phone_number)
    response = login_with_phone(payload, encrypt_key)

    assert response is not None
    assert isinstance(response, dict)

    login_success = is_api_success(response)

    login_info = extract_login_info(response)
    if login_info:
        store_login_credentials(phone_number, login_info)

    logger.info(f"phone={phone_number}, 响应: {response}")
    logger.info(f"phone={phone_number}, 登录结果: success={login_success}")
    if login_info:
        logger.info(f"phone={phone_number}, stayUserId={login_info['stayUserId']} stayToken={login_info['stayToken']}")

    if not login_success:
        from common.response_utils import extract_error_message
        error_message = extract_error_message(response)
        pytest.fail(
            f"登录失败: phone={phone_number}, code={response.get('code')}, "
            f"stayCode={response.get('stayCode')}, message={error_message}, response={response}"
        )

    # 避免接口请求过于频繁，等待2秒
    time.sleep(2)


def _build_debug_payload(phone=None, code=None, area=None, password=None):
    """右上角直接运行文件时，复用同一套测试参数。"""
    return create_login_phone_params(
        phone_number=phone or "15200711073",
        verification_code=code or "8888",
        area_code=area or "86",
        password=password or "a123456",
    )


if __name__ == "__main__":
    args = parse_args()
    logger.info(f"phone={args.phone}, code={args.code}, area={args.area}, password={args.password}, run-api={args.run_api}, verbose={args.verbose}")

    if not args.run_api:
        print("警告: 需要 --run-api 参数才会执行真实API测试")
        print("示例: python tests/test_login_phone.py --run-api --phone 15200711073 --code 8888 --area 86 --password a123456")
        sys.exit(0)

    payload = _build_debug_payload(phone=args.phone, code=args.code, area=args.area, password=args.password)
    print("[login_phone][debug] direct run mode enabled")
    response = login_with_phone(payload, settings.TEST_ENCRYPT_KEY)
    print(f"[login_phone] 响应: {response}")
    print(f"[login_phone] 登录结果: success={is_api_success(response)}")

    # 提取登录信息
    login_info = extract_login_info(response)
    if login_info:
        print(f"[login_phone] stayUserId={login_info['stayUserId']} stayToken={login_info['stayToken']}")
        store_login_credentials(args.phone, login_info)
        print(f"[login_phone] 登录凭证已保存")
