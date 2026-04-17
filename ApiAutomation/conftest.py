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
    return settings.BASE_URL

@pytest.fixture(scope="function")
def default_headers():
    """基础请求头信息"""
    return settings.DEFAULT_HEADERS.copy()


@pytest.fixture(scope="session")
def encrypt_key():
    return settings.TEST_ENCRYPT_KEY