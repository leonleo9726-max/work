"""日志脱敏 module。"""

import logging
import re
from collections.abc import Mapping, Sequence
from typing import Any

_SECRET_KEYS = {
    "authorization",
    "deviceid",
    "idfa",
    "idfv",
    "password",
    "sign",
    "staytoken",
    "token",
    "uniqueid",
    "widevineid",
}
_PHONE_KEYS = {"phone", "phonenumber", "phone_number"}
_PHONE_PATTERN = re.compile(r"(?<!\d)(1\d{2})\d{4}(\d{4})(?!\d)")
_SECRET_PATTERN = re.compile(
    r"(?i)((?:staytoken|token|uniqueid|deviceid|password)['\"]?\s*[:=]\s*['\"]?)[^'\",\s}\]]+"
)


def _mask_phone(value: Any) -> str:
    text = str(value)
    if len(text) >= 7:
        return f"{text[:3]}****{text[-4:]}"
    return "***"


def redact_sensitive(value: Any, key: str = "") -> Any:
    """递归复制数据，并遮盖令牌、设备标识与手机号。"""
    normalized_key = key.replace("-", "").replace("_", "").lower()
    if normalized_key in _SECRET_KEYS:
        return "***"
    if normalized_key in _PHONE_KEYS:
        return _mask_phone(value)
    if isinstance(value, Mapping):
        return {
            item_key: redact_sensitive(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str):
        value = _PHONE_PATTERN.sub(r"\1****\2", value)
        return _SECRET_PATTERN.sub(r"\1***", value)
    return value


class SensitiveDataFilter(logging.Filter):
    """在日志写出前统一遮盖敏感内容。"""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        record.msg = redact_sensitive(message)
        record.args = ()
        return True


def install_sensitive_data_filter() -> None:
    """为根 logger 的现有 handler 安装一次脱敏 filter。"""
    for handler in logging.getLogger().handlers:
        if not any(isinstance(item, SensitiveDataFilter) for item in handler.filters):
            handler.addFilter(SensitiveDataFilter())
