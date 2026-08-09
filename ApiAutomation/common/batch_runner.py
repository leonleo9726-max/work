"""统一并发、重试和结果汇总的批处理 module。"""

import random
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

Item = TypeVar("Item")
Result = TypeVar("Result")


@dataclass(frozen=True)
class BatchPolicy:
    workers: int = 3
    attempts: int = 1
    delay: float = 0
    retry_delay: float = 1
    jitter: float = 0

    def __post_init__(self) -> None:
        if self.workers < 1 or self.attempts < 1:
            raise ValueError("workers 和 attempts 必须大于零")
        if self.delay < 0 or self.retry_delay < 0:
            raise ValueError("delay 和 retry_delay 不能为负数")
        if not 0 <= self.jitter <= 1:
            raise ValueError("jitter 必须位于 0 到 1 之间")


@dataclass(frozen=True)
class BatchItemResult(Generic[Item, Result]):
    item: Item
    result: Result | None
    success: bool
    attempts: int
    error: str | None = None


@dataclass(frozen=True)
class BatchSummary(Generic[Item, Result]):
    results: list[BatchItemResult[Item, Result]]

    @property
    def succeeded(self) -> int:
        return sum(result.success for result in self.results)

    @property
    def failed(self) -> int:
        return len(self.results) - self.succeeded


def _default_succeeded(result: Any) -> bool:
    if isinstance(result, dict) and "success" in result:
        return result["success"] is True
    return bool(result)


class BatchRunner:
    """以一个 operation interface 执行批次，隐藏并发和重试 implementation。"""

    def __init__(
        self,
        *,
        sleep: Callable[[float], None] = time.sleep,
        random_uniform: Callable[[float, float], float] = random.uniform,
        finalizer: Callable[[], None] | None = None,
    ):
        self._sleep = sleep
        self._random_uniform = random_uniform
        self._finalizer = finalizer

    def run(
        self,
        items: Iterable[Item],
        operation: Callable[[Item], Result],
        policy: BatchPolicy,
        *,
        succeeded: Callable[[Result], bool] = _default_succeeded,
    ) -> BatchSummary[Item, Result]:
        try:
            with ThreadPoolExecutor(max_workers=policy.workers) as executor:
                futures = {
                    executor.submit(
                        self._execute_item, item, operation, policy, succeeded
                    ): index
                    for index, item in enumerate(items)
                }
                ordered: list[tuple[int, BatchItemResult[Item, Result]]] = []
                for future in as_completed(futures):
                    ordered.append((futures[future], future.result()))
            ordered.sort(key=lambda entry: entry[0])
            return BatchSummary([entry[1] for entry in ordered])
        finally:
            if self._finalizer:
                self._finalizer()

    def _execute_item(
        self,
        item: Item,
        operation: Callable[[Item], Result],
        policy: BatchPolicy,
        succeeded: Callable[[Result], bool],
    ) -> BatchItemResult[Item, Result]:
        self._wait(policy.delay, policy.jitter)
        last_result: Result | None = None
        last_error: str | None = None
        for attempt in range(1, policy.attempts + 1):
            try:
                last_result = operation(item)
                if succeeded(last_result):
                    return BatchItemResult(item, last_result, True, attempt)
                last_error = "operation 返回失败结果"
            except Exception as error:
                last_error = str(error)
            if attempt < policy.attempts:
                self._wait(policy.retry_delay, policy.jitter)
        return BatchItemResult(
            item,
            last_result,
            False,
            policy.attempts,
            last_error,
        )

    def _wait(self, delay: float, jitter: float) -> None:
        if delay <= 0:
            return
        factor = 1 + self._random_uniform(-jitter, jitter)
        self._sleep(max(0, delay * factor))
