"""
手机登录测试模块。

提供手机号验证码和密码登录的测试用例和辅助函数。
登录凭证管理已统一迁移至 common/auth_utils.py。
"""

import argparse
import csv
import logging
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.auth_utils import (
    create_phone_login_params,
    create_login_phone_params,
    login_with_verification_code,
    login_with_phone,
    store_login_credentials,
)
from common.response_utils import extract_login_info, is_api_success
from config import settings

logger = logging.getLogger(__name__)

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
    parser.add_argument("--login-mode", choices=("password", "phone"), default="password",
                        help="登录方式：password 或 phone（验证码登录）")
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


def _is_login_success(response):
    """根据常见返回结构判断是否登录成功。"""
    return is_api_success(response)


def extract_login_user_info(response):
    """从登录响应中提取 stayUserId 和 stayToken。"""
    return extract_login_info(response)


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


def test_create_phone_login_params_contains_required_fields():
    payload = create_phone_login_params(
        phone_number="13800138000",
        verification_code="8888",
        area_code="86",
        unique_id="test-device-id",
    )

    assert payload["stayPhoneNumber"] == "13800138000"
    assert payload["stayVerificationCode"] == "8888"
    assert payload["stayAreaCode"] == "86"
    assert payload["stayUniqueId"] == "test-device-id"
    assert payload["stayLoginType"] == 3
    assert payload["stayLoginPwdType"] == 1
    assert "password" not in payload


def build_login_payload(login_mode, phone_number, verification_code, area_code, password):
    """根据选择的登录方式构造相应接口的业务载荷。"""
    if login_mode == "phone":
        return create_phone_login_params(
            phone_number=phone_number,
            verification_code=verification_code,
            area_code=area_code,
        )
    return create_login_phone_params(
        phone_number=phone_number,
        verification_code=verification_code,
        area_code=area_code,
        password=password,
    )


def execute_login(login_mode, payload, encrypt_key):
    """将业务载荷发送至所选登录接口。"""
    if login_mode == "phone":
        return login_with_verification_code(payload, encrypt_key)
    return login_with_phone(payload, encrypt_key)


@pytest.mark.api
def test_login_phone_api_single(request, encrypt_key):
    """单用户登录测试，支持命令行参数"""
    if not request.config.getoption("--run-api"):
        pytest.skip("need --run-api option to execute real API tests")

    login_mode = request.config.getoption("--login-mode")
    phone_number = request.config.getoption("--phone")
    verification_code = request.config.getoption("--code")
    area_code = request.config.getoption("--area")
    password = request.config.getoption("--password")

    payload = build_login_payload(
        login_mode, phone_number, verification_code, area_code, password
    )
    response = execute_login(login_mode, payload, encrypt_key)

    assert response is not None
    assert isinstance(response, dict)

    login_success = _is_login_success(response)

    login_info = extract_login_user_info(response)
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

    login_mode = request.config.getoption("--login-mode")
    payload = build_login_payload(login_mode, phone_number, "8888", "86", "a123456")
    response = execute_login(login_mode, payload, encrypt_key)

    assert response is not None
    assert isinstance(response, dict)

    login_success = _is_login_success(response)

    login_info = extract_login_user_info(response)
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


def _build_debug_payload(login_mode, phone=None, code=None, area=None, password=None):
    """右上角直接运行文件时，复用同一套测试参数。"""
    return build_login_payload(
        login_mode,
        phone or "15200711073",
        code or "8888",
        area or "86",
        password or "a123456",
    )


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    args = parse_args()
    logger.info(f"phone={args.phone}, login_mode={args.login_mode}, run-api={args.run_api}, verbose={args.verbose}")

    if not args.run_api:
        print("警告: 需要 --run-api 参数才会执行真实API测试")
        print("示例: python tests/test_login_phone.py --run-api --login-mode phone --phone 15200711073 --code 8888 --area 86")
        sys.exit(0)

    payload = _build_debug_payload(args.login_mode, phone=args.phone, code=args.code, area=args.area, password=args.password)
    print("[login_phone][debug] direct run mode enabled")
    response = execute_login(args.login_mode, payload, settings.TEST_ENCRYPT_KEY)
    print(f"[login_phone] 响应: {response}")
    print(f"[login_phone] 登录结果: success={_is_login_success(response)}")
    
    # 提取登录信息
    login_info = extract_login_user_info(response)
    if login_info:
        print(f"[login_phone] stayUserId={login_info['stayUserId']} stayToken={login_info['stayToken']}")
        store_login_credentials(args.phone, login_info)
        print(f"[login_phone] 登录凭证已保存")
