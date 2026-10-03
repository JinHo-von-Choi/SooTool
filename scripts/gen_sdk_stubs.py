"""``sootool.sdk`` 의 정적 타입 선언(``src/sootool/sdk/_typed.py``)을 레지스트리에서 생성한다.

네임스페이스마다 Protocol 클래스를 만들고, 도구마다 시그니처와 결과 TypedDict 를 선언한다. 런타임에는 쓰이지
않고 타입 검사기와 편집기 자동완성만 이 파일을 본다. 숫자 인자를 받는 문자열 파라미터는 ``Num``
(문자열, 정수, Decimal, 부동소수)로 선언한다.

사용:
    uv run python scripts/gen_sdk_stubs.py          # 파일 갱신
    uv run python scripts/gen_sdk_stubs.py --check  # 갱신 없이 최신인지 검사(아니면 종료 코드 1)

작성자: 최진호
작성일: 2026-10-04
"""
from __future__ import annotations

import argparse
import inspect
import sys
import types
import typing
from decimal import Decimal
from pathlib import Path
from typing import Any

from sootool.core.registry import REGISTRY, ToolEntry
from sootool.core.result_types import declared_result_type
from sootool.runtime import NAMESPACE_MODULES, _load_modules
from sootool.sdk import _wants_str

_TARGET = Path(__file__).resolve().parents[1] / "src" / "sootool" / "sdk" / "_typed.py"

_HEADER = '''"""``sootool.sdk`` 의 정적 타입 선언. scripts/gen_sdk_stubs.py 가 생성한다. 직접 고치지 않는다.

런타임에는 가져오지 않는다(``sootool.sdk`` 가 TYPE_CHECKING 일 때만 참조한다).
"""
# ruff: noqa
# mypy: ignore-errors
from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal, Protocol

{imports}

Num = str | int | float | Decimal
'''


class _Renderer:
    def __init__(self) -> None:
        self.modules: dict[str, str] = {}

    def module_alias(self, module: str) -> str:
        return self.modules.setdefault(module, f"_m{len(self.modules)}")

    def render(self, tp: Any, num: bool) -> str:
        if tp is Any:
            return "Any"
        if tp is None or tp is type(None):
            return "None"
        if tp is str:
            return "Num" if num else "str"
        if tp in (int, float, bool, bytes, Decimal):
            return tp.__name__
        origin = typing.get_origin(tp)
        args   = typing.get_args(tp)
        if origin is typing.Literal:
            return "Literal[" + ", ".join(repr(a) for a in args) + "]"
        if origin is typing.Union or origin is types.UnionType:
            return " | ".join(self.render(a, num) for a in args)
        if origin in (list, set, frozenset, tuple) and args:
            inner = ", ".join(self.render(a, num) if a is not Ellipsis else "..." for a in args)
            return f"{origin.__name__}[{inner}]"
        if origin is dict and len(args) == 2:
            return f"dict[{self.render(args[0], False)}, {self.render(args[1], num)}]"
        if isinstance(tp, type) and hasattr(tp, "__annotations__"):
            return f"{self.module_alias(tp.__module__)}.{tp.__name__}"
        raise TypeError(f"스텁으로 옮길 수 없는 타입: {tp!r}")


def _method(renderer: _Renderer, entry: ToolEntry) -> str:
    signature = entry.exposed_signature()
    try:
        hints = typing.get_type_hints(entry.fn)
    except Exception:  # noqa: BLE001
        hints = {}
    parts: list[str] = ["self"]
    keyword_only_started = False
    for name, parameter in signature.parameters.items():
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY and not keyword_only_started:
            parts.append("*")
            keyword_only_started = True
        annotation = hints.get(name, parameter.annotation)
        rendered   = renderer.render(annotation, _wants_str(annotation))
        default    = "" if parameter.default is inspect.Parameter.empty else f" = {parameter.default!r}"
        parts.append(f"{name}: {rendered}{default}")
    declared = declared_result_type(entry.fn)
    returns  = renderer.render(declared, False) if declared is not None else "dict[str, Any]"
    description = " ".join(entry.description.split()).replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return f"    def {entry.name}({', '.join(parts)}) -> {returns}:\n        \"\"\"{description}\"\"\"\n        ..."


def generate() -> str:
    _load_modules()
    renderer = _Renderer()
    classes: list[str] = []
    variables: list[str] = []
    for namespace in sorted(NAMESPACE_MODULES):
        entries = sorted((e for e in REGISTRY.list() if e.namespace == namespace), key=lambda e: e.name)
        if not entries:
            continue
        class_name = f"_{namespace.title().replace('_', '')}Tools"
        body = "\n".join(_method(renderer, e) for e in entries)
        classes.append(f"class {class_name}(Protocol):\n{body}\n")
        variables.append(f"{namespace}: {class_name}")
    imports = "\n".join(f"import {module} as {alias}" for module, alias in sorted(renderer.modules.items()))
    return _HEADER.format(imports=imports) + "\n\n" + "\n\n".join(classes) + "\n\n" + "\n".join(variables) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="갱신하지 않고 최신인지 검사한다")
    args = parser.parse_args()
    content = generate()
    if args.check:
        current = _TARGET.read_text(encoding="utf-8") if _TARGET.exists() else ""
        if current != content:
            print(f"{_TARGET} 이 최신이 아닙니다. scripts/gen_sdk_stubs.py 를 실행하세요.")
            return 1
        return 0
    _TARGET.write_text(content, encoding="utf-8")
    print(f"wrote {_TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
