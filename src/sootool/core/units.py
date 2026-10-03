from __future__ import annotations

import threading
from decimal import Decimal
from typing import Any, TypedDict

_UREG_LOCK = threading.RLock()


class _LazyRegistry:
    """첫 속성 접근 때 pint 레지스트리를 만든다.

    pint 를 가져오고 단위 정의를 읽는 데 0.5초가량 걸리므로, 단위 변환을 쓰지 않는 호출(대부분의 계산 도구와
    SDK)이 그 비용을 내지 않게 한다. 한 번 만든 레지스트리는 모든 호출이 공유한다.
    """

    def __init__(self) -> None:
        self._registry: Any = None

    def _get(self) -> Any:
        if self._registry is None:
            with _UREG_LOCK:
                if self._registry is None:
                    import pint

                    self._registry = pint.UnitRegistry(non_int_type=Decimal)
        return self._registry

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)


_UREG: Any = _LazyRegistry()


def __getattr__(name: str) -> Any:
    if name == "Quantity":
        return _UREG.Quantity
    raise AttributeError(name)


class SerializedQuantity(TypedDict):
    magnitude: str
    unit:      str


def Q(magnitude: str | Decimal | int, unit: str) -> Any:
    """Create a Quantity with a Decimal magnitude."""
    value = Decimal(magnitude) if not isinstance(magnitude, Decimal) else magnitude
    return _UREG.Quantity(value, unit)


def convert(q: Any, target_unit: str) -> Any:
    """Convert a Quantity to a different unit (read-only, lock-free)."""
    return q.to(target_unit)


def serialize(q: Any) -> SerializedQuantity:
    """Serialize a Quantity to a plain dict with string magnitude."""
    return {"magnitude": str(q.magnitude), "unit": str(q.units)}
