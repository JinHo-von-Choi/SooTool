"""Tests for PM Critical Path Method (CPM) tool."""
from __future__ import annotations

import concurrent.futures
from decimal import Decimal

import pytest

import sootool.modules.pm  # noqa: F401
from sootool.core.errors import DomainConstraintError, InvalidInputError
from sootool.core.registry import REGISTRY


def _cpm(tasks: list[dict]) -> dict:
    return REGISTRY.invoke("pm.critical_path", tasks=tasks)


def _task(tid: str, dur: str, preds: list[str] | None = None) -> dict:
    return {"id": tid, "duration": dur, "predecessors": preds or []}


class TestCriticalPathSimple:
    def test_critical_path_simple(self) -> None:
        """A(5d) -> B(3d) and A(5d) -> C(4d): CP=[A,C], total=9, slack B=1."""
        tasks = [
            _task("A", "5"),
            _task("B", "3", ["A"]),
            _task("C", "4", ["A"]),
        ]
        r = _cpm(tasks)

        assert r["total_duration"] == "9"
        cp = r["critical_path"]
        assert "A" in cp
        assert "C" in cp
        assert "B" not in cp

        # Verify slack
        details = {d["id"]: d for d in r["task_details"]}
        assert details["A"]["slack"] == "0"
        assert details["C"]["slack"] == "0"
        assert details["B"]["slack"] == "1"

    def test_critical_path_linear(self) -> None:
        """Linear chain A->B->C: all are critical."""
        tasks = [
            _task("A", "3"),
            _task("B", "4", ["A"]),
            _task("C", "5", ["B"]),
        ]
        r = _cpm(tasks)
        assert r["total_duration"] == "12"
        assert set(r["critical_path"]) == {"A", "B", "C"}

    def test_critical_path_parallel_paths(self) -> None:
        """Two parallel paths with equal length: both are critical."""
        tasks = [
            _task("A", "3"),
            _task("B", "3", ["A"]),
            _task("C", "3", ["A"]),
            _task("D", "3", ["B", "C"]),
        ]
        r = _cpm(tasks)
        # Both paths A->B->D and A->C->D are equal
        assert r["total_duration"] == "9"
        # All tasks should be critical (both paths tie)
        assert set(r["critical_path"]) == {"A", "B", "C", "D"}

    def test_critical_path_single_task(self) -> None:
        tasks = [_task("A", "7")]
        r = _cpm(tasks)
        assert r["total_duration"] == "7"
        assert r["critical_path"] == ["A"]

    def test_critical_path_es_ef_correct(self) -> None:
        """Verify ES/EF values in simple 3-task network."""
        tasks = [
            _task("A", "5"),
            _task("B", "3", ["A"]),
        ]
        r = _cpm(tasks)
        details = {d["id"]: d for d in r["task_details"]}
        assert details["A"]["es"] == "0"
        assert details["A"]["ef"] == "5"
        assert details["B"]["es"] == "5"
        assert details["B"]["ef"] == "8"

    def test_critical_path_ls_lf_correct(self) -> None:
        """Verify LS/LF values match the critical path analysis."""
        tasks = [
            _task("A", "5"),
            _task("B", "3", ["A"]),
            _task("C", "4", ["A"]),
        ]
        r = _cpm(tasks)
        details = {d["id"]: d for d in r["task_details"]}
        # B is non-critical: LS=6, LF=9
        assert details["B"]["ls"] == "6"
        assert details["B"]["lf"] == "9"
        # C is critical: LS=5, LF=9
        assert details["C"]["ls"] == "5"
        assert details["C"]["lf"] == "9"

    def test_critical_path_trace(self) -> None:
        r = _cpm([_task("A", "5")])
        assert "trace" in r
        assert r["trace"]["tool"] == "pm.critical_path"


class TestCriticalPathCycle:
    def test_critical_path_cycle(self) -> None:
        """Cycle detection: A->B->C->A must raise DomainConstraintError."""
        tasks = [
            _task("A", "3", ["C"]),
            _task("B", "2", ["A"]),
            _task("C", "4", ["B"]),
        ]
        with pytest.raises(DomainConstraintError):
            _cpm(tasks)

    def test_critical_path_self_loop(self) -> None:
        tasks = [_task("A", "3", ["A"])]
        with pytest.raises(DomainConstraintError):
            _cpm(tasks)


class TestCriticalPathValidation:
    def test_critical_path_empty_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            _cpm([])

    def test_critical_path_unknown_predecessor_raises(self) -> None:
        tasks = [_task("A", "5", ["Z"])]
        with pytest.raises(InvalidInputError):
            _cpm(tasks)

    def test_critical_path_duplicate_id_raises(self) -> None:
        tasks = [_task("A", "5"), _task("A", "3")]
        with pytest.raises(InvalidInputError):
            _cpm(tasks)

    def test_critical_path_negative_duration_raises(self) -> None:
        tasks = [_task("A", "-1")]
        with pytest.raises(DomainConstraintError):
            _cpm(tasks)


class TestCPMBatchRaceFree:
    def test_pm_batch_race_free(self) -> None:
        tasks = [
            _task("A", "5"),
            _task("B", "3", ["A"]),
            _task("C", "4", ["A"]),
        ]
        expected_total = _cpm(tasks)["total_duration"]

        def run() -> str:
            return _cpm(tasks)["total_duration"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(run) for _ in range(40)]
            results = [f.result() for f in futures]

        for r in results:
            assert r == expected_total, f"Race condition in critical_path"
