from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import dataclass
from typing import Any

from sootool.core.errors import SooToolError
from sootool.core.registry import ToolRegistry


class BatchLimitError(SooToolError):
    pass


@dataclass
class BatchExecutor:
    registry: ToolRegistry
    max_items: int = 500
    item_timeout_s: float = 10.0
    batch_timeout_s: float = 60.0
    max_workers: int = 16
    deterministic: bool = True

    def run(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        if len(items) > self.max_items:
            raise BatchLimitError(f"배치 항목 수 {len(items)} > 한도 {self.max_items}")
        ids = [it["id"] for it in items]
        if len(set(ids)) != len(ids):
            raise ValueError("배치 항목 id 중복")

        started = time.monotonic()
        workers = min(self.max_workers, max(1, len(items)))
        results: dict[str, dict[str, Any]] = {}
        item_started_at: dict[str, float] = {}

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures: dict[Future[Any], str] = {}
            for it in items:
                submit_t0 = time.monotonic()
                fut = pool.submit(self.registry.invoke, it["tool"], **it.get("args", {}))
                futures[fut] = it["id"]
                item_started_at[it["id"]] = submit_t0

            # ADR-020: deterministic 경로도 as_completed 로 결과를 수집하여
            # wall-clock 을 max(item_time) 으로 단축한다. 순차 future.result() 루프는
            # 느린 선행 항목이 뒤따르는 빠른 항목의 결과 수집을 블로킹했다.
            # ADR-011 invariant(응답 results 가 입력 id 순서)는 아래 ordered 구성 단계에서 유지.
            #
            # item_timeout_s 와 batch_timeout_s 을 모두 존중하며, 둘 중 먼저 도달한
            # 시점에 pending future 를 타임아웃 처리하고 남은 것을 cancel 한다.
            pending = set(futures.keys())
            batch_deadline = started + self.batch_timeout_s

            def _finalize_timeout(fut: Future[Any], reason_ms: float, reason_key: str) -> None:
                item_id = futures[fut]
                t0 = item_started_at[item_id]
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
                # 1) 개별 item_timeout_s 초과 future 는 즉시 타임아웃 처리
                expired = [
                    fut for fut in pending
                    if (now - item_started_at[futures[fut]]) >= self.item_timeout_s
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

                # 3) 다음 item deadline 또는 batch deadline 중 가까운 시점까지 대기
                next_item_deadline = min(
                    item_started_at[futures[fut]] + self.item_timeout_s
                    for fut in pending
                )
                wait_until = min(next_item_deadline, batch_deadline)
                wait_for = max(0.0, wait_until - now)

                try:
                    done_iter = as_completed(pending, timeout=wait_for)
                    done_fut = next(iter(done_iter))
                except (StopIteration, FuturesTimeout):
                    # 대기 시한 도달. 루프 재진입하여 expired 검사 재수행.
                    continue

                pending.discard(done_fut)
                item_id = futures[done_fut]
                t0 = item_started_at[item_id]
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

        response: dict[str, Any] = {
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
