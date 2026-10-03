from __future__ import annotations

import pytest

from sootool.__main__ import _build_parser, _resolve_profile


def _args(*argv: str):
    return _build_parser().parse_args(list(argv))


def test_profile_defaults_to_full(monkeypatch):
    monkeypatch.delenv("SOOTOOL_PROFILE", raising=False)
    assert _resolve_profile(_args()) == "full"


def test_profile_flag_selects_lean(monkeypatch):
    monkeypatch.delenv("SOOTOOL_PROFILE", raising=False)
    assert _resolve_profile(_args("--profile", "lean")) == "lean"


def test_profile_environment_variable_is_used_without_flag(monkeypatch):
    monkeypatch.setenv("SOOTOOL_PROFILE", "lean")
    assert _resolve_profile(_args()) == "lean"


def test_profile_flag_overrides_environment(monkeypatch):
    monkeypatch.setenv("SOOTOOL_PROFILE", "lean")
    assert _resolve_profile(_args("--profile", "full")) == "full"


def test_unknown_profile_in_environment_exits(monkeypatch):
    monkeypatch.setenv("SOOTOOL_PROFILE", "tiny")
    with pytest.raises(SystemExit):
        _resolve_profile(_args())


def test_unknown_profile_flag_is_rejected_by_parser():
    with pytest.raises(SystemExit):
        _args("--profile", "tiny")
