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

# ============================================================
# 统一处理 sys.path
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================
# 日志配置
# ============================================================

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"


def configure_logging(level=logging.INFO):
    """配置全局日志。

    Args:
        level: 日志级别，默认 INFO。
    """
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        stream=sys.stdout,
    )


# 默认启用日志
configure_logging()

# ============================================================
# pytest 配置
# ============================================================


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
