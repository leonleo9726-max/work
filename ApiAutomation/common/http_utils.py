import sys
import os
import time
import logging
import threading
from contextlib import contextmanager
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.sign_utils import SignUtils

logger = logging.getLogger(__name__)


class ConnectionPool:
    """
    连接池管理器，基于 requests.Session 实现 HTTP 连接复用。
    
    特性：
    - 线程安全的 Session 管理
    - 可配置的连接池大小和重试策略
    - 自动重试（可配置）
    - 连接超时和读取超时控制
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self, pool_connections: int = 50, pool_maxsize: int = 100,
                 max_retries: int = 2, backoff_factor: float = 0.5,
                 timeout: int = 30):
        """
        初始化连接池。
        
        Args:
            pool_connections: 连接池缓存连接数（每个host）
            pool_maxsize: 连接池最大连接数（每个host）
            max_retries: 最大重试次数
            backoff_factor: 重试退避因子（秒）
            timeout: 请求超时时间（秒）
        """
        self._timeout = timeout
        self._local = threading.local()

        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )

        # 配置适配器
        self._adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=retry_strategy,
            pool_block=False,
        )

    def _create_session(self) -> requests.Session:
        """创建一个新的 Session，挂载适配器"""
        session = requests.Session()
        session.mount("https://", self._adapter)
        session.mount("http://", self._adapter)
        return session

    def get_session(self) -> requests.Session:
        """
        获取当前线程的 Session（线程本地存储）。
        每个线程持有自己的 Session，避免锁竞争。
        """
        if not hasattr(self._local, "session") or self._local.session is None:
            self._local.session = self._create_session()
        return self._local.session

    def close_session(self):
        """关闭当前线程的 Session，释放连接"""
        if hasattr(self._local, "session") and self._local.session is not None:
            try:
                self._local.session.close()
            except Exception:
                pass
            self._local.session = None

    @classmethod
    def get_instance(cls, pool_connections: int = 50, pool_maxsize: int = 100,
                     max_retries: int = 2, backoff_factor: float = 0.5,
                     timeout: int = 30) -> "ConnectionPool":
        """获取全局单例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(
                        pool_connections=pool_connections,
                        pool_maxsize=pool_maxsize,
                        max_retries=max_retries,
                        backoff_factor=backoff_factor,
                        timeout=timeout,
                    )
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """重置单例（主要用于测试）"""
        with cls._lock:
            if cls._instance is not None:
                cls._instance = None


class HttpUtils:
    """
    HTTP 工具类，集成连接池。
    
    所有请求方法均为线程安全，自动从连接池获取 Session。
    """

    # 默认连接池配置
    POOL_CONNECTIONS = 50   # 每个 host 缓存连接数
    POOL_MAXSIZE = 100      # 每个 host 最大连接数
    MAX_RETRIES = 2         # 最大重试次数
    BACKOFF_FACTOR = 0.5    # 重试退避因子
    TIMEOUT = 30            # 请求超时（秒）

    @classmethod
    def _get_pool(cls) -> ConnectionPool:
        """获取连接池单例"""
        return ConnectionPool.get_instance(
            pool_connections=cls.POOL_CONNECTIONS,
            pool_maxsize=cls.POOL_MAXSIZE,
            max_retries=cls.MAX_RETRIES,
            backoff_factor=cls.BACKOFF_FACTOR,
            timeout=cls.TIMEOUT,
        )

    @classmethod
    def get_session(cls) -> requests.Session:
        """获取当前线程的 Session"""
        return cls._get_pool().get_session()

    @classmethod
    def close_session(cls):
        """关闭当前线程的 Session"""
        cls._get_pool().close_session()

    @classmethod
    def get(cls, url, headers=None, params=None):
        """发送GET请求（使用连接池）"""
        try:
            session = cls.get_session()
            response = session.get(
                url=url,
                headers=headers,
                params=params,
                timeout=cls.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("GET请求失败: url=%s, error=%s", url, e)
            return None

    @classmethod
    def post(cls, url, data=None, headers=None, encrypt_key=None,
             locale="zh", timestamp=None):
        """发送POST请求（使用连接池）"""
        try:
            session = cls.get_session()

            # 如果需要加密
            if encrypt_key and data:
                # 生成签名
                if not timestamp:
                    timestamp = str(int(time.time() * 1000))

                sign = SignUtils.generate_sign(data, locale, timestamp, encrypt_key)

                # 加密数据
                encrypted_data = SignUtils.encrypt(data, encrypt_key)

                # 更新headers
                if headers is None:
                    headers = {}
                headers['content-type'] = 'application/json'
                headers['locale'] = locale
                headers['timestamp'] = timestamp
                headers['sign'] = sign

                # 发送加密数据
                response = session.post(
                    url=url,
                    data=encrypted_data,
                    headers=headers,
                    timeout=cls.TIMEOUT,
                )
            else:
                # 发送未加密数据
                response = session.post(
                    url=url,
                    json=data,
                    headers=headers,
                    timeout=cls.TIMEOUT,
                )

            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error("POST请求失败: url=%s, error=%s", url, e)
            return None