"""Playbook definitions for skill_guide — complex multi-step recipes."""
from __future__ import annotations

from typing import Any

_PLAYBOOKS_KO: list[dict[str, Any]] = [
    {
        "id": "payroll_to_net",
        "scenario": "월급 → 연봉 → 소득세 → 실수령액",
        "steps": [
            {"id": "annual", "tool": "core.mul", "args": {"operands": ["<월급>", "12"]}},
            {"id": "tax", "tool": "tax.kr_income", "args": {"taxable_income": "${annual.result}", "year": "<연도>"}},
            {"id": "net", "tool": "core.sub", "args": {"a": "${annual.result}", "b": "${tax.tax}"}},
            {"id": "monthly_net", "tool": "core.div", "args": {"a": "${net.result}", "b": "12"}},
        ],
        "expected_output": {"monthly_net": "실수령 월급", "annual_tax": "연간 소득세"},
        "caveats": [
            "4대보험 공제는 별도 계산 필요",
            "year 인자는 실제 과세 연도 명시 필수",
        ],
    },
    {
        "id": "vat_batch_summary",
        "scenario": "거래명세서 N건 → 부가세 분리 후 합계",
        "steps": [
            {"id": "vat_items", "tool": "core.batch", "args": {"items": [{"id": "item_<i>", "tool": "accounting.vat_extract", "args": {"vat_inclusive": "<금액>", "rate": "0.1"}}]}},
            {"id": "total_supply", "tool": "core.add", "args": {"operands": ["${vat_items.results[*].output.supply}"]}},
            {"id": "total_vat", "tool": "core.add", "args": {"operands": ["${vat_items.results[*].output.vat}"]}},
        ],
        "expected_output": {"total_supply": "공급가액 합계", "total_vat": "부가세 합계"},
        "caveats": [
            "각 건의 vat는 DOWN 반올림 적용됨",
            "합계 시 반올림 누적 오차 최소화를 위해 개별 추출 후 합산 권장",
        ],
    },
    {
        "id": "loan_compare_3",
        "scenario": "대출 3안 비교 (이자율 다름)",
        "steps": [
            {"id": "loans", "tool": "core.batch", "args": {
                "items": [
                    {"id": "loan_a", "tool": "finance.loan_schedule", "args": {"principal": "<원금>", "annual_rate": "<이자율A>", "months": "<기간>"}},
                    {"id": "loan_b", "tool": "finance.loan_schedule", "args": {"principal": "<원금>", "annual_rate": "<이자율B>", "months": "<기간>"}},
                    {"id": "loan_c", "tool": "finance.loan_schedule", "args": {"principal": "<원금>", "annual_rate": "<이자율C>", "months": "<기간>"}},
                ]
            }},
        ],
        "expected_output": {"results": "3개 대출 스케줄 (총이자, 월납입금 비교)"},
        "caveats": ["원리금균등 방식 기준", "중도상환 수수료는 별도 계산 필요"],
    },
    {
        "id": "npv_sensitivity",
        "scenario": "할인율 민감도 (9개 지점)",
        "steps": [
            {"id": "npvs", "tool": "core.batch", "args": {
                "items": [
                    {"id": "npv_<r>", "tool": "finance.npv", "args": {"rate": "<r>", "cashflows": "<현금흐름>"}}
                    for r in ["0.05", "0.06", "0.07", "0.08", "0.09", "0.10", "0.11", "0.12", "0.13"]
                ]
            }},
        ],
        "expected_output": {"results": "할인율별 NPV 9개"},
        "caveats": ["cashflows는 현재 시점을 0번 인덱스로 (보통 음수 투자액)"],
    },
    {
        "id": "bond_yield_duration",
        "scenario": "채권 YTM + Modified Duration 동시 계산",
        "steps": [
            {"id": "bond_calcs", "tool": "core.batch", "args": {
                "items": [
                    {"id": "ytm", "tool": "finance.bond_ytm", "args": {"face": "<액면가>", "price": "<시장가>", "coupon_rate": "<쿠폰율>", "periods": "<기간>", "freq": "<이자지급횟수>"}},
                    {"id": "dur", "tool": "finance.bond_duration", "args": {"face": "<액면가>", "price": "<시장가>", "coupon_rate": "<쿠폰율>", "periods": "<기간>", "freq": "<이자지급횟수>"}},
                ]
            }},
        ],
        "expected_output": {"ytm": "수익률", "macaulay_duration": "맥컬리 듀레이션", "modified_duration": "수정 듀레이션"},
        "caveats": ["Macaulay와 Modified Duration 모두 반환됨", "YTM은 시장가 기준 수익률"],
    },
    {
        "id": "ab_test_full",
        "scenario": "A/B 테스트 전체 (t-검정 + 신뢰구간 + 효과 크기)",
        "steps": [
            {"id": "ttest", "tool": "stats.ttest_two_sample", "args": {"group_a": "<A그룹 데이터>", "group_b": "<B그룹 데이터>"}},
            {"id": "ci_a", "tool": "stats.ci_mean", "args": {"data": "<A그룹 데이터>", "confidence": "0.95"}},
            {"id": "ci_b", "tool": "stats.ci_mean", "args": {"data": "<B그룹 데이터>", "confidence": "0.95"}},
        ],
        "expected_output": {"p_value": "유의확률", "ci_a": "A 신뢰구간", "ci_b": "B 신뢰구간"},
        "caveats": ["p < 0.05 기준 유의성 판단", "효과 크기(Cohen's d) 별도 계산 필요 시 descriptive stats 활용"],
    },
    {
        "id": "policy_annual_update",
        "scenario": "연간 세법 개정 → policy_propose → policy_activate 로 정책 YAML 갱신",
        "title": "연간 세법 개정 정책 업데이트",
        "description": "고시문 확인 후 policy_propose → policy_activate 워크플로우로 정책 YAML을 갱신한다.",
        "steps": [
            {"id": "validate", "tool": "sootool.policy_validate", "args": {"domain": "<도메인>", "name": "<정책명>", "year": "<연도>", "yaml_content": "<새 YAML>"}},
            {"id": "propose",  "tool": "sootool.policy_propose",  "args": {"domain": "<도메인>", "name": "<정책명>", "year": "<연도>", "yaml_content": "<새 YAML>"}},
            {"id": "activate", "tool": "sootool.policy_activate",  "args": {"draft_id": "<propose 응답의 draft_id>"}},
        ],
        "expected_output": {"source": "override", "audit_id": "aud-..."},
        "caveats": ["SOOTOOL_ADMIN_MODE=1 필요", "SHA256 불일치 시 auto_fix_sha256=true 옵션 활용"],
    },
    {
        "id": "policy_hotfix_rollback",
        "scenario": "오적용된 override 정책 즉시 롤백 → 패키지 기본값 복원",
        "title": "긴급 롤백 — 오적용된 정책 원상 복구",
        "description": "잘못 활성화된 override 정책을 즉시 롤백하여 패키지 기본값으로 복원한다.",
        "steps": [
            {"id": "history",  "tool": "sootool.policy_history",  "args": {"domain": "<도메인>", "name": "<정책명>"}},
            {"id": "rollback", "tool": "sootool.policy_rollback",  "args": {"domain": "<도메인>", "name": "<정책명>", "year": "<연도>"}},
        ],
        "expected_output": {"rolled_back": True, "source_now": "package"},
        "caveats": ["SOOTOOL_ADMIN_MODE=1 필요", "감사 로그에 rollback 항목 기록됨"],
    },
    {
        "id": "policy_portability",
        "scenario": "정책 번들 export → import 로 환경 간 이식",
        "title": "정책 번들 내보내기/가져오기 (환경 이전)",
        "description": "policy_export로 서명된 번들을 생성하고 policy_import로 다른 환경에 이식한다.",
        "steps": [
            {"id": "export", "tool": "sootool.policy_export", "args": {"domain": "<도메인>", "name": "<정책명>", "year": "<연도>"}},
            {"id": "import", "tool": "sootool.policy_import", "args": {"bundle": "<export 응답의 bundle>"}},
        ],
        "expected_output": {"imported": True, "source": "override"},
        "caveats": ["SOOTOOL_ADMIN_MODE=1 필요", "서명 검증 활성화 시 require_signature=true"],
    },
]

_PLAYBOOKS_EN: list[dict[str, Any]] = [
    {
        "id": "payroll_to_net",
        "scenario": "Monthly salary -> annual -> income tax -> net pay",
        "steps": [
            {"id": "annual", "tool": "core.mul", "args": {"operands": ["<monthly>", "12"]}},
            {"id": "tax", "tool": "tax.kr_income", "args": {"taxable_income": "${annual.result}", "year": "<year>"}},
            {"id": "net", "tool": "core.sub", "args": {"a": "${annual.result}", "b": "${tax.tax}"}},
            {"id": "monthly_net", "tool": "core.div", "args": {"a": "${net.result}", "b": "12"}},
        ],
        "expected_output": {"monthly_net": "net monthly pay", "annual_tax": "annual income tax"},
        "caveats": [
            "Social insurance deductions require separate calculation",
            "Specify the actual tax year for the year argument",
        ],
    },
    {
        "id": "vat_batch_summary",
        "scenario": "N invoice lines -> separate VAT -> totals",
        "steps": [
            {"id": "vat_items", "tool": "core.batch", "args": {"items": [{"id": "item_<i>", "tool": "accounting.vat_extract", "args": {"vat_inclusive": "<amount>", "rate": "0.1"}}]}},
            {"id": "total_supply", "tool": "core.add", "args": {"operands": ["${vat_items.results[*].output.supply}"]}},
            {"id": "total_vat", "tool": "core.add", "args": {"operands": ["${vat_items.results[*].output.vat}"]}},
        ],
        "expected_output": {"total_supply": "total supply amount", "total_vat": "total VAT"},
        "caveats": [
            "Each line VAT uses DOWN rounding",
            "Extract per-line then sum to minimize rounding accumulation",
        ],
    },
    {
        "id": "loan_compare_3",
        "scenario": "Compare 3 loan options with different rates",
        "steps": [
            {"id": "loans", "tool": "core.batch", "args": {
                "items": [
                    {"id": "loan_a", "tool": "finance.loan_schedule", "args": {"principal": "<principal>", "annual_rate": "<rate_a>", "months": "<term>"}},
                    {"id": "loan_b", "tool": "finance.loan_schedule", "args": {"principal": "<principal>", "annual_rate": "<rate_b>", "months": "<term>"}},
                    {"id": "loan_c", "tool": "finance.loan_schedule", "args": {"principal": "<principal>", "annual_rate": "<rate_c>", "months": "<term>"}},
                ]
            }},
        ],
        "expected_output": {"results": "3 loan schedules (total interest, monthly payment comparison)"},
        "caveats": ["Equal principal+interest method", "Prepayment penalties calculated separately"],
    },
    {
        "id": "npv_sensitivity",
        "scenario": "NPV sensitivity over 9 discount rates",
        "steps": [
            {"id": "npvs", "tool": "core.batch", "args": {
                "items": [
                    {"id": "npv_<r>", "tool": "finance.npv", "args": {"rate": "<r>", "cashflows": "<cashflows>"}}
                    for r in ["0.05", "0.06", "0.07", "0.08", "0.09", "0.10", "0.11", "0.12", "0.13"]
                ]
            }},
        ],
        "expected_output": {"results": "NPV at 9 discount rates"},
        "caveats": ["cashflows[0] is the current period (typically negative investment)"],
    },
    {
        "id": "bond_yield_duration",
        "scenario": "Bond YTM + Modified Duration simultaneously",
        "steps": [
            {"id": "bond_calcs", "tool": "core.batch", "args": {
                "items": [
                    {"id": "ytm", "tool": "finance.bond_ytm", "args": {"face": "<face>", "price": "<price>", "coupon_rate": "<coupon>", "periods": "<n>", "freq": "<freq>"}},
                    {"id": "dur", "tool": "finance.bond_duration", "args": {"face": "<face>", "price": "<price>", "coupon_rate": "<coupon>", "periods": "<n>", "freq": "<freq>"}},
                ]
            }},
        ],
        "expected_output": {"ytm": "yield to maturity", "macaulay_duration": "Macaulay duration", "modified_duration": "Modified duration"},
        "caveats": ["Both Macaulay and Modified Duration returned", "YTM is yield based on market price"],
    },
    {
        "id": "ab_test_full",
        "scenario": "Full A/B test: t-test + confidence interval + effect size",
        "steps": [
            {"id": "ttest", "tool": "stats.ttest_two_sample", "args": {"group_a": "<data_a>", "group_b": "<data_b>"}},
            {"id": "ci_a", "tool": "stats.ci_mean", "args": {"data": "<data_a>", "confidence": "0.95"}},
            {"id": "ci_b", "tool": "stats.ci_mean", "args": {"data": "<data_b>", "confidence": "0.95"}},
        ],
        "expected_output": {"p_value": "significance probability", "ci_a": "CI for A", "ci_b": "CI for B"},
        "caveats": ["Significance threshold p < 0.05", "Use descriptive stats for Cohen's d effect size"],
    },
    {
        "id": "policy_annual_update",
        "scenario": "Annual tax law update -> policy_propose -> policy_activate to refresh YAML",
        "title": "Annual Tax Law Policy Update",
        "description": "After reviewing official notices, update a policy YAML via policy_propose → policy_activate workflow.",
        "steps": [
            {"id": "validate", "tool": "sootool.policy_validate", "args": {"domain": "<domain>", "name": "<policy>", "year": "<year>", "yaml_content": "<new YAML>"}},
            {"id": "propose",  "tool": "sootool.policy_propose",  "args": {"domain": "<domain>", "name": "<policy>", "year": "<year>", "yaml_content": "<new YAML>"}},
            {"id": "activate", "tool": "sootool.policy_activate",  "args": {"draft_id": "<draft_id from propose>"}},
        ],
        "expected_output": {"source": "override", "audit_id": "aud-..."},
        "caveats": ["Requires SOOTOOL_ADMIN_MODE=1", "Use auto_fix_sha256=true if SHA256 mismatch"],
    },
    {
        "id": "policy_hotfix_rollback",
        "scenario": "Revert misapplied override policy -> restore package default",
        "title": "Emergency Rollback — Revert Misapplied Policy",
        "description": "Immediately roll back a wrongly activated override policy to restore the package default.",
        "steps": [
            {"id": "history",  "tool": "sootool.policy_history",  "args": {"domain": "<domain>", "name": "<policy>"}},
            {"id": "rollback", "tool": "sootool.policy_rollback",  "args": {"domain": "<domain>", "name": "<policy>", "year": "<year>"}},
        ],
        "expected_output": {"rolled_back": True, "source_now": "package"},
        "caveats": ["Requires SOOTOOL_ADMIN_MODE=1", "Audit log records rollback entry"],
    },
    {
        "id": "policy_portability",
        "scenario": "policy_export signed bundle -> policy_import in another environment",
        "title": "Policy Bundle Export/Import (Environment Migration)",
        "description": "Export a signed bundle with policy_export and import it into another environment with policy_import.",
        "steps": [
            {"id": "export", "tool": "sootool.policy_export", "args": {"domain": "<domain>", "name": "<policy>", "year": "<year>"}},
            {"id": "import", "tool": "sootool.policy_import", "args": {"bundle": "<bundle from export>"}},
        ],
        "expected_output": {"imported": True, "source": "override"},
        "caveats": ["Requires SOOTOOL_ADMIN_MODE=1", "Enable signature verification with require_signature=true"],
    },
]


def get_playbooks(locale: str = "ko") -> list[dict[str, Any]]:
    """Return playbook definitions for the given locale."""
    if locale == "en":
        return _PLAYBOOKS_EN
    return _PLAYBOOKS_KO
