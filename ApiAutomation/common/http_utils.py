"""可替换 transport 的 HTTP module。"""

import threading
import time
from typing import Any, Protocol

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common.sign_utils import SignUtils


class HttpRequestError(RuntimeError):
    """保留请求方法和地址、但不携带敏感请求内容的 transport 错误。"""

    def __init__(self, method: str, url: str, message: str):
        super().__init__(f"{method.upper()} 请求失败: {url}: {message}")
        self.method = method.upper()
        self.url = url


class Transport(Protocol):
    def request(self, method: str, url: str, **kwargs: Any) -> dict: ...

    def close(self) -> None: ...


class RequestsTransport:
    """生产 requests adapter；仅 GET 允许底层自动重试。"""

    def __init__(
        self,
        *,
        pool_connections: int = 50,
        pool_maxsize: int = 100,
        max_retries: int = 2,
        backoff_factor: float = 0.5,
        timeout: int = 30,
    ):
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset({"GET"}),
            raise_on_status=False,
        )
        self._adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy,
            pool_block=False,
        )
        self._timeout = timeout
        self._local = threading.local()
        self._sessions: set[requests.Session] = set()
        self._sessions_lock = threading.Lock()

    def _get_session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.mount("https://", self._adapter)
            session.mount("http://", self._adapter)
            self._local.session = session
            with self._sessions_lock:
                self._sessions.add(session)
        return session

    def request(self, method: str, url: str, **kwargs: Any) -> dict:
        kwargs.setdefault("timeout", self._timeout)
        try:
            response = self._get_session().request(method, url, **kwargs)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as error:
            raise HttpRequestError(method, url, str(error)) from error
        if not isinstance(data, dict):
            raise HttpRequestError(method, url, "响应不是 JSON 对象")
        return data

    def close(self) -> None:
        """关闭所有已创建的 worker session。"""
        with self._sessions_lock:
            sessions = list(self._sessions)
            self._sessions.clear()
        for session in sessions:
            session.close()
        self._local.session = None


class HttpClient:
    """隐藏签名、加密和 transport 细节的小 interface。"""

    def __init__(self, transport: Transport, *, timeout: int = 30):
        self._transport = transport
        self._timeout = timeout

    def get(
        self,
        url: str,
        *,
        headers: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        return self._request(
            "GET", url, headers=headers, params=params, timeout=self._timeout
        )

    def post(
        self,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
        encrypt_key: str | None = None,
        locale: str = "zh",
        timestamp: str | None = None,
    ) -> dict:
        request_headers = dict(headers or {})
        kwargs: dict[str, Any] = {
            "headers": request_headers,
            "timeout": self._timeout,
        }
        if encrypt_key is not None:
            if not encrypt_key:
                raise ValueError("加密请求必须提供非空 encrypt_key")
            request_timestamp = timestamp or str(int(time.time() * 1000))
            request_headers.update(
                {
                    "content-type": "application/json",
                    "locale": locale,
                    "timestamp": request_timestamp,
                    "sign": SignUtils.generate_sign(
                        data or {}, locale, request_timestamp, encrypt_key
                    ),
                }
            )
            kwargs["data"] = SignUtils.encrypt(data or {}, encrypt_key)
        else:
            kwargs["json"] = data
        return self._request("POST", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs: Any) -> dict:
        try:
            return self._transport.request(method, url, **kwargs)
        except HttpRequestError:
            raise
        except Exception as error:
            raise HttpRequestError(method, url, str(error)) from error

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


class HttpUtils:
    """现有调用者使用的兼容 adapter。"""

    TIMEOUT = 30
    _transport: Transport = RequestsTransport(timeout=TIMEOUT)
    _client = HttpClient(_transport, timeout=TIMEOUT)

    @classmethod
    def configure_transport(cls, transport: Transport) -> None:
        cls.close_session()
        cls._transport = transport
        cls._client = HttpClient(transport, timeout=cls.TIMEOUT)

    @classmethod
    def get(cls, url, headers=None, params=None):
        return cls._client.get(url, headers=headers, params=params)

    @classmethod
    def post(
        cls,
        url,
        data=None,
        headers=None,
        encrypt_key=None,
        locale="zh",
        timestamp=None,
    ):
        return cls._client.post(
            url,
            data=data,
            headers=headers,
            encrypt_key=encrypt_key,
            locale=locale,
            timestamp=timestamp,
        )

    @classmethod
    def close_session(cls):
        cls._client.close()
