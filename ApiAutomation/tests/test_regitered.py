import requests
import pytest
from common.sign_utils import generate_heard_sign

class TestUser:
    
    # 使用参数化，方便测试多个手机号或异常情况
    @pytest.mark.parametrize("phone, area_code", [
        ("15200711072", "86"),
        ("13800138000", "86")
    ])
    def test_phone_registered_status(self, base_url, default_headers, phone, area_code):
        endpoint = f"{base_url}/user/stay/phone/registered"
        
        # 组装请求参数
        params = {
            'stayAppType': '0',
            'stayAreaCode': area_code,
            'stayPhoneNumber': phone,
            'stayUniqueId': 'bac1131e82cd4c738e3199375ffe77b4'
        }
        
        # 动态处理 Header (heard 签名)
        timestamp = "1775101261010" # 实际可用 str(int(time.time()*1000))
        headers = default_headers.copy()
        headers['timestamp'] = timestamp
        headers['sign'] = "8db71757aaf14142c0844e593a7ea0bf591067ecfe6917e9e3a4a089c016a9d3" # 或调用 sign_utils

        # 发起请求
        response = requests.get(endpoint, params=params, headers=headers)
        
        # 断言
        assert response.status_code == 200
        json_data = response.json()
        # 假设业务成功 code 为 0 或 200
        assert "code" in json_data, "返回结构不完整"