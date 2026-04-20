import pytest
import sys
import csv
import random
import time  # 添加time模块
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.http_utils import HttpUtils
from config import settings

REGISTER_TEST_PHONE = "13900011111"


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
        # 如果没有uniqueId，使用默认值
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
random.seed(42)  # 固定随机种子，使测试结果可重复
TEST_CASES = create_balanced_random_allocation()

def send_verification_code(params, encrypt_key):
    """发送验证码"""
    try:
        url = f"{settings.BASE_URL}{settings.SEND_CODE_PATH}"
        headers = settings.build_common_encrypted_headers()

        response = HttpUtils.post(
            url=url,
            data=params,
            headers=headers,
            encrypt_key=encrypt_key
        )
        return response
    except Exception as e:
        print(f"发送验证码失败: {str(e)}")
        return {'code': 500, 'message': f'服务器内部错误: {str(e)}'}

def create_send_code_params(phone_number, area_code="86", user_sms_type=0, **kwargs):
    """创建发送验证码的参数
    
    Args:
        phone_number: 手机号码
        area_code: 区号，默认86
        user_sms_type: 短信类型，0: 注册, 1: 登录, 2: 修改密码, 3: 找回密码登录, 4: 绑定手机
        **kwargs: 其他可选参数，包括uniqueId等
    
    Returns:
        完整的发送验证码参数
    """
    default_params = {
        'platformType': 0,  # android
        'appType': 0,  # 主包
        'variantType': 0,  # 主包
        'appVersion': '2.1.3',  # 应用版本（与线上一致）
        'buildVersion': 317,  # 编译版本
        'osModel': 'RMX3511',  # 设备型号（与线上一致）
        'osVersion': '33',  # 系统版本（与线上一致）
        'language': 'ar',  # 语言（与线上一致）
        'uniqueId': kwargs.get('uniqueId', '00026a07e2434812b65b0c3b40678afe'),  # 设备标识（从CSV读取）
        'userSmsType': user_sms_type,  # 短信类型
        'areaCode': area_code,  # 区号
        'phoneNumber': phone_number,  # 手机号码
        'validate': kwargs.get('validate'),  # google验证码校验
        'remoteIp': '41.235.64.230',  # 远程ip（使用默认值）
        'ipAddress': '41.235.64.230'  # IP地址（使用默认值）
    }
    
    # 更新默认参数
    default_params.update(kwargs)
    
    return default_params

def create_register_params(phone_number, area_code="86", verification_code="", **kwargs):
    """创建注册参数
    
    Args:
        phone_number: 手机号码
        area_code: 区号，默认86
        verification_code: 验证码
        **kwargs: 其他可选参数，包括uniqueId等
    
    Returns:
        完整的注册参数
    """
    default_params = {
        # 基础信息
        'platformType': 0,  # android
        'appType': 0,  # 主包
        'variantType': 0,  # 主包
        'appVersion': '2.1.3',  # 应用版本（与线上一致）
        'buildVersion': 317,  # 编译版本
        'osModel': 'RMX3511',  # 设备型号（与线上一致）
        'osVersion': '33',  # 系统版本（与线上一致）
        'language': 'ar',  # 语言（与线上一致）
        
        # 设备标识信息（从CSV读取uniqueId，其他使用默认值）
        'uniqueId': kwargs.get('uniqueId', '00026a07e2434812b65b0c3b40678afe'),  # 唯一码
        'adid': None,  # adjust广告标识
        'uuid': '9fcd8047c27442138fdbdcddcb026ebd',  # 客户端生成id（默认值）
        'gaid': None,  # google广告标识
        'deviceId': 'be825900787d419f9872eed48566f45c',  # 设备id（默认值）
        'widevineId': None,  # 数字版权id
        'idfv': None,  # ios标识符
        'idfa': None,  # ios广告标识符
        
        # 设备环境信息
        'tablet': 0,  # 是否为平板
        'simulator': 0,  # 是否为模拟器
        'useVpn': 0,  # 是否使用vpn
        'vpnAddress': None,  # 代理的vpn地址
        'useRoot': 0,  # 是否已经root
        'useDebug': 0,  # 是否开启debug调试
        'mockLocation': 0,  # 是否允许模拟位置
        'timezone': 'Asia/Shanghai',  # 时区
        'languageCountry': 'CN',  # 语言国家
        'mcc': None,  # 移动设备国家代码
        'mnc': None,  # 移动设备网络代码
        'networkName': None,  # 网络运营商名称
        'appLanguage': 'en',  # 应用语言
        'inviteCode': None,  # 邀请码
        'downloadChannel': None,  # 下载渠道
        'ipAddress': '41.235.64.230',  # IP地址（使用默认值）
        
        # 登录信息
        'areaCode': area_code,  # 手机区号
        'phoneNumber': phone_number,  # 手机号码
        'verificationCode': verification_code  # 验证码
    }
    
    # 更新默认参数
    default_params.update(kwargs)
    
    return default_params

def register_user(params, encrypt_key):
    """注册用户"""
    try:
        url = f"{settings.BASE_URL}{settings.REGISTER_PATH}"
        headers = settings.build_common_encrypted_headers()

        response = HttpUtils.post(
            url=url,
            data=params,
            headers=headers,
            encrypt_key=encrypt_key
        )
        return response
    except Exception as e:
        print(f"注册失败: {str(e)}")
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
        print(f"uniqueId: {unique_id}")
        print(f"  分配数量: {len(phones)}")
        print(f"  分配比例: {len(phones)/len(TEST_CASES):.1%}")
        # 显示前3个手机号作为示例
        if phones:
            sample = phones[:3]
            sample_str = ", ".join(sample)
            if len(phones) > 3:
                sample_str += f", ...等{len(phones)}个"
            print(f"  手机号示例: {sample_str}")
        
    
    # 验证分配是否均衡
    counts = [len(phones) for phones in unique_id_usage.values()]
    if counts:
        min_count = min(counts)
        max_count = max(counts)
        print(f"分配均衡性: 最小{min_count}个，最大{max_count}个")
        if max_count - min_count <= 1:
            print("✓ 分配非常均衡")
        elif max_count - min_count <= 2:
            print("✓ 分配基本均衡")
        else:
            print("⚠ 分配不够均衡")
    


@pytest.mark.api
@pytest.mark.parametrize("test_case", TEST_CASES, ids=lambda x: f"phone={x['phone_number']}")
def test_send_code_api(test_case, encrypt_key):
    """测试发送验证码API，手机号随机匹配uniqueId"""
    # 只在第一个测试用例时打印统计信息
    if test_case['phone_number'] == TEST_CASES[0]['phone_number']:
        print_allocation_statistics()
    
    send_code_params = create_send_code_params(
        phone_number=test_case['phone_number'],
        uniqueId=test_case['uniqueId']
    )
    # 避免请求过于频繁，先等待
    time.sleep(3)
    response = send_verification_code(send_code_params, encrypt_key)

    print(f"[发送验证码] 手机号={test_case['phone_number']}, uniqueId={test_case['uniqueId']}, 响应={response}")
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
        uniqueId=test_case['uniqueId']
    )
    # 避免请求过于频繁，先等待
    time.sleep(3)
    send_code_response = send_verification_code(send_code_params, encrypt_key)
    print(f"[注册前发码] 手机号={test_case['phone_number']}, uniqueId={test_case['uniqueId']}, 响应={send_code_response}")

    assert send_code_response is not None
    assert isinstance(send_code_response, dict)
    assert ("code" in send_code_response) or ("stayCode" in send_code_response) or (send_code_response.get("stayIsSuccess") is True)

    # 注册用户
    verification_code = "8888"
    register_params = create_register_params(
        phone_number=test_case['phone_number'],
        verification_code=verification_code,
        uniqueId=test_case['uniqueId']
    )
    
    response = register_user(register_params, encrypt_key)

    print(f"[注册请求] 手机号={test_case['phone_number']}, uniqueId={test_case['uniqueId']}, 响应={response}")

    assert response is not None
    assert isinstance(response, dict)
    assert ("code" in response) or ("stayCode" in response) or (response.get("stayIsSuccess") is True)

    if response.get("code") == 0:
        print(f"[注册结果] 手机号 {test_case['phone_number']} 注册成功，uniqueId={test_case['uniqueId']}")
    else:
        error_message = response.get("message") or response.get("msg") or "未知错误"
        print(f"[注册结果] 手机号 {test_case['phone_number']} 注册失败，uniqueId={test_case['uniqueId']}，code={response.get('code')}，message={error_message}")
        pytest.fail(f"注册失败: code={response.get('code')}, message={error_message}")