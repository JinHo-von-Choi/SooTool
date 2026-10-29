"""Tests for policy_source/policy_audit_id trace extension on tax.kr_income.

Author: 최진호
Date: 2026-04-23
"""
from __future__ import annotations

from sootool.policy_mgmt import loader


def test_kr_income_trace_has_policy_source_package():
    """tax.kr_income response must include policy_source when loaded from package."""
    loader.invalidate_cache()
    from sootool.modules.tax.kr_income import tax_kr_income

    result = tax_kr_income(taxable_income="50000000", year=2026)
    assert "policy_source" in result
    assert result["policy_source"] == "package"
    assert "policy_sha256" in result
    assert "policy_effective_date" in result
    # 패키지 기본 정책은 사용자가 바꾼 적이 없으므로 감사 id가 없다(None).
    # 키의 존재만 확인하면 값이 항상 None이어도 통과하므로 값을 함께 확인한다.
    assert "policy_audit_id" in result
    assert result["policy_audit_id"] is None


def test_kr_income_trace_field_in_trace_dict():
    """policy_source must also appear inside the trace dict."""
    loader.invalidate_cache()
    from sootool.modules.tax.kr_income import tax_kr_income

    result = tax_kr_income(taxable_income="50000000", year=2026)
    trace = result.get("trace", {})
    assert "policy_source" in trace
    assert trace["policy_source"] == "package"


def test_kr_income_override_policy_source(tmp_path, monkeypatch):
    """When an override is present, policy_source == 'override' and hint is injected."""
    import hashlib
    import re
    import textwrap

    override_dir = tmp_path / "policies" / "tax"
    override_dir.mkdir(parents=True)

    body = textwrap.dedent("""\
        sha256: "PLACEHOLDER"
        effective_date: "2026-01-01"
        notice_no: "override-test"
        source_url: "https://override.example.com"
        data:
          brackets:
            - upper: 14000000
              rate: 0.06
            - upper: null
              rate: 0.15
    """)
    stripped = re.sub(r"^sha256:.*\n", "", body, flags=re.MULTILINE)
    real_hash = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
    yaml_content = body.replace("PLACEHOLDER", real_hash)
    (override_dir / "kr_income_2026.yaml").write_text(yaml_content, encoding="utf-8")

    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))
    loader.invalidate_cache()

    from sootool.modules.tax.kr_income import tax_kr_income

    result = tax_kr_income(taxable_income="50000000", year=2026)
    assert result["policy_source"] == "override"

    # Check _meta.hints contains override hint
    meta = result.get("_meta", {})
    hints = meta.get("hints", [])
    signals = {h["signal"] for h in hints}
    assert "override_policy_in_use" in signals

    loader.invalidate_cache()


def test_policy_audit_id_matches_audit_log(tmp_path, monkeypatch):
    """ADR-016: 덮어쓰기 정책을 activate 한 감사 id가 계산 결과 trace로 전파되어야 한다.

    2026-10-30 감사에서 ``_resolve_audit_id`` 가 항상 None 을 돌려주어 전파가 끊겨 있었고,
    기존 테스트는 키의 존재만 확인해 그 결함을 통과시키고 있었다. 여기서는 activate 응답의
    audit_id 와 감사 로그 항목, 계산 결과의 policy_audit_id 가 모두 같은지 확인한다.
    """
    import hashlib
    import json
    import re
    import textwrap

    monkeypatch.setenv("SOOTOOL_ADMIN_MODE", "1")
    monkeypatch.setenv("SOOTOOL_POLICY_DIR", str(tmp_path / "policies"))
    monkeypatch.setenv("SOOTOOL_STATE_DIR", str(tmp_path / "state"))

    body = textwrap.dedent("""\
        sha256: "PLACEHOLDER"
        effective_date: "2026-01-01"
        notice_no: "audit-id-test"
        source_url: "https://override.example.com"
        data:
          brackets:
            - upper: 14000000
              rate: 0.06
            - upper: null
              rate: 0.15
    """)
    stripped = re.sub(r"^sha256:.*\n", "", body, flags=re.MULTILINE)
    real_hash = hashlib.sha256(stripped.encode("utf-8")).hexdigest()
    yaml_content = body.replace("PLACEHOLDER", real_hash)

    from sootool.server import _load_modules
    _load_modules()
    from sootool.core.registry import REGISTRY

    loader.invalidate_cache()

    proposed = REGISTRY.invoke(
        "sootool.policy_propose",
        domain="tax",
        name="kr_income",
        year=2026,
        yaml_content=yaml_content,
    )
    assert "error" not in proposed, proposed

    activated = REGISTRY.invoke(
        "sootool.policy_activate",
        draft_id=proposed["draft_id"],
    )
    assert "error" not in activated, activated
    audit_id = activated["audit_id"]
    assert audit_id

    loader.invalidate_cache()
    result = REGISTRY.invoke("tax.kr_income", taxable_income="50000000", year=2026)

    assert result["policy_source"] == "override"
    assert result["policy_audit_id"] == audit_id
    assert result["trace"]["policy_audit_id"] == audit_id

    # 감사 로그의 마지막 activate 항목과도 일치해야 한다.
    log_path = tmp_path / "state" / "policy_audit.jsonl"
    entries = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    last_activate = [e for e in entries if e.get("action") == "activate"][-1]
    assert last_activate["audit_id"] == audit_id

    loader.invalidate_cache()


def test_realestate_acquisition_tax_trace_extension():
    """realestate.kr_acquisition_tax should also expose policy_source."""
    loader.invalidate_cache()
    from sootool.modules.realestate.acquisition_tax import realestate_kr_acquisition_tax

    result = realestate_kr_acquisition_tax(
        price="500000000",
        house_count=1,
        is_regulated=False,
        area_m2="80",
        year=2026,
    )
    assert "policy_source" in result
    assert result["policy_source"] == "package"
