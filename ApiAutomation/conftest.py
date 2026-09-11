"""
pytest 全局配置。

统一处理：
1. sys.path 添加项目根目录（消除各文件的重复代码）
2. pytest 命令行选项（--run-api）
3. 全局 fixture（base_url, default_headers, encrypt_key）
4. 日志配置
"""

import logging
import sys
from pathlib import Path

import pytest
from config import settings


def pytest_addoption(parser):
    parser.addoption(
        "--run-api",
        action="store_true",
        default=False,
        help="run tests that call external APIs",
    )
    parser.addoption(
        "--login-mode",
        choices=("password", "phone"),
        default="password",
        help="login mode for tests/test_login_phone.py",
    )
    parser.addoption(
        "--phone",
        default="15200711073",
        help="phone number for tests/test_login_phone.py",
    )
    parser.addoption(
        "--code",
        default="8888",
        help="verification code for tests/test_login_phone.py",
    )
    parser.addoption(
        "--area",
        default="86",
        help="area code for tests/test_login_phone.py",
    )
    parser.addoption(
        "--password",
        default="a123456",
        help="password for tests/test_login_phone.py",
    )


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
    from config import settings
    return settings.TEST_ENCRYPT_KEY
