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
