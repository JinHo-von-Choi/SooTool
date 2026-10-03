"""Discrete Fourier Transform utilities.

내부 자료형 (ADR-008):
- 입력 샘플(실수)은 Decimal 문자열 리스트 → float64 변환 후 numpy.fft.
- 출력은 복소수 frequency bin 당 (magnitude, phase_rad) Decimal 문자열 쌍 (12 유효숫자).

작성자: 최진호
작성일: 2026-04-23
"""
from __future__ import annotations

import cmath
from typing import Any, TypedDict

import numpy as np

from sootool.core.audit import CalcTrace
from sootool.core.cast import decimal_to_float64, float64_to_decimal_str
from sootool.core.decimal_ops import D
from sootool.core.errors import InvalidInputError
from sootool.core.limits import ensure_max
from sootool.core.registry import REGISTRY
from sootool.core.result_types import TracedResult

_SIG = 12


def _to_float_array(values: list[str], name: str) -> np.ndarray:
    if not isinstance(values, list) or not values:
        raise InvalidInputError(f"{name}은(는) 비어있지 않은 리스트여야 합니다.")
    try:
        return np.array([decimal_to_float64(D(v)) for v in values], dtype=np.float64)
    except Exception as exc:
        raise InvalidInputError(f"{name} 요소는 Decimal 문자열이어야 합니다.") from exc


class FftBin(TypedDict):
    """주파수 bin 하나. k 는 인덱스 문자열."""

    k:         str
    magnitude: str
    phase_rad: str


class IfftComplexSample(TypedDict):
    real: str
    imag: str


class FftResult(TracedResult):
    bins: list[FftBin]
    n:    int


@REGISTRY.tool(
    namespace="math",
    name="fft",
    description=(
        "실수 샘플의 이산 푸리에 변환(DFT)을 numpy.fft 로 계산한다. "
        "samples 는 2개 이상 65536개 이하의 Decimal 문자열 리스트. 각 bin 은 k, magnitude, phase_rad 를 담으며 float64 계산에 유효숫자 12자리이고 1/N 정규화는 하지 않는다. "
        "k 는 주파수가 아니라 인덱스이므로 Hz 는 k * 샘플링주파수 / N 으로 직접 계산한다."
    ),
    version="1.0.0",
)
def fft(samples: list[str]) -> FftResult:
    trace = CalcTrace(
        tool="math.fft",
        formula="X_k = Σ_{n=0}^{N-1} x_n * exp(-2πi k n / N)",
    )
    ensure_max("FFT_SAMPLES", len(samples), "samples")
    arr = _to_float_array(samples, "samples")
    if arr.size < 2:
        raise InvalidInputError("samples는 최소 2개 이상이어야 합니다.")

    trace.input("samples_count", arr.size)

    spectrum = np.fft.fft(arr)
    bins: list[FftBin] = []
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


class IfftResult(TracedResult):
    samples: list[str] | list[IfftComplexSample]


@REGISTRY.tool(
    namespace="math",
    name="ifft",
    description=(
        "fft 결과의 bin 리스트({magnitude, phase_rad})에서 시간 영역 샘플을 복원한다(1/N 정규화 포함). 최대 65536개. real_output 기본 true 는 허수부 절대값이 1e-9 를 넘으면 오류를 내고 문자열 리스트를 반환하며, false 면 {real, imag} 쌍을 반환한다. "
        "bin 은 N개 전체를 순서대로 넣어야 하며 일부만 넣으면 다른 신호가 복원된다."
    ),
    version="1.0.0",
)
def ifft(
    bins:        list[dict[str, str]],
    real_output: bool = True,
) -> IfftResult:
    trace = CalcTrace(
        tool="math.ifft",
        formula="x_n = (1/N) Σ_{k=0}^{N-1} X_k * exp(2πi k n / N)",
    )
    if not isinstance(bins, list) or not bins:
        raise InvalidInputError("bins는 비어있지 않은 리스트여야 합니다.")
    ensure_max("FFT_SAMPLES", len(bins), "bins")

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
