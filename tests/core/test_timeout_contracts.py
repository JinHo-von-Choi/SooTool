"""P0-2: 시간 축 계약 테스트 스위트.

BatchExecutor / PipelineExecutor / symbolic 모듈의 타임아웃 계약을
wall-clock 측정으로 검증한다.

로컬 ToolRegistry를 생성·주입하므로 전역 REGISTRY를 오염시키지 않는다.

작성자: 최진호
작성일: 2026-04-24
"""
from __future__ import annotations

import concurrent.futures
import os
import signal
import time

import pytest

from sootool.core.batch import BatchExecutor
from sootool.core.pipeline import PipelineExecutor
from sootool.core.registry import REGISTRY, ToolRegistry

# symbolic 모듈이 전역 REGISTRY 에 등록되려면 명시적으로 import 해야 한다.
# (서버 기동 시 선택적으로 import 되는 모듈이므로 테스트에서 직접 로드한다.)
try:
    import sootool.modules.symbolic  # noqa: F401
except ImportError:
    pass  # sympy 미설치 환경 — symbolic 테스트는 pytest.importorskip 으로 skip 됨

TIMEOUT_TOLERANCE = float(os.environ.get("SOOTOOL_TIMEOUT_TOLERANCE", "2.0"))

# ---------------------------------------------------------------------------
# 로컬 레지스트리 + 더미 도구
# ---------------------------------------------------------------------------

_local_reg: ToolRegistry = ToolRegistry()


@_local_reg.tool(namespace="_test", name="slow_sleep")
def _slow_sleep(seconds: float = 10.0) -> dict[str, object]:
    time.sleep(seconds)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Test 1: batch_timeout 기반 wall-clock 상한
# ---------------------------------------------------------------------------


def test_batch_batch_timeout_wall_clock() -> None:
    """batch_timeout_s=1.0 이 10건 x 10초 sleep 을 1초 근방에서 종료시킨다."""
    ex = BatchExecutor(
        registry=_local_reg,
        batch_timeout_s=1.0,
        item_timeout_s=10.0,
        max_items=500,
    )
    items = [
        {"id": f"s{i}", "tool": "_test.slow_sleep", "args": {"seconds": 10}}
        for i in range(10)
    ]

    t0 = time.monotonic()
    resp = ex.run(items)
    elapsed = time.monotonic() - t0

    upper_bound = 1.0 * TIMEOUT_TOLERANCE + 2.0
    assert elapsed < upper_bound, (
        f"wall-clock {elapsed:.2f}s >= upper bound {upper_bound:.2f}s"
    )
    assert resp["count_timeout"] >= 1, "타임아웃된 항목이 없음"
    for r in resp["results"]:
        assert r["status"] in ("timeout", "ok"), f"unexpected status: {r['status']}"


# ---------------------------------------------------------------------------
# Test 2: item_timeout_s 기반 개별 항목 타임아웃
# ---------------------------------------------------------------------------


def test_batch_item_timeout_wall_clock() -> None:
    """item_timeout_s=1.0 이 단건 10초 sleep 을 타임아웃 처리한다."""
    ex = BatchExecutor(
        registry=_local_reg,
        item_timeout_s=1.0,
        batch_timeout_s=60.0,
    )
    items = [{"id": "x0", "tool": "_test.slow_sleep", "args": {"seconds": 10}}]

    t0 = time.monotonic()
    resp = ex.run(items)
    time.monotonic() - t0

    first = resp["results"][0]
    assert first["status"] == "timeout", f"expected timeout, got {first['status']}"
    elapsed_ms = first["elapsed_ms"]
    upper_ms = 3000 * TIMEOUT_TOLERANCE
    assert 1000 <= elapsed_ms <= upper_ms, (
        f"elapsed_ms={elapsed_ms} not in [1000, {upper_ms:.0f}]"
    )


# ---------------------------------------------------------------------------
# Test 3: pipeline step_timeout_s 강제
# ---------------------------------------------------------------------------


def test_pipeline_step_timeout_enforced() -> None:
    """step_timeout_s=1.0 이 10초 sleep step 을 timeout 처리하고 빠르게 반환한다."""
    ex = PipelineExecutor(
        registry=_local_reg,
        step_timeout_s=1.0,
        pipeline_timeout_s=60.0,
    )
    steps = [{"id": "s1", "tool": "_test.slow_sleep", "args": {"seconds": 10}}]

    t0 = time.monotonic()
    resp = ex.run(steps)
    elapsed = time.monotonic() - t0

    assert resp["steps"]["s1"]["status"] == "timeout", (
        f"expected timeout, got {resp['steps']['s1']['status']}"
    )
    upper_bound = 1.0 * TIMEOUT_TOLERANCE + 2.0
    assert elapsed < upper_bound, (
        f"wall-clock {elapsed:.2f}s >= upper bound {upper_bound:.2f}s"
    )


# ---------------------------------------------------------------------------
# Test 4: pipeline_timeout 전파 — 후속 step 이 skipped 처리됨
# ---------------------------------------------------------------------------


def test_pipeline_deadline_propagates() -> None:
    """pipeline_timeout_s=1.0 도달 후 나머지 step 이 PipelineTimeout/skipped 가 된다."""
    ex = PipelineExecutor(
        registry=_local_reg,
        step_timeout_s=2.0,
        pipeline_timeout_s=1.0,
    )
    steps = [
        {"id": "s1", "tool": "_test.slow_sleep", "args": {"seconds": 10}},
        {"id": "s2", "tool": "_test.slow_sleep", "args": {"seconds": 0.1}},
        {"id": "s3", "tool": "_test.slow_sleep", "args": {"seconds": 0.1}},
    ]

    resp = ex.run(steps)
    step_results = resp["steps"]

    # step1: timeout 또는 pipeline deadline hit 으로 timeout/skipped
    assert step_results["s1"]["status"] in ("timeout", "skipped"), (
        f"s1 status={step_results['s1']['status']}"
    )

    # step2/step3: pipeline deadline 이후 처리.
    # pipeline 코드 흐름: deadline 도달한 첫 step = "timeout" (pipeline_deadline_hit 활성화),
    # 이후 step = "skipped". s2/s3 중 어느 쪽이 "first deadline-hit" step이 될 수 있음.
    # 두 step 모두 error.type == "PipelineTimeout" 이어야 함.
    for sid in ("s2", "s3"):
        sr = step_results[sid]
        assert sr["status"] in ("timeout", "skipped"), (
            f"{sid} status={sr['status']}"
        )
        assert sr["error"]["type"] == "PipelineTimeout", (
            f"{sid} error.type={sr['error']['type']}"
        )


# ---------------------------------------------------------------------------
# Test 5: symbolic worker thread 타임아웃 (sympy 선택적 의존)
# ---------------------------------------------------------------------------


def test_symbolic_timeout_in_worker_thread() -> None:
    """sympy 워커 스레드 경로: 장시간 연산이 타임아웃 경계(_EVAL_TIMEOUT_S=5s) 내에 종료된다.

    동작: run_symbolic 내부 ThreadPoolExecutor 가 fut.result(timeout=5) 로 감싸므로,
    5s 내에 DomainConstraintError(타임아웃) 또는 NotImplementedError(sympy 포기) 중
    하나가 발생한다. 어느 쪽이든 연산이 무기한 블로킹되지 않음을 검증한다.
    """
    pytest.importorskip("sympy")

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        t0 = time.monotonic()
        fut = pool.submit(
            REGISTRY.invoke,
            "symbolic.solve",
            equation="x**x**x**x**x**x**x - 2",
            var="x",
        )
        try:
            fut.result(timeout=30)
            # 풀이가 빠르게 성공할 경우도 허용
        except Exception:  # noqa: S110
            pass
        elapsed = time.monotonic() - t0

    # run_symbolic 타임아웃 경계(5s) + 여유(TIMEOUT_TOLERANCE 적용)
    upper_bound = 6.5 * TIMEOUT_TOLERANCE
    assert elapsed <= upper_bound, (
        f"symbolic worker elapsed {elapsed:.2f}s > {upper_bound:.2f}s"
    )


# ---------------------------------------------------------------------------
# Test 6: symbolic SIGALRM 경로 (메인 스레드, Linux/macOS only)
# ---------------------------------------------------------------------------


def test_symbolic_main_thread_sigalrm_path() -> None:
    """메인 스레드 + SIGALRM 경로: 장시간 연산이 _EVAL_TIMEOUT_S(5s) 내에 종료된다.

    SIGALRM 경로에서는 DomainConstraintError 가 발생하거나, sympy 가 타임아웃 전에
    NotImplementedError 를 raise 할 수 있다. 어느 쪽이든 5s 내에 반환되어야 한다.
    """
    pytest.importorskip("sympy")

    if not hasattr(signal, "SIGALRM"):
        pytest.skip("SIGALRM unavailable on this platform")

    t0 = time.monotonic()
    try:
        REGISTRY.invoke(
            "symbolic.solve",
            equation="x**x**x**x**x**x**x - 2",
            var="x",
        )
    except Exception:  # noqa: S110
        pass
    elapsed = time.monotonic() - t0

    assert elapsed < 5.0 * TIMEOUT_TOLERANCE, (
        f"SIGALRM path took {elapsed:.2f}s (> {5.0 * TIMEOUT_TOLERANCE:.2f}s)"
    )


# ---------------------------------------------------------------------------
# Test 7: batch + symbolic protection — worker 내 DomainConstraintError 처리
# ---------------------------------------------------------------------------


def test_batch_worker_symbolic_protection() -> None:
    """BatchExecutor 가 symbolic 장시간 연산 10건을 5초 이내에 처리한다."""
    pytest.importorskip("sympy")

    ex = BatchExecutor(
        registry=REGISTRY,
        batch_timeout_s=2.0,
        item_timeout_s=10.0,
    )
    items = [
        {
            "id": f"sym{i}",
            "tool": "symbolic.solve",
            "args": {
                "expression": "x**x**x**x**x**x**x - 2",
                "var": "x",
            },
        }
        for i in range(10)
    ]

    t0 = time.monotonic()
    resp = ex.run(items)
    elapsed = time.monotonic() - t0

    upper_bound = 5.0 * TIMEOUT_TOLERANCE
    assert elapsed < upper_bound, (
        f"batch symbolic wall-clock {elapsed:.2f}s >= {upper_bound:.2f}s"
    )
    # error(DomainConstraintError) 또는 timeout 으로 처리돼야 함
    assert resp["count_timeout"] + resp["count_error"] >= 1, (
        "symbolic 연산이 타임아웃/에러 없이 모두 완료됨 — protection 미작동"
    )
