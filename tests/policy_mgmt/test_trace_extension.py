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
    assert "policy_audit_id" in result


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
