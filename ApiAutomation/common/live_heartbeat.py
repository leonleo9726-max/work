"""直播间用户心跳。"""

import threading
from typing import Callable

from common.api_client import EastPointClient
from common.api_paths import LIVE_HEARTBEAT_PATH
from common.http_utils import HttpUtils
from common.response_utils import extract_error_message, is_api_success
from config import settings


def post_live_heartbeat(
    credential: dict,
    live_id: int,
    client_factory: Callable[..., EastPointClient] = EastPointClient,
):
    """以一个已登录用户身份发送一次直播心跳。"""
    stay_token = credential.get("stayToken")
    stay_user_id = credential.get("stayUserId")
    if not stay_token or not stay_user_id:
        raise ValueError("心跳凭证缺少 stayToken 或 stayUserId")
    if live_id < 0:
        raise ValueError("live_id 不能小于 0")

    return client_factory(
        settings.TEST_ENCRYPT_KEY, base_url=settings.LIVE_BASE_URL
    ).post(
        LIVE_HEARTBEAT_PATH,
        {"liveId": live_id},
        token=stay_token,
        user_id=str(stay_user_id),
        locale="zh",
        extra_headers=settings.build_live_service_headers(),
        plain_json=True,
    )


class LiveHeartbeatLoop:
    """在批量操作期间为一组发送人持续保持直播间心跳。"""

    def __init__(
        self,
        credentials: list[dict],
        live_id: int,
        interval_seconds: float,
        post_heartbeat: Callable[[dict, int], object] = post_live_heartbeat,
    ):
        if not credentials:
            raise ValueError("心跳发送人不能为空")
        if live_id < 0:
            raise ValueError("live_id 不能小于 0")
        if interval_seconds <= 0:
            raise ValueError("心跳间隔必须大于 0")

        self._credentials = credentials
        self._live_id = live_id
        self._interval_seconds = interval_seconds
        self._post_heartbeat = post_heartbeat
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._failures: list[dict] = []
        self._thread: threading.Thread | None = None

    @property
    def failures(self) -> list[dict]:
        with self._lock:
            return self._failures.copy()

    def start(self) -> None:
        """完成首轮心跳后启动后台保活；首轮失败时拒绝继续。"""
        try:
            initial_failures = self._send_round()
        finally:
            HttpUtils.close_session()
        if initial_failures:
            self._record_failures(initial_failures)
            first_failure = initial_failures[0]
            raise RuntimeError(
                f"心跳失败: sender_user_id={first_failure['sender_user_id']}, "
                f"error={first_failure['error']}"
            )

        self._thread = threading.Thread(target=self._run, name="live-heartbeat", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止后台心跳并释放该线程的 HTTP 会话。"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self._interval_seconds + 1)

    def raise_if_failed(self) -> None:
        """在发送礼物前阻止已失去心跳的发送人继续操作。"""
        failures = self.failures
        if failures:
            first_failure = failures[0]
            raise RuntimeError(
                f"心跳失败: sender_user_id={first_failure['sender_user_id']}, "
                f"error={first_failure['error']}"
            )

    def _run(self) -> None:
        try:
            while not self._stop_event.wait(self._interval_seconds):
                self._record_failures(self._send_round())
        finally:
            HttpUtils.close_session()

    def _send_round(self) -> list[dict]:
        failures = []
        for credential in self._credentials:
            user_id = str(credential.get("stayUserId", ""))
            try:
                response = self._post_heartbeat(credential, self._live_id)
                if not is_api_success(response):
                    error = extract_error_message(response) if isinstance(response, dict) else "心跳响应为空或格式无效"
                    failures.append({"sender_user_id": user_id, "error": error})
            except Exception as exc:
                failures.append({"sender_user_id": user_id, "error": str(exc)})
        return failures

    def _record_failures(self, failures: list[dict]) -> None:
        if not failures:
            return
        with self._lock:
            self._failures.extend(failures)
