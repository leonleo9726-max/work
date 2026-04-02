import pytest

@pytest.fixture(scope="session")
def base_url():
    return "https://api.eastpointtest.com"

@pytest.fixture(scope="function")
def default_headers():
    """基础请求头信息"""
    return {
        'content-type': 'application/json',
        'locale': 'zh',
        'appLanguage': 'en',
        'app-type': '0',
        'content-sign': 'sat1',
        'content-status': '1',
        'platform-type': '0',
        'variant-type': '0',
        'build-version': '317'
    }