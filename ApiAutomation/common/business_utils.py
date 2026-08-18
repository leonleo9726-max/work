"""业务公共工具模块 — 统一成功判定、错误提取、请求头构建、红包ID提取。"""

import json
import logging
from common.auth_utils import build_business_headers
from common.response_utils import (
    extract_error_details as _extract_error_details,
    extract_stay_red_packet_id as _extract_stay_red_packet_id,
    is_api_success,
)

_log = logging.getLogger("api_test")


def is_success(response):
    """判断接口响应是否成功"""
    return is_api_success(response)


def get_error_details(response):
    """从响应中提取错误信息"""
    return _extract_error_details(response)


def extract_stay_red_packet_id(response):
    """从发红包接口响应中提取 stayRedPacketId"""
    return _extract_stay_red_packet_id(response)


def check_success_or_fail(response, context="操作"):
    """成功返回 None，失败返回错误信息字符串。用于非 pytest 场景（批量脚本）。"""
    if is_success(response):
        return None
    return f"{context}失败: {get_error_details(response)}"


def require_success(response, context="操作"):
    """断言成功，失败时抛出 RuntimeError。"""
    err = check_success_or_fail(response, context)
    if err:
        raise RuntimeError(err)
    return True


def load_json_credentials(file_path):
    """加载 JSON 凭证文件，统一容错处理。"""
    if not file_path.exists():
        _log.error("凭证文件不存在: %s", file_path)
        return {}
    try:
        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, IOError) as e:
        _log.error("凭证文件读取失败: %s — %s", file_path, e)
        return {}


def setup_logging(level=logging.INFO, log_file=None):
    """统一日志配置，所有模块共享 'api_test' logger。"""
    logger = logging.getLogger("api_test")
    logger.setLevel(level)
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        handler = logging.FileHandler(log_file, encoding="utf-8") if log_file else logging.StreamHandler()
        handler.setFormatter(fmt)
        logger.addHandler(handler)


def credentials_to_list(credentials):
    """将 {key: {stayUserId, stayToken, ...}} 转为列表，兼容两种 JSON 结构。"""
    result = []
    for key, cred in credentials.items():
        result.append({
            "stayUserId": str(cred.get("stayUserId", key)),
            "phone_number": cred.get("phone_number", key),
            "stayToken": cred.get("stayToken", ""),
            "uniqueId": cred.get("uniqueId", ""),
        })
    return result
