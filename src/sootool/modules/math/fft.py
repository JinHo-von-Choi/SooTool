"""Discrete Fourier Transform utilities.

내부 자료형 (ADR-008):
- 입력 샘플(실수)은 Decimal 문자열 리스트 → float64 변환 후 numpy.fft.
- 출력은 복소수 frequency bin 당 (magnitude, phase_rad) Decimal 문자열 쌍 (12 유효숫자).

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

import cmath
from typing import Any

import numpy as np

from sootool.core.audit import CalcTrace
from sootool.core.cast import decimal_to_float64, float64_to_decimal_str
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.registry import REGISTRY

_SIG = 12


def _to_float_array(values: list[str], name: str) -> np.ndarray:
    if not isinstance(values, list) or not values:
        raise InvalidInputError(f"{name}은(는) 비어있지 않은 리스트여야 합니다.")
    try:
        return np.array([decimal_to_float64(D(v)) for v in values], dtype=np.float64)
    except Exception as exc:
        raise InvalidInputError(f"{name} 요소는 Decimal 문자열이어야 합니다.") from exc


@REGISTRY.tool(
    namespace="math",
    name="fft",
    description=(
        "이산 푸리에 변환 (DFT): 실수 샘플 → 복소수 bin 리스트. "
        "각 bin은 {magnitude, phase_rad} Decimal 문자열 쌍. numpy.fft 기반."
    ),
    version="1.0.0",
)
def fft(samples: list[str]) -> dict[str, Any]:
    trace = CalcTrace(
        tool="math.fft",
        formula="X_k = Σ_{n=0}^{N-1} x_n * exp(-2πi k n / N)",
    )
    arr = _to_float_array(samples, "samples")
    if arr.size < 2:
        raise InvalidInputError("samples는 최소 2개 이상이어야 합니다.")

    trace.input("samples_count", arr.size)

    spectrum = np.fft.fft(arr)
    bins: list[dict[str, str]] = []
    for k, c in enumerate(spectrum):
        mag = abs(c)
        phase = cmath.phase(complex(c))
        bins.append({
            "k":          str(k),
            "magnitude":  float64_to_decimal_str(float(mag),   digits=_SIG),
            "phase_rad":  float64_to_decimal_str(float(phase), digits=_SIG),
        })

    trace.step("bins_count", len(bins))
    trace.output({"bins_count": len(bins)})

    return {"bins": bins, "n": arr.size, "trace": trace.to_dict()}


@REGISTRY.tool(
    namespace="math",
    name="ifft",
    description=(
        "역 이산 푸리에 변환. 복소수 bin 리스트 ({magnitude, phase_rad}) → 실수/복소수 샘플 복원. "
        "real_output=true 면 허수부 절대값이 1e-9 미만인 경우 실수만 반환."
    ),
    version="1.0.0",
)
def ifft(
    bins:        list[dict[str, str]],
    real_output: bool = True,
) -> dict[str, Any]:
    trace = CalcTrace(
        tool="math.ifft",
        formula="x_n = (1/N) Σ_{k=0}^{N-1} X_k * exp(2πi k n / N)",
    )
    if not isinstance(bins, list) or not bins:
        raise InvalidInputError("bins는 비어있지 않은 리스트여야 합니다.")

    complex_arr = np.empty(len(bins), dtype=np.complex128)
    for i, b in enumerate(bins):
        if "magnitude" not in b or "phase_rad" not in b:
            raise InvalidInputError("각 bin은 magnitude, phase_rad 필드를 가져야 합니다.")
        mag   = decimal_to_float64(D(b["magnitude"]))
        phase = decimal_to_float64(D(b["phase_rad"]))
        complex_arr[i] = mag * np.exp(1j * phase)

    trace.input("bins_count", len(bins))
    trace.input("real_output", real_output)

    time = np.fft.ifft(complex_arr)
    out_samples: list[Any] = []
    if real_output:
        max_im = float(np.max(np.abs(time.imag)))
        if max_im > 1e-9:
            raise InvalidInputError(
                f"real_output=True 이나 허수부가 큽니다 (max={max_im})."
            )
        for v in time.real:
            out_samples.append(float64_to_decimal_str(float(v), digits=_SIG))
    else:
        for v in time:
            out_samples.append({
                "real": float64_to_decimal_str(float(v.real), digits=_SIG),
                "imag": float64_to_decimal_str(float(v.imag), digits=_SIG),
            })

    trace.step("samples_count", len(out_samples))
    trace.output({"samples_count": len(out_samples)})

    return {"samples": out_samples, "trace": trace.to_dict()}
