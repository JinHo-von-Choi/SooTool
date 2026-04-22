import pytest

from sootool.core.decimal_ops import D, add, div, power


def test_D_from_str_preserves_precision():
    assert D("0.1") + D("0.2") == D("0.3")

def test_D_rejects_float_by_default():
    with pytest.raises(TypeError, match="float 입력 금지"):
        D(0.1)

def test_D_accepts_float_when_allow_float_true():
    assert D(0.1, allow_float=True) == D(str(0.1))

def test_add_chains_three_operands():
    assert add(D("1.1"), D("2.2"), D("3.3")) == D("6.6")

def test_div_raises_on_zero():
    with pytest.raises(ZeroDivisionError):
        div(D("1"), D("0"))

def test_power_integer_exponent():
    assert power(D("2"), 10) == D("1024")
