"""
统一认证/授权工具模块。

集中管理登录凭证的加载、保存、查询、业务 headers 构建等逻辑，
消除各测试文件和批量脚本中的重复代码。
"""

import json
import base64
from pathlib import Path
from typing import Optional

from config import settings

# 项目根目录（此文件位于 ApiAutomation/common/，向上两级）
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 凭证文件路径
LOGIN_CREDENTIALS_FILE = PROJECT_ROOT / "data" / "login_credentials.json"
BATCH_LOGIN_CREDENTIALS_FILE = PROJECT_ROOT / "data" / "batch_login_credentials.json"


# ============================================================
# 登录凭证管理
# ============================================================

# 内存中的登录凭证缓存
_LOGIN_CREDENTIALS: dict = {}


def _ensure_credentials_file():
    """确保凭证文件所在目录存在。"""
    if not LOGIN_CREDENTIALS_FILE.parent.exists():
        LOGIN_CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)


def save_login_credentials_to_json():
    """将内存中的登录凭证持久化到 JSON 文件。"""
    _ensure_credentials_file()
    with LOGIN_CREDENTIALS_FILE.open("w", encoding="utf-8") as file:
        json.dump(_LOGIN_CREDENTIALS, file, ensure_ascii=False, indent=2)


def load_login_credentials_from_json() -> dict:
    """从 JSON 文件加载登录凭证到内存。"""
    if not LOGIN_CREDENTIALS_FILE.exists():
        return {}
    try:
        with LOGIN_CREDENTIALS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file) or {}
            _LOGIN_CREDENTIALS.update(data)
            return data
    except (json.JSONDecodeError, IOError):
        return {}


def store_login_credentials(phone_number: str, login_info: dict):
    """存储登录凭证，保证 stayUserId 与 stayToken 一一对应。

    Args:
        phone_number: 手机号码。
        login_info: 包含 stayUserId 和 stayToken 的字典。

    Raises:
        AssertionError: 如果同一用户 ID 存在不同的 token。
    """
    if not login_info:
        return

    user_id = login_info["stayUserId"]
    token = login_info["stayToken"]

    existing = _LOGIN_CREDENTIALS.get(user_id)
    if existing and existing["stayToken"] != token:
        raise AssertionError(
            f"用户ID {user_id} 已存在不同 token：{existing['stayToken']} vs {token}"
        )

    _LOGIN_CREDENTIALS[user_id] = {
        "phone_number": phone_number,
        "stayUserId": user_id,
        "stayToken": token,
    }
    save_login_credentials_to_json()


def get_login_credentials_by_user_id(stay_user_id: str) -> Optional[dict]:
    """通过用户 ID 查询登录凭证。

    先查内存缓存，再查持久化文件。

    Args:
        stay_user_id: 用户 ID。

    Returns:
        登录凭证字典，未找到则返回 None。
    """
    user_id = str(stay_user_id)
    if user_id in _LOGIN_CREDENTIALS:
        return _LOGIN_CREDENTIALS[user_id]
    persisted = load_login_credentials_from_json()
    return persisted.get(user_id)


def get_login_credentials_by_phone(phone_number: str) -> Optional[dict]:
    """通过手机号查询登录凭证。

    先查内存缓存，再查持久化文件。

    Args:
        phone_number: 手机号码。

    Returns:
        登录凭证字典，未找到则返回 None。
    """
    for value in _LOGIN_CREDENTIALS.values():
        if value["phone_number"] == phone_number:
            return value
    persisted = load_login_credentials_from_json()
    for value in persisted.values():
        if value.get("phone_number") == phone_number:
            return value
    return None


def build_business_headers(stay_token: str) -> dict:
    """构建业务请求头。

    Args:
        stay_token: 登录后获取的 token。

    Returns:
        包含 token 的请求头字典。
    """
    headers = settings.build_common_encrypted_headers()
    headers["token"] = stay_token
    return headers


def build_business_headers_from_login(
    phone_number: Optional[str] = None,
    stay_user_id: Optional[str] = None,
) -> tuple:
    """从持久化登录凭证构建业务请求头。

    Args:
        phone_number: 手机号码（与 stay_user_id 二选一）。
        stay_user_id: 用户 ID（与 phone_number 二选一）。

    Returns:
        (headers, credential) 元组。

    Raises:
        ValueError: 未找到登录凭证或参数不足。
    """
    credential = None
    if phone_number:
        credential = get_login_credentials_by_phone(phone_number)
    elif stay_user_id:
        credential = get_login_credentials_by_user_id(stay_user_id)

    if credential is None:
        raise ValueError(
            "未找到登录凭证，请先执行登录并生成 data/login_credentials.json。"
        )

    headers = build_business_headers(credential["stayToken"])
    return headers, credential


# ============================================================
# 批量登录凭证加载（用于 batch_*.py 脚本）
# ============================================================


def load_batch_login_credentials() -> list:
    """从 JSON 文件加载批量登录凭证。

    优先使用 batch_login_credentials.json，其次使用 login_credentials.json。

    Returns:
        凭证字典列表，每个元素包含 stayUserId, phone_number, stayToken, uniqueId。

    Raises:
        SystemExit: 凭证文件不存在时退出。
    """
    if BATCH_LOGIN_CREDENTIALS_FILE.exists():
        credentials_file = BATCH_LOGIN_CREDENTIALS_FILE
    elif LOGIN_CREDENTIALS_FILE.exists():
        credentials_file = LOGIN_CREDENTIALS_FILE
    else:
        print("错误: 登录凭证文件不存在")
        print(f"  请检查以下文件是否存在:")
        print(f"    - {BATCH_LOGIN_CREDENTIALS_FILE}")
        print(f"    - {LOGIN_CREDENTIALS_FILE}")
        print("请先运行 batch_login.py --save-credentials 生成登录凭证")
        import sys
        sys.exit(1)

    with credentials_file.open("r", encoding="utf-8") as f:
        credentials = json.load(f)

    credential_list = []
    for key, cred in credentials.items():
        # key 可能是手机号（batch_login_credentials.json）或 stayUserId（login_credentials.json）
        stay_user_id = cred.get("stayUserId", key)
        credential_list.append({
            "stayUserId": stay_user_id,
            "phone_number": cred.get("phone_number", key),
            "stayToken": cred.get("stayToken", ""),
            "uniqueId": cred.get("uniqueId", ""),
        })

    return credential_list


# ============================================================
# 工具函数
# ============================================================


def to_base64(value: str) -> Optional[str]:
    """将字符串转为 base64 编码。

    Args:
        value: 原始字符串。

    Returns:
        Base64 编码后的字符串，输入为 None 时返回 None。
    """
    if value is None:
        return None
    return base64.b64encode(str(value).encode("utf-8")).decode("utf-8")
