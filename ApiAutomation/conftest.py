import pytest
import requests

#封装sing签名
from common.sign_utils import Signer

@pytest.fixture
def api_headers():
    """生成包含签名的请求头"""
    def _create_headers(payload=None):
        app_key = "test_user_01"
        app_secret = "abc123456" # 实际项目中建议放在配置文件
        timestamp = str(int(time.time()))
        nonce = str(uuid.uuid4())
        
        # 需要参与签名的字段
        sign_params = {
            "app_key": app_key,
            "timestamp": timestamp,
            "nonce": nonce
        }
        # 如果业务要求业务参数也参与签名，则合并
        if payload:
            sign_params.update(payload)
            
        signature = Signer.generate_signature(sign_params, app_secret)
        
        return {
            "Content-Type": "application/json",
            "X-App-Key": app_key,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature
        }
    return _create_headers

# 定义一个公共的请求头（包含 Token 等）
@pytest.fixture(scope="function")
def common_headers():
    return {
        "User-Agent": "ApiAutomation-Test",
        "Content-Type": "application/json"
    }



# 示例 3: 模拟登录，获取一个 Session 对象
@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    # 这里可以写登录逻辑，session.post(login_url, data=...)
    yield session
    session.close() # 测试结束后关闭会话