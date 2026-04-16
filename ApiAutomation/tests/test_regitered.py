import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.http_utils import HttpUtils
from common.sign_utils import SignUtils

def send_verification_code(params):
    """发送验证码"""
    try:
        # API地址
        url = "https://api.eastpointtest.com/user/stay/send-code"
        
        # 请求头
        headers = {
            'appLanguage': 'en',
            'app-language': 'en',
            'app-type': '0',
            'content-sign': 'sat1',
            'content-status': '1',
            'platform-type': '0',
            'variant-type': '0',
            'build-version': '317'
        }
        
        # 发送加密请求
        response = HttpUtils.post(
            url=url,
            data=params,
            headers=headers,
            encrypt_key=SignUtils.test_encrypt_key
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

def register_user(params):
    """注册用户"""
    try:
        # API地址
        url = "https://api.eastpointtest.com/user/stay/login/phone"
        
        # 请求头
        headers = {
            'appLanguage': 'en',
            'app-language': 'en',
            'app-type': '0',
            'content-sign': 'sat1',
            'content-status': '1',
            'platform-type': '0',
            'variant-type': '0',
            'build-version': '317'
        }
        
        # 发送加密请求
        response = HttpUtils.post(
            url=url,
            data=params,
            headers=headers,
            encrypt_key=test_encrypt_key
        )
        
        return response
        
    except Exception as e:
        print(f"注册失败: {str(e)}")
        return {'code': 500, 'message': f'服务器内部错误: {str(e)}'}

if __name__ == '__main__':
    # 循环注册从13800138001到13800138100
    start_number = 13900010001
    end_number = 13900010005
    
    for i in range(start_number, end_number + 1):
        phone_number = str(i)
        print(f"\n=== 开始处理手机号: {phone_number} ===")
        
        try:
            # 发送验证码
            send_code_params = create_send_code_params(phone_number)
            code_result = send_verification_code(send_code_params)
            print(f"发送验证码结果: {code_result}")
            
            # 休眠1秒，避免请求过快
            time.sleep(1)
            
            # 注册用户
            verification_code = "8888"  # 替换为收到的验证码
            register_params = create_register_params(phone_number, verification_code=verification_code)
            register_result = register_user(register_params)
            print(f"注册结果: {register_result}")
            
            # 休眠2秒，避免请求过快
            time.sleep(2)
            
        except Exception as e:
            print(f"处理手机号 {phone_number} 时出错: {str(e)}")
            # 出错时也休眠，避免请求过快
            time.sleep(1)
            continue  # 跳过错误，继续处理下一个
    
    print("\n=== 注册任务完成 ===")