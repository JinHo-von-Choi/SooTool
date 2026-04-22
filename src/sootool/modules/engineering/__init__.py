"""Engineering domain module.

Importing this package registers all engineering tools in REGISTRY:
  - engineering.electrical_ohm     (Ohm's law)
  - engineering.electrical_power   (power equations P=VI=I²R=V²/R)
  - engineering.resistor_series    (series resistance)
  - engineering.resistor_parallel  (parallel resistance)
  - engineering.fluid_reynolds     (Reynolds number + flow regime)
  - engineering.si_prefix_convert  (SI prefix scale conversion)
"""
from __future__ import annotations

from sootool.modules.engineering import electrical, fluid, si_prefix

__all__ = ["electrical", "fluid", "si_prefix"]
