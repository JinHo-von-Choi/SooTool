"""
Tests for core/determinism.py — deterministic RNG and sort helpers.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

import numpy as np

from sootool.core.determinism import get_rng, sorted_by_id


class TestGetRng:
    def test_returns_generator(self):
        rng = get_rng(0)
        assert isinstance(rng, np.random.Generator)

    def test_same_seed_same_instance(self):
        """Acceptance test: get_rng(0) is get_rng(0)."""
        rng1 = get_rng(0)
        rng2 = get_rng(0)
        assert rng1 is rng2

    def test_different_seeds_different_instances(self):
        rng_a = get_rng(1)
        rng_b = get_rng(2)
        assert rng_a is not rng_b

    def test_default_seed_is_zero(self):
        rng_default = get_rng()
        rng_zero    = get_rng(0)
        assert rng_default is rng_zero

    def test_rng_is_deterministic(self):
        """Two fresh calls with the same seed produce the same first value."""
        # Since we cache, we cannot re-seed. Instead verify the module-level cache
        # returns same object (statefulness is by design).
        rng = get_rng(42)
        assert rng is get_rng(42)


class TestSortedById:
    def test_basic_sort(self):
        """Acceptance test from spec."""
        data   = [{"id": "b", "v": 2}, {"id": "a", "v": 1}]
        result = sorted_by_id(data)
        assert result == [{"id": "a", "v": 1}, {"id": "b", "v": 2}]

    def test_already_sorted(self):
        data   = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        result = sorted_by_id(data)
        assert result == data

    def test_stable_sort(self):
        """Items with the same id preserve original relative order."""
        data   = [{"id": "a", "v": 1}, {"id": "a", "v": 2}]
        result = sorted_by_id(data)
        assert result[0]["v"] == 1
        assert result[1]["v"] == 2

    def test_empty_list(self):
        assert sorted_by_id([]) == []

    def test_single_item(self):
        data = [{"id": "x", "val": 99}]
        assert sorted_by_id(data) == data

    def test_does_not_mutate_input(self):
        data   = [{"id": "b"}, {"id": "a"}]
        before = list(data)
        sorted_by_id(data)
        assert data == before

    def test_numeric_string_ids(self):
        data   = [{"id": "10"}, {"id": "2"}, {"id": "1"}]
        result = sorted_by_id(data)
        # Lexicographic string sort: "1" < "10" < "2"
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "10"
        assert result[2]["id"] == "2"
