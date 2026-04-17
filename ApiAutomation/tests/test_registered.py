import pytest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.http_utils import HttpUtils
from config import settings

REGISTER_TEST_PHONE = "13900011111"

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
        **kwargs: 其他可选参数
    
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
        'uniqueId': '00026a07e2434812b65b0c3b40678afe',  # 设备标识（与线上一致）
        'userSmsType': user_sms_type,  # 短信类型
        'areaCode': area_code,  # 区号
        'phoneNumber': phone_number,  # 手机号码
        'validate': kwargs.get('validate'),  # google验证码校验
        'remoteIp': '41.235.64.230',  # 远程ip（与线上一致）
        'ipAddress': '41.235.64.230'  # IP地址（后端需要）
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
        **kwargs: 其他可选参数
    
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
        
        # 设备标识信息
        'uniqueId': '00026a07e2434812b65b0c3b40678afe',  # 唯一码（与线上一致）
        'adid': None,  # adjust广告标识
        'uuid': '9fcd8047c27442138fdbdcddcb026ebd',  # 客户端生成id
        'gaid': None,  # google广告标识
        'deviceId': 'be825900787d419f9872eed48566f45c',  # 设备id
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
        'ipAddress': '41.235.64.230',  # IP地址（后端需要）
        
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


@pytest.mark.api
@pytest.mark.parametrize("phone_number", [REGISTER_TEST_PHONE])
def test_send_code_api(phone_number, encrypt_key):
    send_code_params = create_send_code_params(phone_number)
    response = send_verification_code(send_code_params, encrypt_key)

    print(f"[发送验证码] 手机号={phone_number}, 响应={response}")
    assert response is not None
    assert isinstance(response, dict)
    assert "code" in response


@pytest.mark.api
@pytest.mark.parametrize("phone_number,verification_code", [(REGISTER_TEST_PHONE, "8888")])
def test_register_api(phone_number, verification_code, encrypt_key):
    register_params = create_register_params(
        phone_number=phone_number,
        verification_code=verification_code
    )
    response = register_user(register_params, encrypt_key)

    print(f"[注册请求] 手机号={phone_number}, 响应={response}")

    assert response is not None
    assert isinstance(response, dict)
    assert "code" in response

    if response.get("code") == 0:
        print(f"[注册结果] 手机号 {phone_number} 注册成功")
    else:
        error_message = response.get("message") or response.get("msg") or "未知错误"
        print(f"[注册结果] 手机号 {phone_number} 注册失败，code={response.get('code')}，message={error_message}")
        pytest.fail(f"注册失败: code={response.get('code')}, message={error_message}")