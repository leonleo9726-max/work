"""
统一响应处理工具模块。

集中管理 API 响应成功判断、错误信息提取、红包 ID 提取等逻辑，
消除各测试文件和批量脚本中的重复代码。
"""

from typing import Any, Optional


def is_api_success(response: Any) -> bool:
    """判断 API 响应是否成功。

    支持多种后端响应结构：
    - {"code": 0, "data": {...}}
    - {"stayCode": 200, "stayResult": {...}}
    - {"stayIsSuccess": true}
    - {"success": true}
    - {"status": "success"}

    Args:
        response: API 返回的 JSON 响应（字典）或 None。

    Returns:
        成功返回 True，否则返回 False。
    """
    if not isinstance(response, dict):
        return False

    # 检查 stayCode
    stay_code = response.get("stayCode")
    if stay_code in (0, "0", 200, "200"):
        return True

    # 检查 stayIsSuccess
    if response.get("stayIsSuccess") is True:
        return True

    # 检查 code
    code = response.get("code")
    if code in (0, "0", 200, "200"):
        return True

    # 检查 success
    if response.get("success") is True:
        return True

    # 检查 status
    if response.get("status") in ("success", "ok", "SUCCESS", "OK"):
        return True

    # 检查 data 中是否包含 token
    data = response.get("data")
    if isinstance(data, dict):
        if data.get("token") or data.get("accessToken") or data.get("jwt"):
            return True

    return False


def extract_error_message(response: Any) -> str:
    """从 API 响应中提取错误信息。

    按优先级尝试多个可能的错误字段。

    Args:
        response: API 返回的 JSON 响应。

    Returns:
        提取到的错误信息字符串，未找到则返回 "未知错误"。
    """
    if not isinstance(response, dict):
        return "无效的响应格式"

    # 按优先级检查错误字段
    error_fields = [
        "stayErrorMessage",
        "stayMessage",
        "errorMessage",
        "message",
        "msg",
        "error",
    ]
    for field in error_fields:
        value = response.get(field)
        if value:
            return str(value)

    return "未知错误"


def extract_error_details(response: Any) -> str:
    """从 API 响应中提取详细的错误信息（含错误码）。

    Args:
        response: API 返回的 JSON 响应。

    Returns:
        包含错误码和错误信息的字符串。
    """
    if not isinstance(response, dict):
        return "无效的响应格式"

    parts = []

    # 检查错误码字段
    code_fields = ["stayCode", "code", "errorCode"]
    for field in code_fields:
        if field in response and response[field] is not None:
            parts.append(f"{field}: {response[field]}")

    # 检查错误信息字段
    error_fields = [
        "stayErrorMessage",
        "stayMessage",
        "errorMessage",
        "message",
        "msg",
        "error",
    ]
    for field in error_fields:
        if field in response and response[field]:
            parts.append(f"{field}: {response[field]}")

    if parts:
        return "; ".join(parts)
    return str(response)


def extract_stay_red_packet_id(response: Any) -> Optional[str]:
    """从发红包接口的响应中提取 stayRedPacketId。

    支持多种响应结构：
    - {"code": 0, "data": {"stayRedPacketId": "xxx"}}
    - {"stayCode": 200, "stayResult": {"stayRedPacketId": "xxx"}}
    - {"stayRedPacketId": "xxx"}
    - {"data": {"stayRedPacketId": "xxx"}}

    Args:
        response: 发红包接口返回的 JSON 响应。

    Returns:
        红包 ID 字符串，未找到则返回 None。
    """
    if not isinstance(response, dict):
        return None

    # 尝试从 stayResult 中提取
    stay_result = response.get("stayResult")
    if isinstance(stay_result, dict):
        red_packet_id = stay_result.get("stayRedPacketId")
        if red_packet_id is not None:
            return str(red_packet_id)

    # 尝试从 data 中提取
    data = response.get("data")
    if isinstance(data, dict):
        red_packet_id = data.get("stayRedPacketId")
        if red_packet_id is not None:
            return str(red_packet_id)

    # 尝试从响应顶层提取
    red_packet_id = response.get("stayRedPacketId")
    if red_packet_id is not None:
        return str(red_packet_id)

    return None


def extract_login_info(response: Any) -> Optional[dict]:
    """从登录响应中提取 stayUserId 和 stayToken。

    Args:
        response: 登录接口返回的 JSON 响应。

    Returns:
        包含 stayUserId 和 stayToken 的字典，未找到则返回 None。
    """
    if not isinstance(response, dict):
        return None

    candidates = []
    if isinstance(response.get("stayResult"), dict):
        candidates.append(response["stayResult"])
    if isinstance(response.get("data"), dict):
        candidates.append(response["data"])
    candidates.append(response)

    for data in candidates:
        if not isinstance(data, dict):
            continue
        stay_user_id = data.get("stayUserId")
        stay_token = data.get("stayToken")
        if stay_user_id and stay_token:
            return {
                "stayUserId": str(stay_user_id),
                "stayToken": str(stay_token),
            }
    return None
