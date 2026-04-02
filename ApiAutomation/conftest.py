import pytest
import requests

# 示例 1: 定义一个全局的基础 URL，方便切换环境
@pytest.fixture(scope="session")
def base_url():
    return "https://httpbin.org"

# 示例 2: 定义一个公共的请求头（包含 Token 等）
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