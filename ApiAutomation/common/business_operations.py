"""认证后加密业务请求的统一 module。"""

import time

from common.auth_utils import build_business_headers
from common.http_utils import HttpUtils
from config import settings


def encrypted_business_request(
    path: str,
    payload: dict,
    credential: dict,
    *,
    encrypt_key: str | None = None,
    http=HttpUtils,
) -> dict:
    """隐藏 URL、鉴权 header、密钥读取与时间戳拼装。"""
    token = credential.get("stayToken")
    if not token:
        raise ValueError("credential 缺少 stayToken")
    return http.post(
        url=f"{settings.BASE_URL}{path}",
        data=payload,
        headers=build_business_headers(token),
        encrypt_key=encrypt_key or settings.require_encrypt_key(),
        locale="en",
        timestamp=str(int(time.time() * 1000)),
    )
