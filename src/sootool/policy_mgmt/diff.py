"""Semantic diff for policy files — bracket-level rate change comparison.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any


def _extract_brackets(data: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Try to extract a bracket list from a policy data dict."""
    if "brackets" in data:
        return list(data["brackets"])
    if "income_tax_brackets" in data:
        return list(data["income_tax_brackets"])
    if "house" in data and isinstance(data["house"], dict) and "brackets" in data["house"]:
        return list(data["house"]["brackets"])
    return None


def _bracket_key(b: dict[str, Any]) -> str:
    upper = b.get("upper")
    return f"upper={upper}"


def diff_policy_data(
    old_data: dict[str, Any],
    new_data: dict[str, Any],
    old_year: int,
    new_year: int,
) -> dict[str, Any]:
    """Produce a semantic diff between two policy data dicts.

    Compares bracket-level changes, top-level scalar fields, and rate ratios.
    """
    changes: list[dict[str, Any]] = []

    old_brackets = _extract_brackets(old_data)
    new_brackets = _extract_brackets(new_data)

    if old_brackets is not None and new_brackets is not None:
        changes.extend(_diff_brackets(old_brackets, new_brackets))

    # Also diff top-level scalar numeric fields
    for field in ("dsr_cap",):
        if field in old_data and field in new_data:
            old_val = Decimal(str(old_data[field]))
            new_val = Decimal(str(new_data[field]))
            if old_val != new_val:
                changes.append({
                    "field":    field,
                    "old":      str(old_val),
                    "new":      str(new_val),
                    "delta":    str(new_val - old_val),
                    "type":     "field_change",
                })

    # Diff LTV/DTI blocks
    for block in ("ltv", "dti"):
        if block in old_data and block in new_data:
            old_block = old_data[block]
            new_block = new_data[block]
            if isinstance(old_block, dict) and isinstance(new_block, dict):
                for k in set(list(old_block.keys()) + list(new_block.keys())):
                    ov = old_block.get(k)
                    nv = new_block.get(k)
                    if ov is not None and nv is not None and str(ov) != str(nv):
                        changes.append({
                            "field":   f"{block}.{k}",
                            "old":     str(ov),
                            "new":     str(nv),
                            "delta":   str(Decimal(str(nv)) - Decimal(str(ov))),
                            "type":    "field_change",
                        })

    return {
        "vs_year":      old_year,
        "current_year": new_year,
        "changes":      changes,
        "summary":      f"{len(changes)} change(s) vs {old_year}",
    }


def _diff_brackets(
    old_brackets: list[dict[str, Any]],
    new_brackets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compare two bracket lists, matching by upper bound."""
    changes: list[dict[str, Any]] = []

    old_by_key = {_bracket_key(b): b for b in old_brackets}
    new_by_key = {_bracket_key(b): b for b in new_brackets}

    all_keys = sorted(
        set(list(old_by_key.keys()) + list(new_by_key.keys())),
        key=lambda k: float("inf") if "None" in k else float(k.split("=")[1]),
    )

    for key in all_keys:
        old_b = old_by_key.get(key)
        new_b = new_by_key.get(key)

        if old_b is None:
            changes.append({
                "bracket": key,
                "type":    "added",
                "new_rate": str(new_b["rate"]),  # type: ignore[index]
            })
        elif new_b is None:
            changes.append({
                "bracket": key,
                "type":    "removed",
                "old_rate": str(old_b["rate"]),
            })
        else:
            old_rate = Decimal(str(old_b["rate"]))
            new_rate = Decimal(str(new_b["rate"]))
            if old_rate != new_rate:
                delta = new_rate - old_rate
                pct_change = (delta / old_rate * 100) if old_rate != Decimal("0") else Decimal("0")
                changes.append({
                    "bracket":     key,
                    "type":        "rate_changed",
                    "old_rate":    str(old_rate),
                    "new_rate":    str(new_rate),
                    "delta":       str(delta),
                    "pct_change":  str(pct_change.quantize(Decimal("0.01"))),
                })

    return changes


def diff_policies(
    old_doc: dict[str, Any],
    new_doc: dict[str, Any],
    old_year: int,
    new_year: int,
) -> dict[str, Any]:
    """High-level diff between two loaded policy documents (output of loader.load)."""
    old_data = old_doc.get("data", old_doc)
    new_data = new_doc.get("data", new_doc)
    return diff_policy_data(old_data, new_data, old_year, new_year)
