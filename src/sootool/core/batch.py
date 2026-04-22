from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout, as_completed, Future
from dataclasses import dataclass, field
from typing import Any

from sootool.core.registry import ToolRegistry
from sootool.core.errors import SooToolError


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

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures: dict[Future, str] = {}
            for it in items:
                fut = pool.submit(self.registry.invoke, it["tool"], **it.get("args", {}))
                futures[fut] = it["id"]

            if self.deterministic:
                # Collect by future mapped to item id, then order by input order
                id_to_future: dict[str, Future] = {v: k for k, v in futures.items()}
                for item_id, fut in id_to_future.items():
                    t0 = time.monotonic()
                    try:
                        res = fut.result(timeout=self.item_timeout_s)
                        results[item_id] = {
                            "id": item_id,
                            "status": "ok",
                            "result": res,
                            "elapsed_ms": int((time.monotonic() - t0) * 1000),
                        }
                    except FuturesTimeout:
                        fut.cancel()
                        results[item_id] = {
                            "id": item_id,
                            "status": "timeout",
                            "error": {"type": "TimeoutError", "message": f"item_timeout_s={self.item_timeout_s}"},
                            "elapsed_ms": int((time.monotonic() - t0) * 1000),
                        }
                    except Exception as e:
                        results[item_id] = {
                            "id": item_id,
                            "status": "error",
                            "error": {"type": type(e).__name__, "message": str(e)},
                            "elapsed_ms": int((time.monotonic() - t0) * 1000),
                        }
            else:
                # Non-deterministic: collect by completion order
                for fut in as_completed(futures):
                    item_id = futures[fut]
                    t0 = time.monotonic()
                    try:
                        res = fut.result(timeout=0)
                        results[item_id] = {
                            "id": item_id,
                            "status": "ok",
                            "result": res,
                            "elapsed_ms": int((time.monotonic() - t0) * 1000),
                        }
                    except FuturesTimeout:
                        results[item_id] = {
                            "id": item_id,
                            "status": "timeout",
                            "error": {"type": "TimeoutError", "message": f"item_timeout_s={self.item_timeout_s}"},
                            "elapsed_ms": int((time.monotonic() - t0) * 1000),
                        }
                    except Exception as e:
                        results[item_id] = {
                            "id": item_id,
                            "status": "error",
                            "error": {"type": type(e).__name__, "message": str(e)},
                            "elapsed_ms": int((time.monotonic() - t0) * 1000),
                        }

        total_ms = int((time.monotonic() - started) * 1000)

        if self.deterministic:
            ordered = [results[it["id"]] for it in items]
        else:
            # Ordered by completion time (already in insertion order via dict)
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
