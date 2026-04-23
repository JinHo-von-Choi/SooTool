"""Tests for sootool.skill_guide tool."""
from __future__ import annotations

import pytest

from sootool.skill_guide.guide import skill_guide

GUIDE_VERSION = "1.0.0"


class TestSkillGuideSection:
    def test_all_sections_present(self) -> None:
        result = skill_guide(section="all")
        assert "triggers" in result
        assert "examples" in result
        assert "anti_patterns" in result
        assert "playbooks" in result
        assert result["version"] == GUIDE_VERSION
        assert result["locale"] in ("ko", "en")

    def test_triggers_only(self) -> None:
        result = skill_guide(section="triggers")
        assert "triggers" in result
        assert "examples" not in result
        assert "anti_patterns" not in result
        assert "playbooks" not in result

    def test_examples_only(self) -> None:
        result = skill_guide(section="examples")
        assert "examples" in result
        assert "triggers" not in result

    def test_anti_patterns_only(self) -> None:
        result = skill_guide(section="anti_patterns")
        assert "anti_patterns" in result
        assert "triggers" not in result

    def test_playbooks_only(self) -> None:
        result = skill_guide(section="playbooks")
        assert "playbooks" in result
        assert "triggers" not in result

    def test_invalid_section_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid section"):
            skill_guide(section="bogus")

    def test_version_field(self) -> None:
        result = skill_guide()
        assert result["version"] == GUIDE_VERSION

    def test_locale_field_ko(self) -> None:
        result = skill_guide(lang="ko")
        assert result["locale"] == "ko"

    def test_locale_field_en(self) -> None:
        result = skill_guide(section="triggers", lang="en")
        assert result["locale"] == "en"


class TestTriggersContent:
    def test_trigger_count(self) -> None:
        result = skill_guide(section="triggers")
        # Phase 1 base 15 + M8 policy management 2 + Phase 4 Tier B/C 8 = 25
        assert len(result["triggers"]) == 25

    def test_trigger_structure(self) -> None:
        result = skill_guide(section="triggers", lang="ko")
        for t in result["triggers"]:
            assert "signal" in t
            assert "tool" in t
            assert "reason" in t

    def test_triggers_en_different_from_ko(self) -> None:
        ko = skill_guide(section="triggers", lang="ko")
        en = skill_guide(section="triggers", lang="en")
        # English and Korean triggers must differ (different content)
        ko_signals = [t["signal"] for t in ko["triggers"]]
        en_signals = [t["signal"] for t in en["triggers"]]
        assert ko_signals != en_signals


class TestAntiPatternsContent:
    def test_anti_pattern_count(self) -> None:
        result = skill_guide(section="anti_patterns")
        # Plan specifies 6 anti-patterns
        assert len(result["anti_patterns"]) == 6

    def test_anti_pattern_structure(self) -> None:
        result = skill_guide(section="anti_patterns", lang="ko")
        for ap in result["anti_patterns"]:
            assert "pattern" in ap
            assert "why" in ap
            assert "instead" in ap


class TestPlaybooksContent:
    def test_playbook_count(self) -> None:
        result = skill_guide(section="playbooks")
        # Phase 1 base 6 + M8 policy management 3 + Phase 4 Tier B/C 3 = 12
        assert len(result["playbooks"]) == 12

    def test_playbook_structure(self) -> None:
        result = skill_guide(section="playbooks", lang="ko")
        expected_ids = {
            "payroll_to_net", "vat_batch_summary", "loan_compare_3",
            "npv_sensitivity", "bond_yield_duration", "ab_test_full",
            "policy_annual_update", "policy_hotfix_rollback", "policy_portability",
            "lunar_holiday_planner", "medical_dose_with_qtc", "math_integration_npv",
        }
        actual_ids = {pb["id"] for pb in result["playbooks"]}
        assert actual_ids == expected_ids

    def test_playbook_fields(self) -> None:
        result = skill_guide(section="playbooks", lang="ko")
        for pb in result["playbooks"]:
            assert "id" in pb
            assert "scenario" in pb
            assert "steps" in pb
            assert "expected_output" in pb
            assert "caveats" in pb
