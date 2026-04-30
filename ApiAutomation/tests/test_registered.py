"""
用户注册测试模块。

支持从 CSV 文件加载手机号和设备 ID，进行批量注册测试。
"""

import csv
import logging
import random
import time
from pathlib import Path

import pytest

# conftest.py 已处理 sys.path
from common.api_paths import REGISTER_PATH, SEND_CODE_PATH
from common.http_utils import HttpUtils
from common.response_utils import extract_error_message, is_api_success
from config import settings

logger = logging.getLogger(__name__)

REGISTER_TEST_PHONE = "13900011111"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_phones_from_csv():
    """从 CSV 文件加载注册手机号列表。"""
    data_file = PROJECT_ROOT / "data" / "register_phone.csv"
    phones = []
    with data_file.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            phone = (row.get("phone_number") or "").strip()
            if phone:
                phones.append(phone)
    return phones


def load_unique_ids_from_csv():
    """从 CSV 文件加载uniqueId列表。"""
    data_file = PROJECT_ROOT / "data" / "device_ids.csv"
    unique_ids = []
    with data_file.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            unique_id = (row.get("uniqueId") or "").strip()
            if unique_id:
                unique_ids.append(unique_id)
    return unique_ids


def create_balanced_random_allocation():
    """
    为每个手机号随机分配提供的uniqueId，可循环使用
    """
    phones = load_phones_from_csv()
    unique_ids = load_unique_ids_from_csv()

    if not unique_ids:
        unique_ids = ['00026a07e2434812b65b0c3b40678afe']

    test_cases = []
    for phone in phones:
        unique_id = random.choice(unique_ids)
        test_case = {
            'phone_number': phone,
            'uniqueId': unique_id
        }
        test_cases.append(test_case)

    return test_cases


# 设置随机种子以确保测试可重复
random.seed(42)
TEST_CASES = create_balanced_random_allocation()


def send_verification_code(params, encrypt_key):
    """发送验证码"""
    try:
        url = f"{settings.BASE_URL}{SEND_CODE_PATH}"
        headers = settings.build_common_encrypted_headers()

        response = HttpUtils.post(
            url=url,
            data=params,
            headers=headers,
            encrypt_key=encrypt_key,
        )
        return response
    except Exception as e:
        logger.error(f"发送验证码失败: {e}")
        return {'code': 500, 'message': f'服务器内部错误: {str(e)}'}


def create_send_code_params(phone_number, area_code="86", user_sms_type=0, **kwargs):
    """创建发送验证码的参数"""
    default_params = {
        'platformType': 0,
        'appType': 0,
        'variantType': 0,
        'appVersion': '2.1.3',
        'buildVersion': 317,
        'osModel': 'RMX3511',
        'osVersion': '33',
        'language': 'ar',
        'uniqueId': kwargs.get('uniqueId', '00026a07e2434812b65b0c3b40678afe'),
        'userSmsType': user_sms_type,
        'areaCode': area_code,
        'phoneNumber': phone_number,
        'validate': kwargs.get('validate'),
        'remoteIp': '41.235.64.230',
        'ipAddress': '41.235.64.230',
    }
    default_params.update(kwargs)
    return default_params


def create_register_params(phone_number, area_code="86", verification_code="", **kwargs):
    """创建注册参数"""
    default_params = {
        'platformType': 0,
        'appType': 0,
        'variantType': 0,
        'appVersion': '2.1.3',
        'buildVersion': 317,
        'osModel': 'RMX3511',
        'osVersion': '33',
        'language': 'ar',
        'uniqueId': kwargs.get('uniqueId', '00026a07e2434812b65b0c3b40678afe'),
        'adid': None,
        'uuid': '9fcd8047c27442138fdbdcddcb026ebd',
        'gaid': None,
        'deviceId': 'be825900787d419f9872eed48566f45c',
        'widevineId': None,
        'idfv': None,
        'idfa': None,
        'tablet': 0,
        'simulator': 0,
        'useVpn': 0,
        'vpnAddress': None,
        'useRoot': 0,
        'useDebug': 0,
        'mockLocation': 0,
        'timezone': 'Asia/Shanghai',
        'languageCountry': 'CN',
        'mcc': None,
        'mnc': None,
        'networkName': None,
        'appLanguage': 'en',
        'inviteCode': None,
        'downloadChannel': None,
        'ipAddress': '41.235.64.230',
        'areaCode': area_code,
        'phoneNumber': phone_number,
        'verificationCode': verification_code,
    }
    default_params.update(kwargs)
    return default_params


def register_user(params, encrypt_key):
    """注册用户"""
    try:
        url = f"{settings.BASE_URL}{REGISTER_PATH}"
        headers = settings.build_common_encrypted_headers()

        response = HttpUtils.post(
            url=url,
            data=params,
            headers=headers,
            encrypt_key=encrypt_key,
        )
        return response
    except Exception as e:
        logger.error(f"注册失败: {e}")
        return {'code': 500, 'message': f'服务器内部错误: {str(e)}'}


def test_create_send_code_params_contains_required_fields():
    phone_number = REGISTER_TEST_PHONE
    params = create_send_code_params(phone_number)

    assert params["phoneNumber"] == phone_number
    assert params["areaCode"] == "86"
    assert params["userSmsType"] == 0
    assert "ipAddress" in params


def test_create_register_params_contains_required_fields():
    phone_number = REGISTER_TEST_PHONE
    verification_code = "8888"
    params = create_register_params(phone_number, verification_code=verification_code)

    assert params["phoneNumber"] == phone_number
    assert params["verificationCode"] == verification_code
    assert params["areaCode"] == "86"
    assert "uniqueId" in params


def print_allocation_statistics():
    """打印uniqueId分配统计信息"""
    unique_id_usage = {}
    for test_case in TEST_CASES:
        unique_id = test_case['uniqueId']
        if unique_id not in unique_id_usage:
            unique_id_usage[unique_id] = []
        unique_id_usage[unique_id].append(test_case['phone_number'])

    for unique_id, phones in unique_id_usage.items():
        logger.info(f"uniqueId: {unique_id}")
        logger.info(f"  分配数量: {len(phones)}")
        logger.info(f"  分配比例: {len(phones)/len(TEST_CASES):.1%}")
        if phones:
            sample = phones[:3]
            sample_str = ", ".join(sample)
            if len(phones) > 3:
                sample_str += f", ...等{len(phones)}个"
            logger.info(f"  手机号示例: {sample_str}")

    counts = [len(phones) for phones in unique_id_usage.values()]
    if counts:
        min_count = min(counts)
        max_count = max(counts)
        logger.info(f"分配均衡性: 最小{min_count}个，最大{max_count}个")
        if max_count - min_count <= 1:
            logger.info("✓ 分配非常均衡")
        elif max_count - min_count <= 2:
            logger.info("✓ 分配基本均衡")
        else:
            logger.info("⚠ 分配不够均衡")


@pytest.mark.api
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda x: f"phone={x['phone_number']}")
def test_send_code_api(test_case, encrypt_key):
    """测试发送验证码API，手机号随机匹配uniqueId"""
    if test_case['phone_number'] == TEST_CASES[0]['phone_number']:
        print_allocation_statistics()

    send_code_params = create_send_code_params(
        phone_number=test_case['phone_number'],
        uniqueId=test_case['uniqueId'],
    )
    time.sleep(3)
    response = send_verification_code(send_code_params, encrypt_key)

    logger.info(f"手机号={test_case['phone_number']}, uniqueId={test_case['uniqueId']}, 响应={response}")
    assert response is not None
    assert isinstance(response, dict)
    assert ("code" in response) or ("stayCode" in response) or (response.get("stayIsSuccess") is True)


@pytest.mark.api
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda x: f"phone={x['phone_number']}")
def test_register_api(test_case, encrypt_key):
    """测试注册API，手机号随机匹配uniqueId"""
    # 发送验证码
    send_code_params = create_send_code_params(
        phone_number=test_case['phone_number'],
        uniqueId=test_case['uniqueId'],
    )
    time.sleep(3)
    send_code_response = send_verification_code(send_code_params, encrypt_key)
    logger.info(f"[注册前发码] 手机号={test_case['phone_number']}, uniqueId={test_case['uniqueId']}, 响应={send_code_response}")

    assert send_code_response is not None
    assert isinstance(send_code_response, dict)
    assert ("code" in send_code_response) or ("stayCode" in send_code_response) or (send_code_response.get("stayIsSuccess") is True)

    # 注册用户
    verification_code = "8888"
    register_params = create_register_params(
        phone_number=test_case['phone_number'],
        verification_code=verification_code,
        uniqueId=test_case['uniqueId'],
    )

    response = register_user(register_params, encrypt_key)

    logger.info(f"[注册请求] 手机号={test_case['phone_number']}, uniqueId={test_case['uniqueId']}, 响应={response}")

    assert response is not None
    assert isinstance(response, dict)
    assert ("code" in response) or ("stayCode" in response) or (response.get("stayIsSuccess") is True)

    if response.get("code") == 0:
        logger.info(f"手机号 {test_case['phone_number']} 注册成功，uniqueId={test_case['uniqueId']}")
    else:
        error_message = extract_error_message(response)
        logger.info(f"手机号 {test_case['phone_number']} 注册失败，uniqueId={test_case['uniqueId']}，code={response.get('code')}，message={error_message}")
        pytest.fail(f"注册失败: code={response.get('code')}, message={error_message}")
