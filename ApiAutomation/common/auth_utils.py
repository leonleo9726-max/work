"""
统一认证/授权工具模块。

集中管理登录凭证的加载、保存、查询、业务 headers 构建等逻辑，
消除各测试文件和批量脚本中的重复代码。
"""

import json
import threading
from collections.abc import Callable
from pathlib import Path

from config import settings

# 项目根目录（此文件位于 ApiAutomation/common/，向上两级）
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 凭证文件路径
LOGIN_CREDENTIALS_FILE = PROJECT_ROOT / "data" / "local" / "login_credentials.json"
BATCH_LOGIN_CREDENTIALS_FILE = PROJECT_ROOT / "data" / "local" / "batch_login_credentials.json"


# ============================================================
# 登录凭证管理
# ============================================================

class CredentialRepository:
    """以 JSON 文件持久化登录凭证的仓库。"""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._credentials: dict[str, dict] = {}
        self._lock = threading.RLock()

    def load(self) -> dict:
        with self._lock:
            if not self.path.exists():
                self._credentials = {}
                return {}
            try:
                with self.path.open("r", encoding="utf-8") as file:
                    data = json.load(file) or {}
            except (json.JSONDecodeError, OSError):
                self._credentials = {}
                return {}
            if not isinstance(data, dict):
                self._credentials = {}
                return {}
            self._credentials = data
            return data.copy()

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
            with temporary_path.open("w", encoding="utf-8") as file:
                json.dump(self._credentials, file, ensure_ascii=False, indent=2)
            temporary_path.replace(self.path)

    def store(self, phone_number: str, login_info: dict) -> dict | None:
        if not login_info:
            return None
        try:
            user_id = str(login_info["stayUserId"])
            token = str(login_info["stayToken"])
        except KeyError as error:
            raise ValueError(f"登录响应缺少必需字段: {error.args[0]}") from error

        with self._lock:
            if not self._credentials:
                self.load()
            existing = self._credentials.get(user_id)
            if existing and existing.get("stayToken") != token:
                raise ValueError(f"用户 {user_id} 已存在不同凭证")

            credential = {
                "phone_number": phone_number,
                "stayUserId": user_id,
                "stayToken": token,
            }
            if login_info.get("uniqueId"):
                credential["uniqueId"] = login_info["uniqueId"]
            self._credentials[user_id] = credential
            self.save()
            return credential.copy()

    def get_by_user_id(self, stay_user_id: str) -> dict | None:
        with self._lock:
            if not self._credentials:
                self.load()
            user_id = str(stay_user_id)
            credential = self._credentials.get(user_id)
            if credential:
                return credential.copy()
            for candidate in self._credentials.values():
                if str(candidate.get("stayUserId")) == user_id:
                    return candidate.copy()
            return None

    def get_by_phone(self, phone_number: str) -> dict | None:
        with self._lock:
            if not self._credentials:
                self.load()
            for credential in self._credentials.values():
                if credential.get("phone_number") == phone_number:
                    return credential.copy()
            return None


_DEFAULT_REPOSITORY = CredentialRepository(LOGIN_CREDENTIALS_FILE)
_BATCH_REPOSITORY = CredentialRepository(BATCH_LOGIN_CREDENTIALS_FILE)


def save_login_credentials_to_json():
    """将内存中的登录凭证持久化到 JSON 文件。"""
    _DEFAULT_REPOSITORY.save()


def load_login_credentials_from_json() -> dict:
    """从 JSON 文件加载登录凭证到内存。"""
    return _DEFAULT_REPOSITORY.load()


def store_login_credentials(phone_number: str, login_info: dict):
    """存储登录凭证，保证 stayUserId 与 stayToken 一一对应。

    Args:
        phone_number: 手机号码。
        login_info: 包含 stayUserId 和 stayToken 的字典。

    Raises:
        ValueError: 如果登录信息无效或同一用户 ID 存在不同凭证。
    """
    return _DEFAULT_REPOSITORY.store(phone_number, login_info)


def get_login_credentials_by_user_id(stay_user_id: str) -> dict | None:
    """通过用户 ID 查询登录凭证。

    先查内存缓存，再查持久化文件。

    Args:
        stay_user_id: 用户 ID。

    Returns:
        登录凭证字典，未找到则返回 None。
    """
    return _DEFAULT_REPOSITORY.get_by_user_id(
        stay_user_id
    ) or _BATCH_REPOSITORY.get_by_user_id(stay_user_id)


def get_login_credentials_by_phone(phone_number: str) -> dict | None:
    """通过手机号查询登录凭证。

    先查内存缓存，再查持久化文件。

    Args:
        phone_number: 手机号码。

    Returns:
        登录凭证字典，未找到则返回 None。
    """
    return _DEFAULT_REPOSITORY.get_by_phone(
        phone_number
    ) or _BATCH_REPOSITORY.get_by_phone(phone_number)


def ensure_login_credentials(
    phone_number: str,
    encrypt_key: str,
    *,
    login: Callable[[str, str], dict] | None = None,
    repository: CredentialRepository | None = None,
) -> dict:
    """返回手机号凭证；缺失时通过可替换的登录 adapter 获取并保存。"""
    credential_repository = repository or _DEFAULT_REPOSITORY
    credential = credential_repository.get_by_phone(phone_number)
    if credential:
        return credential

    if login is None:
        from common.login_operations import login_phone

        login = login_phone
    login_info = login(phone_number, encrypt_key)
    credential = credential_repository.store(phone_number, login_info)
    if credential is None:
        raise RuntimeError("登录成功但未返回可保存的凭证")
    return credential


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
    phone_number: str | None = None,
    stay_user_id: str | None = None,
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
            "未找到登录凭证，请先执行登录并生成 data/local/login_credentials.json。"
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
        FileNotFoundError: 本地凭证文件不存在。
    """
    if BATCH_LOGIN_CREDENTIALS_FILE.exists():
        credentials_file = BATCH_LOGIN_CREDENTIALS_FILE
    elif LOGIN_CREDENTIALS_FILE.exists():
        credentials_file = LOGIN_CREDENTIALS_FILE
    else:
        raise FileNotFoundError(
            "登录凭证不存在；请先运行 batch_login.py --save-credentials，"
            "或在 data/local/ 中放置本地凭证"
        )

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
