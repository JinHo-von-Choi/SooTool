from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from sootool.cli import exit_codes as codes
from sootool.cli.main import SUBCOMMANDS, run


def _run(argv: list[str], capsys) -> tuple[int, str, str]:
    code = run(argv)
    out, err = capsys.readouterr()
    return code, out, err


def _json(out: str) -> Any:
    return json.loads(out)


# --- call ---

def test_call_with_assignments_returns_the_tool_result(capsys):
    code, out, _ = _run(["call", "core.add", "--arg", "operands=[1,2.5]", "--format", "raw"], capsys)
    assert code == codes.OK
    assert _json(out) == {"result": "3.5"}


def test_call_with_arg_json(capsys):
    code, out, _ = _run(["call", "finance.fv", "--arg-json", '{"present_value":"1000","rate":"0.05","periods":10}',
                         "--format", "raw"], capsys)
    assert code == codes.OK and _json(out)["fv"] == "1628.89"


def test_assignments_override_arg_json(capsys):
    code, out, _ = _run(["call", "core.sub", "--arg-json", '{"a":"10","b":"3"}', "--arg", "b=4", "--format", "raw"], capsys)
    assert _json(out)["result"] == "6"


def test_string_parameters_keep_numeric_text_exactly(capsys):
    code, out, _ = _run(["call", "core.add", "--arg", 'operands=["0.10","0.20"]', "--format", "raw"], capsys)
    assert _json(out)["result"] == "0.30"


def test_policy_arguments_are_accepted_for_policy_tools(capsys):
    code, out, _ = _run(["call", "tax.kr_income", "--arg", "taxable_income=50000000", "--arg", "year=2026",
                         "--arg", "as_of=2026-06-01", "--format", "raw"], capsys)
    assert code == codes.OK and _json(out)["tax"] == "6240000"


@pytest.mark.parametrize("fmt", ["pretty", "json", "raw", "trace"])
def test_all_output_formats_work(capsys, fmt):
    code, out, _ = _run(["call", "core.add", "--arg", "operands=[1,2]", "--format", fmt], capsys)
    assert code == codes.OK and out.strip()
    if fmt == "json":
        assert "_meta" in _json(out)
    if fmt == "trace":
        assert _json(out)["tool"] == "core.add"
    if fmt == "raw":
        assert "trace" not in _json(out) and "_meta" not in _json(out)
    if fmt == "pretty":
        assert "result: 3" in out and "-- receipt:" in out


def test_global_format_flag_before_the_subcommand(capsys):
    code, out, _ = _run(["--format", "raw", "call", "core.add", "--arg", "operands=[1,2]"], capsys)
    assert code == codes.OK and _json(out) == {"result": "3"}


# --- 오류와 종료 코드 ---

def test_missing_required_argument_is_an_input_error(capsys):
    code, _, err = _run(["call", "tax.kr_income", "--arg", "year=2026"], capsys)
    assert code == codes.INPUT_ERROR
    assert _json(err)["error"]["code"] == "invalid_arguments"


def test_unknown_tool_is_an_input_error_with_candidates(capsys):
    code, _, err = _run(["call", "finance.loan"], capsys)
    assert code == codes.INPUT_ERROR
    assert "finance.loan_schedule" in _json(err)["error"]["message"]


def test_unexpected_argument_name_is_rejected(capsys):
    code, _, err = _run(["call", "core.add", "--arg", "operandz=[1]"], capsys)
    assert code == codes.INPUT_ERROR


def test_malformed_assignment_and_json_are_input_errors(capsys):
    assert _run(["call", "core.add", "--arg", "operands"], capsys)[0] == codes.INPUT_ERROR
    assert _run(["call", "core.add", "--arg-json", "{nope"], capsys)[0] == codes.INPUT_ERROR
    assert _run(["call", "core.add", "--arg-json", "[1]"], capsys)[0] == codes.INPUT_ERROR


def test_tool_domain_errors_exit_with_the_tool_error_code(capsys):
    code, _, err = _run(["call", "core.div", "--arg", "a=1", "--arg", "b=0"], capsys)
    assert code == codes.TOOL_ERROR
    assert _json(err)["error"]["code"] == "division_by_zero"


def test_input_limit_errors_are_tool_errors(capsys):
    code, _, err = _run(["call", "probability.factorial", "--arg", "n=1000000"], capsys)
    assert code == codes.TOOL_ERROR and _json(err)["error"]["code"] == "input_limit"


def test_usage_errors_exit_with_the_input_error_code(capsys):
    assert _run(["call"], capsys)[0] == codes.INPUT_ERROR
    assert _run(["call", "core.add", "--format", "xml"], capsys)[0] == codes.INPUT_ERROR


def test_help_exits_successfully(capsys):
    assert _run(["--help"], capsys)[0] == codes.OK


# --- tools / version / skill-guide ---

def test_tools_list_filters_by_domain(capsys):
    code, out, _ = _run(["tools", "list", "--domain", "tax_us"], capsys)
    names = [line.split("\t")[0] for line in out.strip().splitlines()]
    assert code == codes.OK and names == sorted(names) and all(n.startswith("tax_us.") for n in names) and names


def test_tools_search_uses_aliases(capsys):
    code, out, _ = _run(["tools", "list", "--search", "양도세", "--limit", "3"], capsys)
    assert "tax.capital_gains_kr" in out


def test_tools_describe_includes_policy_arguments(capsys):
    code, out, _ = _run(["tools", "describe", "tax.kr_income"], capsys)
    info = _json(out)
    assert [p["name"] for p in info["parameters"]][-2:] == ["as_of", "include_proposed"]


def test_version_text_and_json(capsys):
    text = _run(["version"], capsys)[1]
    assert text.startswith("sootool ") and "mcp 2." in text
    info = _json(_run(["version", "--format", "json"], capsys)[1])
    assert info["tools"] >= 269 and set(info) == {"sootool", "mcp", "python", "tools"}


def test_skill_guide_command(capsys):
    code, out, _ = _run(["skill-guide", "--section", "triggers", "--lang", "en"], capsys)
    assert code == codes.OK and _json(out)["locale"] == "en"


# --- batch / pipeline / stdin ---

def test_batch_from_a_file(capsys, tmp_path):
    file = tmp_path / "items.json"
    file.write_text(json.dumps([{"id": "a", "tool": "core.add", "args": {"operands": ["1", "2"]}}]), encoding="utf-8")
    code, out, _ = _run(["batch", "-f", str(file), "--format", "raw"], capsys)
    assert code == codes.OK and _json(out)["results"][0]["result"]["result"] == "3"


def test_pipeline_from_stdin(capsys, monkeypatch):
    import io

    steps = [{"id": "s1", "tool": "core.add", "args": {"operands": ["1", "2"]}},
             {"id": "s2", "tool": "core.mul", "args": {"operands": ["${s1.result.result}", "4"]}}]
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(steps)))
    code, out, _ = _run(["pipeline", "-f", "-", "--format", "raw"], capsys)
    result = _json(out)
    assert code == codes.OK and result["status"] == "ok"
    assert result["steps"]["s2"]["result"]["result"] == "12"


def test_missing_batch_file_is_an_input_error(capsys, tmp_path):
    assert _run(["batch", "-f", str(tmp_path / "absent.json")], capsys)[0] == codes.INPUT_ERROR


# --- receipt verify ---

def test_receipt_verify_roundtrip_and_tamper_detection(capsys, tmp_path):
    produced = _json(_run(["call", "finance.fv", "--arg-json", '{"present_value":"1000","rate":"0.05","periods":10}',
                           "--format", "json"], capsys)[1])
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(produced["_meta"]["integrity"]), encoding="utf-8")
    args = ["receipt", "verify", "--tool", "finance.fv",
            "--arguments", '{"present_value":"1000","rate":"0.05","periods":10}', "--receipt", str(receipt), "--format", "raw"]
    code, out, _ = _run(args, capsys)
    assert code == codes.OK and _json(out)["valid"] is True

    tampered = json.loads(receipt.read_text(encoding="utf-8"))
    tampered["result_hash"] = "0" * 64
    receipt.write_text(json.dumps(tampered), encoding="utf-8")
    code, out, _ = _run(args, capsys)
    assert code == codes.TOOL_ERROR and _json(out)["valid"] is False


# --- policy 서브커맨드와 관리자 게이트 ---

def test_policy_read_commands_work_without_admin_mode(capsys, monkeypatch):
    monkeypatch.delenv("SOOTOOL_ADMIN_MODE", raising=False)
    code, out, _ = _run(["policy", "show", "--arg", "domain=tax", "--arg", "name=kr_income", "--arg", "year=2026",
                         "--format", "raw"], capsys)
    assert code == codes.OK and _json(out)["policy_version"]["status"] == "enacted"
    code, out, _ = _run(["policy", "list", "--format", "raw"], capsys)
    assert code == codes.OK and _json(out)["policies"]


@pytest.mark.parametrize("action", ["propose", "activate", "rollback", "import"])
def test_policy_write_commands_are_denied_without_admin_mode(capsys, monkeypatch, action):
    monkeypatch.delenv("SOOTOOL_ADMIN_MODE", raising=False)
    code, _, err = _run(["policy", action, "--arg-json", "{}"], capsys)
    assert code == codes.ADMIN_DENIED
    assert _json(err)["error"]["code"] == "admin_required"


def test_policy_write_commands_run_in_admin_mode(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))
    code, out, _ = _run(["policy", "rollback", "--arg", "domain=tax", "--arg", "name=kr_income", "--arg", "year=2026",
                         "--format", "raw"], capsys)
    assert code == codes.OK and _json(out)["rolled_back"] is False


def test_call_of_a_write_tool_is_gated_too(capsys, monkeypatch):
    monkeypatch.delenv("SOOTOOL_ADMIN_MODE", raising=False)
    code, _, err = _run(["call", "sootool.policy_activate", "--arg", "draft_id=x"], capsys)
    assert code == codes.ADMIN_DENIED


# --- 진입점 ---

def test_subcommand_names_do_not_collide_with_server_flags():
    assert all(not name.startswith("-") for name in SUBCOMMANDS)


def test_module_entry_point_dispatches_subcommands_and_keeps_server_flags():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "sootool", "call", "core.add", "--arg", "operands=[1,2]", "--format", "raw"],
        capture_output=True, text=True, timeout=120, cwd=root, check=False,
    )
    assert result.returncode == 0 and _json(result.stdout) == {"result": "3"}
    server_help = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "sootool", "serve", "--help"],
        capture_output=True, text=True, timeout=120, cwd=root, check=False,
    )
    assert server_help.returncode == 0 and "--transport" in server_help.stdout


def test_stdout_carries_only_the_result(capsys):
    code, out, err = _run(["call", "core.add", "--arg", "operands=[1,2]", "--format", "raw"], capsys)
    assert err == "" and _json(out)
