import pytest

from common.response_utils import is_api_success


pytestmark = pytest.mark.unit


def test_accepts_a_successful_response_with_one_indicator():
    assert is_api_success({"code": 0})


def test_rejects_conflicting_success_indicators():
    assert not is_api_success({"code": 0, "success": False})
    assert not is_api_success({"stayCode": 200, "status": "failed"})


def test_rejects_a_response_without_success_indicators():
    assert not is_api_success({"data": {"value": "unknown"}})
