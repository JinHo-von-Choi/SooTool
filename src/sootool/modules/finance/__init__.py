"""Finance domain module.

Importing this package registers all finance tools in REGISTRY.

Tools:
  finance.pv             - Present Value (TVM)
  finance.fv             - Future Value (TVM)
  finance.npv            - Net Present Value
  finance.irr            - Internal Rate of Return
  finance.loan_schedule  - Loan amortization schedule
  finance.bond_ytm       - Bond Yield-to-Maturity
  finance.bond_duration  - Macaulay & Modified Duration
  finance.black_scholes  - Black-Scholes European option pricing + Greeks
"""
from __future__ import annotations

from sootool.modules.finance import bond, loan, metrics, option, tvm

__all__ = ["bond", "loan", "metrics", "option", "tvm"]
