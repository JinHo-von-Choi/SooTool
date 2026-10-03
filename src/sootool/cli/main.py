"""명령줄 진입점과 서브커맨드.

사용:
    sootool call <tool> [--arg-json JSON] [--arg 이름=값 ...] [--format pretty|json|raw|trace]
    sootool tools list [--search 질의] [--domain 네임스페이스]
    sootool tools describe <tool>
    sootool batch -f items.json          sootool pipeline -f steps.json
    sootool receipt verify --tool T --arguments JSON --receipt FILE [--public-key B64]
    sootool policy list|show|history|export ...  (쓰기: propose|activate|rollback|import, 관리자 모드 필요)
    sootool pack build|verify|install ...        (서명된 외부 정책 팩, install 은 관리자 모드 필요)
    sootool skill-guide [--section S] [--lang ko|en]
    sootool version

모든 호출은 REGISTRY.invoke 경로를 거치므로 MCP 호출과 같은 결과, 영수증, 오류 코드를 낸다. 서브커맨드가
없으면 서버로 기동한다(기존 플래그 그대로).

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sootool.boundary import error_payload
from sootool.cli import exit_codes as codes
from sootool.cli.binder import bind_arguments, parse_assignment
from sootool.cli.formatters import FORMATS, format_error, format_result
from sootool.core.catalog import describe_tool, resolve_tool, search_tools
from sootool.core.errors import InvalidInputError, SooToolError
from sootool.core.registry import REGISTRY

SUBCOMMANDS = frozenset({"call", "tools", "batch", "pipeline", "receipt", "policy", "pack", "skill-guide", "version"})

_ADMIN_ENV = "SOOTOOL_ADMIN_MODE"
_POLICY_READ_TOOLS = {
    "list": "sootool.policy_list", "show": "sootool.policy_get", "history": "sootool.policy_history",
    "export": "sootool.policy_export", "validate": "sootool.policy_validate", "diff": "sootool.policy_diff",
}
_POLICY_WRITE_TOOLS = {
    "propose": "sootool.policy_propose", "activate": "sootool.policy_activate",
    "rollback": "sootool.policy_rollback", "import": "sootool.policy_import",
}


class AdminDenied(Exception):
    """쓰기 도구를 관리자 모드 없이 호출했다."""


def _read_json(source: str) -> Any:
    """파일 경로 또는 ``-``(표준입력)에서 JSON 을 읽는다."""
    text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidInputError(f"JSON 을 읽을 수 없습니다({source}): {exc}") from exc


def _json_arg(text: str, label: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidInputError(f"{label} 는 JSON 객체여야 합니다: {exc}") from exc
    if not isinstance(value, dict):
        raise InvalidInputError(f"{label} 는 JSON 객체여야 합니다.")
    return value


def _is_admin() -> bool:
    import os

    return os.environ.get(_ADMIN_ENV, "").strip() in ("1", "true", "yes")


def _invoke(tool: str, raw_arguments: dict[str, Any]) -> Any:
    """도구를 검증하고 REGISTRY.invoke 로 실행한다. 쓰기 도구는 관리자 모드를 요구한다."""
    entry = resolve_tool(REGISTRY, tool)
    if not entry.read_only and not _is_admin():
        raise AdminDenied(f"{entry.full_name} 은(는) 쓰기 도구입니다. {_ADMIN_ENV}=1 로 관리자 모드를 켜세요.")
    return REGISTRY.invoke(entry.full_name, **bind_arguments(entry, raw_arguments))


def _emit(result: Any, fmt: str) -> int:
    print(format_result(result, fmt))
    return codes.OK


# --- 서브커맨드 ---

def _cmd_call(args: argparse.Namespace) -> int:
    entry = resolve_tool(REGISTRY, args.tool)
    raw: dict[str, Any] = _json_arg(args.arg_json, "--arg-json") if args.arg_json else {}
    for assignment in args.arg:
        name, value = parse_assignment(entry, assignment)
        raw[name] = value
    return _emit(_invoke(entry.full_name, raw), args.format)


def _cmd_tools(args: argparse.Namespace) -> int:
    if args.action == "describe":
        return _emit(describe_tool(resolve_tool(REGISTRY, args.name)), "json")
    if args.search:
        rows = search_tools(REGISTRY, args.search, limit=args.limit, namespace=args.domain)
        print("\n".join(f"{row['name']}\t{row['summary']}" for row in rows))
        return codes.OK
    entries = [e for e in REGISTRY.list() if args.domain is None or e.namespace == args.domain]
    print("\n".join(f"{e.full_name}\t{e.version}\t{' '.join(e.description.split())[:100]}"
                    for e in sorted(entries, key=lambda e: e.full_name)))
    return codes.OK


def _cmd_batch(args: argparse.Namespace) -> int:
    return _emit(_invoke("core.batch", {"items": _read_json(args.file)}), args.format)


def _cmd_pipeline(args: argparse.Namespace) -> int:
    return _emit(_invoke("core.pipeline", {"steps": _read_json(args.file)}), args.format)


def _cmd_receipt(args: argparse.Namespace) -> int:
    raw: dict[str, Any] = {
        "tool":      args.tool,
        "arguments": _json_arg(args.arguments, "--arguments"),
        "receipt":   _read_json(args.receipt),
    }
    if args.public_key:
        raw["public_key_b64"] = args.public_key
    if args.require_signature:
        raw["require_signature"] = True
    result = _invoke("sootool.verify_receipt", raw)
    print(format_result(result, args.format))
    return codes.OK if result["valid"] else codes.TOOL_ERROR


def _cmd_policy(args: argparse.Namespace) -> int:
    action = args.action
    tool   = _POLICY_READ_TOOLS.get(action) or _POLICY_WRITE_TOOLS[action]
    raw: dict[str, Any] = _json_arg(args.arg_json, "--arg-json") if args.arg_json else {}
    entry = resolve_tool(REGISTRY, tool)
    for assignment in args.arg:
        name, value = parse_assignment(entry, assignment)
        raw[name] = value
    return _emit(_invoke(tool, raw), args.format)


def _cmd_pack(args: argparse.Namespace) -> int:
    from sootool.policy_mgmt import packs

    if args.action == "build":
        manifest = _read_json(args.manifest)
        bundles  = [_read_json(path) for path in args.bundle]
        print(json.dumps(packs.build_pack(manifest, bundles), ensure_ascii=False, indent=2))
        return codes.OK
    pack = _read_json(args.file)
    if args.action == "verify":
        return _emit({"verified": True, "bundles": packs.verify_pack(pack, args.public_key)}, args.format)
    if not _is_admin():
        raise AdminDenied(f"정책 팩 설치는 쓰기 작업입니다. {_ADMIN_ENV}=1 로 관리자 모드를 켜세요.")
    results = packs.install_pack(pack, args.public_key)
    _emit({"installed": all(r["installed"] for r in results), "bundles": results}, args.format)
    return codes.OK if all(r["installed"] for r in results) else codes.TOOL_ERROR


def _cmd_skill_guide(args: argparse.Namespace) -> int:
    raw: dict[str, Any] = {"section": args.section}
    if args.lang:
        raw["lang"] = args.lang
    return _emit(_invoke("sootool.skill_guide", raw), "json")


def _cmd_version(args: argparse.Namespace) -> int:
    import platform
    from importlib.metadata import version as package_version

    info = {
        "sootool": package_version("sootool"),
        "mcp":     package_version("mcp"),
        "python":  platform.python_version(),
        "tools":   len(REGISTRY.list()),
    }
    if args.format == "json":
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        print(f"sootool {info['sootool']} (mcp {info['mcp']}, python {info['python']}, {info['tools']} tools)")
    return codes.OK


# --- 파서 ---

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sootool",
        description="SooTool: 결정적 계산 도구. 서브커맨드 없이 실행하면 MCP 서버로 기동한다.",
    )
    parser.add_argument("--format", choices=FORMATS, default="pretty", help="결과 출력 형식(기본 pretty)")
    commands = parser.add_subparsers(dest="command", required=True)

    def with_format(sub: argparse.ArgumentParser) -> argparse.ArgumentParser:
        sub.add_argument("--format", choices=FORMATS, default=argparse.SUPPRESS, help="결과 출력 형식")
        return sub

    call = with_format(commands.add_parser("call", help="도구 하나를 실행한다"))
    call.add_argument("tool", help="도구 이름(예: tax.kr_income)")
    call.add_argument("--arg-json", default="", help="인자 전체를 JSON 객체로 전달")
    call.add_argument("--arg", action="append", default=[], metavar="이름=값", help="인자 하나(여러 번 지정 가능)")
    call.set_defaults(handler=_cmd_call)

    tools = commands.add_parser("tools", help="도구 목록과 설명")
    tools.add_argument("action", choices=("list", "describe"))
    tools.add_argument("name", nargs="?", help="describe 대상 도구 이름")
    tools.add_argument("--search", help="질의어로 검색(별칭 포함)")
    tools.add_argument("--domain", help="네임스페이스로 제한")
    tools.add_argument("--limit", type=int, default=10, help="검색 결과 수(기본 10)")
    tools.set_defaults(handler=_cmd_tools)

    for name, handler, helptext in (
        ("batch", _cmd_batch, "독립 호출 여러 건을 실행한다"),
        ("pipeline", _cmd_pipeline, "의존 관계가 있는 호출을 순서대로 실행한다"),
    ):
        sub = with_format(commands.add_parser(name, help=helptext))
        sub.add_argument("-f", "--file", required=True, help="JSON 파일 경로 또는 - (표준입력)")
        sub.set_defaults(handler=handler)

    receipt = commands.add_parser("receipt", help="계산 영수증")
    receipt_actions = receipt.add_subparsers(dest="action", required=True)
    verify = with_format(receipt_actions.add_parser("verify", help="영수증을 재실행으로 검증한다"))
    verify.add_argument("--tool", required=True)
    verify.add_argument("--arguments", required=True, help="원래 호출 인자(JSON 객체)")
    verify.add_argument("--receipt", required=True, help="영수증(_meta.integrity) JSON 파일 또는 -")
    verify.add_argument("--public-key", help="서명 검증용 base64 ed25519 공개 키")
    verify.add_argument("--require-signature", action="store_true", help="서명이 없으면 실패")
    verify.set_defaults(handler=_cmd_receipt)

    policy = commands.add_parser("policy", help="정책 조회와 관리(쓰기는 관리자 모드)")
    policy.add_argument("action", choices=sorted({*_POLICY_READ_TOOLS, *_POLICY_WRITE_TOOLS}))
    policy.add_argument("--arg-json", default="", help="인자 전체를 JSON 객체로 전달")
    policy.add_argument("--arg", action="append", default=[], metavar="이름=값")
    policy.add_argument("--format", choices=FORMATS, default=argparse.SUPPRESS)
    policy.set_defaults(handler=_cmd_policy)

    pack = commands.add_parser("pack", help="서명된 외부 정책 팩 생성, 검증, 설치")
    pack_actions = pack.add_subparsers(dest="action", required=True)
    pack_build = pack_actions.add_parser("build", help="번들 파일들을 서명된 팩으로 묶는다(SOOTOOL_POLICY_KEY_FILE 필요)")
    pack_build.add_argument("--manifest", required=True, help="name, version, publisher 를 가진 JSON 파일")
    pack_build.add_argument("--bundle", action="append", required=True, help="policy_export 번들 JSON 파일(여러 번 지정)")
    for name, helptext in (("verify", "팩 서명과 번들 서명을 검증한다"), ("install", "검증 뒤 번들을 가져온다(관리자 모드)")):
        sub = with_format(pack_actions.add_parser(name, help=helptext))
        sub.add_argument("file", help="팩 JSON 파일 또는 -")
        sub.add_argument("--public-key", required=True, help="제공자의 base64 ed25519 공개 키")
    pack.set_defaults(handler=_cmd_pack)

    guide = commands.add_parser("skill-guide", help="에이전트 활용 가이드")
    guide.add_argument("--section", default="all", choices=("all", "triggers", "examples", "anti_patterns", "playbooks"))
    guide.add_argument("--lang", choices=("ko", "en"))
    guide.set_defaults(handler=_cmd_skill_guide)

    version = with_format(commands.add_parser("version", help="버전 정보"))
    version.set_defaults(handler=_cmd_version)
    return parser


def run(argv: list[str]) -> int:
    """서브커맨드를 실행하고 종료 코드를 반환한다."""
    from sootool.server import _load_modules

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")

    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return codes.OK if exc.code in (0, None) else codes.INPUT_ERROR

    _load_modules()
    try:
        return int(args.handler(args))
    except AdminDenied as exc:
        print(format_error({"code": "admin_required", "message": str(exc), "retryable": False}), file=sys.stderr)
        return codes.ADMIN_DENIED
    except SooToolError as exc:
        print(format_error(error_payload(exc)), file=sys.stderr)
        return codes.INPUT_ERROR if isinstance(exc, InvalidInputError) else codes.TOOL_ERROR
    except (OSError, UnicodeDecodeError) as exc:
        print(format_error({"code": "invalid_input", "message": str(exc), "retryable": False}), file=sys.stderr)
        return codes.INPUT_ERROR
    except Exception as exc:  # noqa: BLE001
        print(format_error(error_payload(exc)), file=sys.stderr)
        return codes.INTERNAL_ERROR
