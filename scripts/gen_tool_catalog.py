"""도구 전체 목록 문서(``docs/tool_catalog.md``)를 레지스트리에서 생성한다.

``ToolSpec`` 에서 이름, 버전, 정확도 등급, 동작 특성, 한 줄 설명을 가져온다. 손으로 고치지 않는다.

사용:
    uv run python scripts/gen_tool_catalog.py          # 파일 갱신
    uv run python scripts/gen_tool_catalog.py --check  # 갱신 없이 최신인지 검사(아니면 종료 코드 1)

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sootool.core.registry import REGISTRY
from sootool.core.toolspec import ToolSpec, tool_spec
from sootool.runtime import _load_modules

_TARGET = Path(__file__).resolve().parents[1] / "docs" / "tool_catalog.md"
_SUMMARY_CHARS = 90

_HEADER = """# 도구 카탈로그

scripts/gen_tool_catalog.py 가 레지스트리에서 생성한다. 직접 고치지 않는다. 정확도 등급은 계산 엔진에서 정해진다:
exact(Decimal), high_precision(mpmath, 지정 자릿수), approximate(float64 근사), depends_on_children(호출한 도구에 따름),
not_numeric(수치 계산 아님). 정책 열이 예이면 `year` 와 시점(`as_of`)에 따라 정책 문서를 읽는다.

총 {total}개 도구, {namespaces}개 네임스페이스.
"""


def _summary(description: str) -> str:
    text = " ".join(description.split()).replace("|", "\\|")
    return text if len(text) <= _SUMMARY_CHARS else text[: _SUMMARY_CHARS - 1] + "…"


def generate() -> str:
    _load_modules()
    specs = sorted((tool_spec(e) for e in REGISTRY.list()), key=lambda s: s.full_name)
    by_namespace: dict[str, list[ToolSpec]] = {}
    for spec in specs:
        by_namespace.setdefault(spec.namespace, []).append(spec)
    lines = [_HEADER.format(total=len(specs), namespaces=len(by_namespace))]
    for namespace, items in by_namespace.items():
        lines.append(f"\n## {namespace} ({len(items)})\n")
        lines.append("|도구|버전|정확도|정책|읽기 전용|설명|")
        lines.append("|-|-|-|-|-|-|")
        for spec in items:
            lines.append(
                f"|{spec.name}|{spec.version}|{spec.exactness}|{'예' if spec.policy else ''}|"
                f"{'예' if spec.read_only else '아니오'}|{_summary(spec.description)}|"
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="갱신하지 않고 최신인지 검사한다")
    args = parser.parse_args()
    content = generate()
    if args.check:
        current = _TARGET.read_text(encoding="utf-8") if _TARGET.exists() else ""
        if current != content:
            print(f"{_TARGET} 이 최신이 아닙니다. scripts/gen_tool_catalog.py 를 실행하세요.")
            return 1
        return 0
    _TARGET.write_text(content, encoding="utf-8")
    print(f"wrote {_TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
