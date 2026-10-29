from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass
from typing import Any, NotRequired, TypedDict

from sootool.core.errors import SooToolError
from sootool.core.limits import orchestration_scope
from sootool.core.registry import ToolRegistry
from sootool.core.request_context import submit_with_context
from sootool.core.result_types import ToolResult


class BatchLimitError(SooToolError):
    pass


class ExecutionError(TypedDict):
    """항목 또는 단계 하나의 실패 원인. ``type`` 은 예외 클래스 이름이다."""

    type:    str
    message: str


class BatchItemResult(TypedDict):
    """배치 항목 하나의 실행 결과. ok 이면 ``result``, error 와 timeout 이면 ``error`` 가 있다."""

    id:         str
    status:     str
    result:     NotRequired[dict[str, Any]]
    error:      NotRequired[ExecutionError]
    elapsed_ms: int


class BatchResult(ToolResult):
    status:            str
    results:           list[BatchItemResult]
    count_ok:          int
    count_error:       int
    count_timeout:     int
    total_time_ms:     int
    parallelism:       int
    non_deterministic: NotRequired[bool]


@dataclass
class BatchExecutor:
    registry: ToolRegistry
    max_items: int = 500
    item_timeout_s: float = 10.0
    batch_timeout_s: float = 60.0
    max_workers: int = 16
    deterministic: bool = True

    def run(self, items: list[dict[str, Any]]) -> BatchResult:
        # 중첩 배치로 인한 스레드 풀 증폭을 막는다(limits.orchestration_scope).
        with orchestration_scope():
            return self._run(items)

    def _run(self, items: list[dict[str, Any]]) -> BatchResult:
        if len(items) > self.max_items:
            raise BatchLimitError(f"배치 항목 수 {len(items)} > 한도 {self.max_items}")
        ids = [it["id"] for it in items]
        if len(set(ids)) != len(ids):
            raise ValueError("배치 항목 id 중복")

        started = time.monotonic()
        workers = min(self.max_workers, max(1, len(items)))
        results: dict[str, BatchItemResult] = {}
        submitted_at: dict[str, float] = {}
        exec_started_at: dict[str, float] = {}

        # wait=False + cancel_futures=True: 타임아웃 처리 완료 후 실행 중 worker 를 분리하여
        # pool.__exit__ 의 blocking shutdown 으로 인한 wall-clock 초과를 방지한다.
        pool = ThreadPoolExecutor(max_workers=workers)
        try:
            futures: dict[Future[Any], str] = {}

            def _run_item(item_id: str, tool: str, args: dict[str, Any]) -> Any:
                """항목의 실행 시작 시각을 기록하고 도구를 호출한다.

                item_timeout_s 는 이 시각부터 센다. 제출 시각부터 세면 워커 대기
                시간까지 시한에 포함돼, 워커 수보다 항목이 많을 때 실제로는 빠르게
                끝나는 항목이 대량으로 타임아웃 처리된다(ADR-020 개정).
                """
                exec_started_at[item_id] = time.monotonic()
                return self.registry.invoke_read_only(tool, **args)

            for it in items:
                submit_t0 = time.monotonic()
                fut = submit_with_context(pool, _run_item, it["id"], it["tool"], it.get("args", {}))
                futures[fut] = it["id"]
                submitted_at[it["id"]] = submit_t0

            # ADR-020: deterministic 경로도 as_completed 로 결과를 수집하여
            # wall-clock 을 max(item_time) 으로 단축한다. 순차 future.result() 루프는
            # 느린 선행 항목이 뒤따르는 빠른 항목의 결과 수집을 블로킹했다.
            # ADR-011 invariant(응답 results 가 입력 id 순서)는 아래 ordered 구성 단계에서 유지.
            #
            # item_timeout_s 와 batch_timeout_s 을 모두 존중하며, 둘 중 먼저 도달한
            # 시점에 pending future 를 타임아웃 처리하고 남은 것을 cancel 한다.
            pending = set(futures.keys())
            batch_deadline = started + self.batch_timeout_s

            def _elapsed_base(item_id: str) -> float:
                """경과 시간 기준점. 실행을 시작한 항목은 실행 시작 시각, 대기 중 항목은 제출 시각."""
                return exec_started_at.get(item_id, submitted_at[item_id])

            def _finalize_timeout(fut: Future[Any], reason_ms: float, reason_key: str) -> None:
                item_id = futures[fut]
                t0 = _elapsed_base(item_id)
                fut.cancel()
                results[item_id] = {
                    "id":         item_id,
                    "status":     "timeout",
                    "error":      {
                        "type":    "TimeoutError",
                        "message": f"{reason_key}={reason_ms}",
                    },
                    "elapsed_ms": int((time.monotonic() - t0) * 1000),
                }

            while pending:
                now = time.monotonic()
                # 1) 실행이 시작된 항목 중 item_timeout_s 를 넘은 future 는 즉시 타임아웃 처리.
                #    아직 시작되지 않은(워커 대기 중) 항목은 실행 시간이 0 이므로 이 검사에 걸리지
                #    않는다. 대기 시간 자체는 batch_timeout_s 가 대신 구속한다.
                expired = [
                    fut for fut in pending
                    if (item_id := futures[fut]) in exec_started_at
                    and (now - exec_started_at[item_id]) >= self.item_timeout_s
                ]
                for fut in expired:
                    _finalize_timeout(fut, self.item_timeout_s, "item_timeout_s")
                    pending.discard(fut)
                if not pending:
                    break

                # 2) batch_timeout 초과 검사
                if now >= batch_deadline:
                    for fut in list(pending):
                        _finalize_timeout(fut, self.batch_timeout_s, "batch_timeout_s")
                    pending.clear()
                    break

                # 3) 다음 item deadline 또는 batch deadline 중 가까운 시점까지 대기.
                #    실행 중인 항목만 item deadline 을 갖는다. 실행 중인 항목이 하나도
                #    없으면(모두 대기 중) batch deadline 까지 기다린다.
                item_deadlines = [
                    exec_started_at[futures[fut]] + self.item_timeout_s
                    for fut in pending
                    if futures[fut] in exec_started_at
                ]
                next_item_deadline = min(item_deadlines) if item_deadlines else None
                wait_until = batch_deadline if next_item_deadline is None else min(next_item_deadline, batch_deadline)
                wait_for = max(0.0, wait_until - now)

                try:
                    done_iter = as_completed(pending, timeout=wait_for)
                    done_fut = next(iter(done_iter))
                except (StopIteration, FuturesTimeout):
                    # 대기 시한 도달. 루프 재진입하여 expired 검사 재수행.
                    continue

                pending.discard(done_fut)
                item_id = futures[done_fut]
                t0 = _elapsed_base(item_id)
                try:
                    res = done_fut.result(timeout=0)
                    results[item_id] = {
                        "id":         item_id,
                        "status":     "ok",
                        "result":     res,
                        "elapsed_ms": int((time.monotonic() - t0) * 1000),
                    }
                except FuturesTimeout:
                    results[item_id] = {
                        "id":         item_id,
                        "status":     "timeout",
                        "error":      {
                            "type":    "TimeoutError",
                            "message": f"item_timeout_s={self.item_timeout_s}",
                        },
                        "elapsed_ms": int((time.monotonic() - t0) * 1000),
                    }
                except Exception as e:
                    results[item_id] = {
                        "id":         item_id,
                        "status":     "error",
                        "error":      {"type": type(e).__name__, "message": str(e)},
                        "elapsed_ms": int((time.monotonic() - t0) * 1000),
                    }
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

        total_ms = int((time.monotonic() - started) * 1000)

        if self.deterministic:
            # ADR-011 invariant: results 는 입력 id 순서
            ordered = [results[it["id"]] for it in items]
        else:
            # non-deterministic: 완료 순서 그대로 노출 (results 에 완료 순으로 누적됨)
            ordered = list(results.values())

        count_ok      = sum(1 for r in ordered if r["status"] == "ok")
        count_error   = sum(1 for r in ordered if r["status"] == "error")
        count_timeout = sum(1 for r in ordered if r["status"] == "timeout")

        if count_ok == len(ordered):
            status = "all_ok"
        elif count_ok == 0:
            status = "all_failed"
        else:
            status = "partial"

        response: BatchResult = {
            "status":         status,
            "results":        ordered,
            "count_ok":       count_ok,
            "count_error":    count_error,
            "count_timeout":  count_timeout,
            "total_time_ms":  total_ms,
            "parallelism":    workers,
        }
        if not self.deterministic:
            response["non_deterministic"] = True
        return response
