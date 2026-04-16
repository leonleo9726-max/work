import sys
import os
import requests
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.sign_utils import SignUtils

class HttpUtils:
    @staticmethod
    def get(url, headers=None, params=None):
        """发送GET请求"""
        try:
            response = requests.get(
                url=url,
                headers=headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"GET请求失败: {e}")
            return None
    
    @staticmethod
    def post(url, data=None, headers=None, encrypt_key=None, locale="zh", timestamp=None):
        """发送POST请求"""
        try:
            # 如果需要加密
            if encrypt_key and data:
                # 生成签名
                if not timestamp:
                    import time
                    timestamp = str(int(time.time() * 1000))
                
                sign = SignUtils.generate_sign(data, locale, timestamp, encrypt_key)
                
                # 加密数据
                encrypted_data = SignUtils.encrypt(data, encrypt_key)
                
                # 更新headers
                if headers is None:
                    headers = {}
                headers['content-type'] = 'application/json'
                headers['locale'] = locale
                headers['timestamp'] = timestamp
                headers['sign'] = sign
                
                # 发送加密数据
                response = requests.post(
                    url=url,
                    data=encrypted_data,
                    headers=headers,
                    timeout=30
                )
            else:
                # 发送未加密数据
                response = requests.post(
                    url=url,
                    json=data,
                    headers=headers,
                    timeout=30
                )
            
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"POST请求失败: {e}")
            return None