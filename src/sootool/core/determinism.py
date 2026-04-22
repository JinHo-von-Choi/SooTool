"""
core/determinism.py — Deterministic helpers for reproducible computations.

get_rng(seed) returns a cached np.random.Generator so that code paths
that need randomness can be made reproducible across runs by fixing the seed.

sorted_by_id provides a stable, deterministic sort of result dicts by their
"id" key, ensuring that batch output order is consistent regardless of
thread scheduling.

작성자: 최진호
작성일: 2026-04-22
"""
from __future__ import annotations

import threading
from typing import Any

import numpy as np

# Module-level cache: seed -> Generator instance
_cache: dict[int, np.random.Generator] = {}
_cache_lock = threading.Lock()


def get_rng(seed: int = 0) -> np.random.Generator:
    """
    Return a cached np.random.Generator for the given seed.

    The same Generator instance is returned for the same seed on every call.
    This means callers share state across calls — use this when you need
    reproducible but stateful random sequences.

    Parameters
    ----------
    seed : int — random seed (default 0).

    Returns
    -------
    np.random.Generator backed by PCG64.
    """
    with _cache_lock:
        if seed not in _cache:
            _cache[seed] = np.random.default_rng(seed)
        return _cache[seed]


def sorted_by_id(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Return a new list of dicts stably sorted by their "id" key (ascending).

    The original list is not modified. Items with equal "id" values preserve
    their original relative order (stable sort).

    Parameters
    ----------
    results : list of dicts, each expected to have an "id" key.

    Returns
    -------
    New list sorted by the "id" key in ascending order.
    """
    return sorted(results, key=lambda item: item["id"])
