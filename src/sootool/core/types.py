from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, field_validator, ConfigDict


class Money(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    amount:   Decimal
    currency: str

    @field_validator("amount", mode="before")
    @classmethod
    def _amount_str_or_decimal_only(cls, v: object) -> Decimal:
        if isinstance(v, float):
            raise TypeError("Money.amount에 float 금지. 문자열 사용.")
        if isinstance(v, int):
            raise TypeError("Money.amount에 int 금지. 문자열 사용.")
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, Decimal):
            return v
        raise TypeError(f"Money.amount는 str 또는 Decimal만 허용. 받은 타입: {type(v).__name__}")


class Percent(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    value: Decimal

    @field_validator("value", mode="before")
    @classmethod
    def _value_str_or_decimal_only(cls, v: object) -> Decimal:
        if isinstance(v, float):
            raise TypeError("Percent.value에 float 금지. 문자열 사용.")
        if isinstance(v, int):
            raise TypeError("Percent.value에 int 금지. 문자열 사용.")
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, Decimal):
            return v
        raise TypeError(f"Percent.value는 str 또는 Decimal만 허용. 받은 타입: {type(v).__name__}")

    def as_fraction(self) -> Decimal:
        return self.value / Decimal("100")
