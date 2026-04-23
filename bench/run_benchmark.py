"""SooTool 벤치마크 리트머스 실행기 (FB-M3).

작성자: 최진호
작성일: 2026-04-24

cases.yaml 에 정의된 20 케이스를 다음 경로로 평가한다.

1. SooTool ground truth — REGISTRY.invoke() 직접 호출하여 Decimal 정답 확정.
2. LLM 비교 — OpenAI / Anthropic / Google GenAI SDK 를 런타임 import.
   - SDK 미설치 또는 API 키 미설정 시 해당 LLM 을 graceful skip.
   - 응답 텍스트에서 숫자 추출 후 기대값과 비교.

결과는 results/YYYY-MM-DD.md 파일로 저장된다.

CI 에서 실행하지 않는다 (API 비용 발생). 로컬에서 수동 실행용.

사용법::

    uv run python bench/run_benchmark.py                # 결과 파일 자동 이름
    uv run python bench/run_benchmark.py --out path.md  # 출력 경로 지정
    uv run python bench/run_benchmark.py --skip-llm     # SooTool ground truth 만

환경변수:
    OPENAI_API_KEY    — OpenAI chat 모델 호출
    ANTHROPIC_API_KEY — Anthropic Claude 모델 호출
    GOOGLE_API_KEY    — Google GenAI (Gemini) 모델 호출
    SOOTOOL_BENCH_OPENAI_MODEL    기본 gpt-4o
    SOOTOOL_BENCH_ANTHROPIC_MODEL 기본 claude-3-7-sonnet-latest
    SOOTOOL_BENCH_GOOGLE_MODEL    기본 gemini-2.5-pro

LLM 응답 매칭 규칙:
    exact  — 문자열 정규화 후 정확 일치
    approx — 상대오차 |llm - expected| / |expected| <= 1e-4
    wrong  — 위 두 조건 모두 실패
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml

from sootool.core.registry import REGISTRY
from sootool.server import _load_modules

_BENCH_DIR     = Path(__file__).resolve().parent
_CASES_YAML    = _BENCH_DIR / "cases.yaml"
_RESULTS_DIR   = _BENCH_DIR / "results"
_APPROX_TOL    = Decimal("0.0001")  # 상대오차 0.01%


# ---------------------------------------------------------------------------
# LLM adapters — SDK 를 런타임 import 하여 미설치 상황에서도 graceful skip.
# ---------------------------------------------------------------------------


@dataclass
class LLMResult:
    provider: str
    model:    str
    raw:      str | None   # LLM 원문 응답
    number:   Decimal | None
    error:    str | None = None


def _call_openai(prompt: str) -> LLMResult:
    provider = "openai"
    model    = os.environ.get("SOOTOOL_BENCH_OPENAI_MODEL", "gpt-4o")
    key      = os.environ.get("OPENAI_API_KEY")
    if not key:
        return LLMResult(provider, model, None, None, "OPENAI_API_KEY not set")
    try:
        from openai import OpenAI  # noqa: PLC0415
    except ImportError as exc:
        return LLMResult(provider, model, None, None, f"openai SDK not installed: {exc}")
    try:
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a precise calculator. Answer with a single number only."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0,
        )
        raw = resp.choices[0].message.content or ""
        return LLMResult(provider, model, raw, _extract_number(raw), None)
    except Exception as exc:  # noqa: BLE001
        return LLMResult(provider, model, None, None, f"openai call failed: {exc}")


def _call_anthropic(prompt: str) -> LLMResult:
    provider = "anthropic"
    model    = os.environ.get("SOOTOOL_BENCH_ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")
    key      = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return LLMResult(provider, model, None, None, "ANTHROPIC_API_KEY not set")
    try:
        import anthropic  # noqa: PLC0415
    except ImportError as exc:
        return LLMResult(provider, model, None, None, f"anthropic SDK not installed: {exc}")
    try:
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=model,
            max_tokens=256,
            temperature=0,
            system="You are a precise calculator. Answer with a single number only.",
            messages=[{"role": "user", "content": prompt}],
        )
        parts: list[str] = []
        for block in msg.content:
            txt = getattr(block, "text", None)
            if txt:
                parts.append(txt)
        raw = "".join(parts)
        return LLMResult(provider, model, raw, _extract_number(raw), None)
    except Exception as exc:  # noqa: BLE001
        return LLMResult(provider, model, None, None, f"anthropic call failed: {exc}")


def _call_google(prompt: str) -> LLMResult:
    provider = "google"
    model    = os.environ.get("SOOTOOL_BENCH_GOOGLE_MODEL", "gemini-2.5-pro")
    key      = os.environ.get("GOOGLE_API_KEY")
    if not key:
        return LLMResult(provider, model, None, None, "GOOGLE_API_KEY not set")
    try:
        from google import genai  # noqa: PLC0415
    except ImportError as exc:
        return LLMResult(provider, model, None, None, f"google-genai SDK not installed: {exc}")
    try:
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model=model,
            contents=(
                "You are a precise calculator. Answer with a single number only.\n\n"
                + prompt
            ),
        )
        raw = getattr(resp, "text", None) or ""
        return LLMResult(provider, model, raw, _extract_number(raw), None)
    except Exception as exc:  # noqa: BLE001
        return LLMResult(provider, model, None, None, f"google call failed: {exc}")


_LLM_PROVIDERS = [_call_openai, _call_anthropic, _call_google]


# ---------------------------------------------------------------------------
# Number extraction and comparison
# ---------------------------------------------------------------------------


_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*(?:[eE][+-]?\d+)?")


def _extract_number(text: str) -> Decimal | None:
    """Extract the first plausible Decimal-castable number from LLM text."""
    if not text:
        return None
    cleaned = text.replace(",", "")
    matches = _NUMBER_RE.findall(cleaned)
    if not matches:
        return None
    for m in matches:
        m_clean = m.replace(",", "")
        if m_clean in ("", "-", ".", "-."):
            continue
        try:
            return Decimal(m_clean)
        except InvalidOperation:
            continue
    return None


def _classify(expected: Decimal, actual: Decimal | None) -> str:
    """Return 'exact' | 'approx' | 'wrong' | 'no_answer'."""
    if actual is None:
        return "no_answer"
    if actual == expected:
        return "exact"
    if expected == 0:
        return "wrong"
    rel = abs(actual - expected) / abs(expected)
    return "approx" if rel <= _APPROX_TOL else "wrong"


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _sootool_value(case: dict[str, Any]) -> Decimal:
    tc = case["tool_call"]
    result = REGISTRY.invoke(tc["tool"], **tc["args"])
    field  = tc["field"]
    return Decimal(str(result[field]))


def _run_cases(
    cases:     list[dict[str, Any]],
    *,
    skip_llm:  bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for c in cases:
        expected = Decimal(c["expected_decimal_string"])
        soo_val  = _sootool_value(c)
        soo_cls  = _classify(expected, soo_val)

        row: dict[str, Any] = {
            "id":            c["id"],
            "category":      c["category"],
            "difficulty":    c["difficulty"],
            "expected":      str(expected),
            "sootool_value": str(soo_val),
            "sootool_class": soo_cls,
            "llms":          {},
        }

        if not skip_llm:
            for fn in _LLM_PROVIDERS:
                res = fn(c["prompt"])
                row["llms"][res.provider] = {
                    "model":  res.model,
                    "raw":    res.raw,
                    "number": str(res.number) if res.number is not None else None,
                    "class":  _classify(expected, res.number),
                    "error":  res.error,
                }

        rows.append(row)
        print(
            f"  - {c['id']:<38} sootool={soo_cls}",
            flush=True,
        )
    return rows


def _render_markdown(rows: list[dict[str, Any]], *, skip_llm: bool) -> str:
    today = _dt.date.today().isoformat()
    lines: list[str] = []
    lines.append(f"# SooTool 벤치마크 리트머스 결과 — {today}")
    lines.append("")
    lines.append("자동 생성 파일. `bench/run_benchmark.py` 실행 결과.")
    lines.append("")
    lines.append("분류: `exact` 문자열 일치, `approx` 상대오차 ≤ 0.01%, `wrong` 그 외, `no_answer` 응답 없음.")
    lines.append("")

    providers = ["openai", "anthropic", "google"]

    if skip_llm:
        lines.append("## SooTool ground truth (LLM 비교 생략)")
        lines.append("")
        lines.append("|id|category|difficulty|expected|sootool|class|")
        lines.append("|-|-|-|-|-|-|")
        for r in rows:
            lines.append(
                f"|{r['id']}|{r['category']}|{r['difficulty']}|"
                f"{r['expected']}|{r['sootool_value']}|{r['sootool_class']}|"
            )
        return "\n".join(lines) + "\n"

    lines.append("## 종합 표")
    lines.append("")
    header = "|id|expected|sootool|" + "|".join(providers) + "|"
    lines.append(header)
    lines.append("|-|-|-|-|-|-|")
    for r in rows:
        cells = [r["id"], r["expected"], r["sootool_class"]]
        for p in providers:
            llm = r["llms"].get(p, {})
            if llm.get("error"):
                cells.append(f"skip ({llm['error'][:24]})")
            else:
                num = llm.get("number") or "-"
                cells.append(f"{llm.get('class','?')} ({num})")
        lines.append("|" + "|".join(cells) + "|")

    lines.append("")
    lines.append("## 집계")
    lines.append("")
    lines.append("|provider|exact|approx|wrong|no_answer|skip|")
    lines.append("|-|-|-|-|-|-|")

    def _count_stats(stats: dict[str, int]) -> str:
        return (
            f"{stats.get('exact',0)}|{stats.get('approx',0)}|"
            f"{stats.get('wrong',0)}|{stats.get('no_answer',0)}|{stats.get('skip',0)}"
        )

    soo_stats: dict[str, int] = {}
    for r in rows:
        soo_stats[r["sootool_class"]] = soo_stats.get(r["sootool_class"], 0) + 1
    lines.append(f"|sootool|{_count_stats(soo_stats)}|")

    for p in providers:
        stats: dict[str, int] = {}
        for r in rows:
            entry = r["llms"].get(p, {})
            if entry.get("error"):
                stats["skip"] = stats.get("skip", 0) + 1
            else:
                cls = entry.get("class", "no_answer")
                stats[cls] = stats.get(cls, 0) + 1
        lines.append(f"|{p}|{_count_stats(stats)}|")

    lines.append("")
    lines.append("## 상세 로그")
    lines.append("")
    for r in rows:
        lines.append(f"### {r['id']} ({r['category']}, {r['difficulty']})")
        lines.append("")
        lines.append(f"- expected: `{r['expected']}`")
        lines.append(f"- sootool: `{r['sootool_value']}` ({r['sootool_class']})")
        for p in providers:
            llm = r["llms"].get(p, {})
            if llm.get("error"):
                lines.append(f"- {p}: skip — {llm['error']}")
            else:
                raw = (llm.get("raw") or "").strip().replace("\n", " ")
                if len(raw) > 200:
                    raw = raw[:200] + "..."
                lines.append(
                    f"- {p} ({llm.get('model')}): `{llm.get('number','-')}` "
                    f"{llm.get('class','?')} — raw=`{raw}`"
                )
        lines.append("")
    return "\n".join(lines) + "\n"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SooTool 벤치마크 리트머스 실행기")
    p.add_argument("--out", type=Path, default=None,
                   help="출력 파일 경로 (기본: bench/results/YYYY-MM-DD.md)")
    p.add_argument("--skip-llm", action="store_true",
                   help="LLM 호출 생략, SooTool ground truth 만 기록")
    p.add_argument("--cases", type=Path, default=_CASES_YAML,
                   help="cases.yaml 경로")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(sys.argv[1:] if argv is None else argv))

    _load_modules()

    doc   = yaml.safe_load(args.cases.read_text(encoding="utf-8"))
    cases = doc["cases"]
    print(f"bench: 케이스 {len(cases)}건 로드")

    rows = _run_cases(cases, skip_llm=args.skip_llm)
    md   = _render_markdown(rows, skip_llm=args.skip_llm)

    out_path = args.out or (_RESULTS_DIR / f"{_dt.date.today().isoformat()}.md")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"bench: 결과 저장 → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
