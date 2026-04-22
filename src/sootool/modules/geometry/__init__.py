"""Geometry domain module.

Importing this package registers all geometry tools in REGISTRY.
"""
from __future__ import annotations

from sootool.modules.geometry import area, distance, matrix_ops, vector_ops, volume

__all__ = ["area", "distance", "matrix_ops", "vector_ops", "volume"]
