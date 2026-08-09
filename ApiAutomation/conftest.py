"""
pytest 全局配置。

统一处理：
1. sys.path 添加项目根目录（消除各文件的重复代码）
2. pytest 命令行选项（--run-api）
3. 全局 fixture（base_url, default_headers, encrypt_key）
4. 日志配置
"""


import pytest

from common.logging_utils import install_sensitive_data_filter
from config import settings


def pytest_addoption(parser):
    parser.addoption(
        "--run-api",
        action="store_true",
        default=False,
        help="run tests that call external APIs",
    )


def pytest_collection_modifyitems(config, items):
    """默认跳过所有真实 API 测试，只有 --run-api 显式放行。"""
    if config.getoption("--run-api"):
        return

    skip_api = pytest.mark.skip(reason="需要 --run-api 才能执行真实 API 测试")
    for item in items:
        if item.get_closest_marker("api") is not None:
            item.add_marker(skip_api)


def pytest_configure():
    install_sensitive_data_filter()


def pytest_runtest_setup():
    install_sensitive_data_filter()


@pytest.fixture(scope="session")
def base_url():
    from config import settings
    return settings.BASE_URL


@pytest.fixture(scope="function")
def default_headers():
    """基础请求头信息"""
    from config import settings
    return settings.DEFAULT_HEADERS.copy()


@pytest.fixture(scope="session")
def encrypt_key():
    return settings.require_encrypt_key()
