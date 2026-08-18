"""统一的加密业务请求入口。"""

from typing import Any, Optional

from common.http_utils import HttpUtils
from config import settings


class EastPointClient:
    """封装 URL、认证头和加密传输，调用方只声明业务载荷。"""

    def __init__(self, encrypt_key: str, transport=HttpUtils, base_url: Optional[str] = None):
        if not encrypt_key:
            raise ValueError("缺少 EASTPOINT_TEST_ENCRYPT_KEY")
        self._encrypt_key = encrypt_key
        self._transport = transport
        self._base_url = (base_url or settings.BASE_URL).rstrip("/")

    def post(
        self,
        path: str,
        payload: dict,
        token: Optional[str] = None,
        locale: str = "en",
        timestamp: Optional[str] = None,
    ) -> Any:
        headers = settings.build_common_encrypted_headers()
        if token:
            headers["token"] = token
        return self._transport.post(
            url=f"{self._base_url}{path}",
            data=payload,
            headers=headers,
            encrypt_key=self._encrypt_key,
            locale=locale,
            timestamp=timestamp,
        )
