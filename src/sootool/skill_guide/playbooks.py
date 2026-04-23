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
    {
        "id": "lunar_holiday_planner",
        "scenario": "음력 명절 양력 환산 + 주변 공휴일·영업일 산정",
        "title": "음력 명절 캘린더 (설/추석 + 영업일)",
        "description": "설날·추석의 양력 날짜를 계산하고 전후 영업일 3일을 함께 반환한다.",
        "steps": [
            {"id": "seollal",  "tool": "datetime.lunar_holiday", "args": {"name": "seollal", "year": "<연도>"}},
            {"id": "chuseok",  "tool": "datetime.lunar_holiday", "args": {"name": "chuseok", "year": "<연도>"}},
            {"id": "preholiday", "tool": "datetime.add_business_days", "args": {"start_date": "${chuseok.solar_date}", "days": "-3", "country": "KR"}},
        ],
        "expected_output": {"seollal": "설날 양력 ISO", "chuseok": "추석 양력 ISO", "preholiday": "추석 3영업일 전"},
        "caveats": ["음력 연도 지원 범위 2020-2030", "country=KR 공휴일 포함"],
    },
    {
        "id": "medical_dose_with_qtc",
        "scenario": "체중 기반 용량 + QT 보정 (약물 안전 체크)",
        "title": "약물 용량 + QT 보정 동시 평가",
        "description": "체중 기반 용량 계산 후 동일 환자의 QTc(Bazett) 와 CHA2DS2-VASc 점수를 묶어 반환한다.",
        "steps": [
            {"id": "dose", "tool": "medical.dose_weight_based", "args": {"weight_kg": "<체중>", "dose_per_kg": "<mg/kg>", "max_dose": "<상한>"}},
            {"id": "qtc",  "tool": "medical.qtc_bazett",         "args": {"qt": "<QT ms>", "rr": "<RR ms>"}},
            {"id": "cha",  "tool": "medical.cha2ds2_vasc",        "args": {"age": "<나이>", "female": "<bool>", "hypertension": "<bool>", "diabetes": "<bool>", "stroke_or_tia": "<bool>"}},
        ],
        "expected_output": {"dose": "계산 용량", "qtc": "보정 QTc ms", "cha": "CHA2DS2-VASc 점수"},
        "caveats": ["QT/RR 단위 일치 필수 (기본 ms)", "CHA 점수 ≥2 이면 항응고 고려 — 임상 판단 필요"],
    },
    {
        "id": "math_integration_npv",
        "scenario": "연속 현금흐름 수치 적분 → NPV 검증",
        "title": "NPV 검증 (이산 vs 수치 적분)",
        "description": "연속 현금흐름 f(t) 를 심프슨 법칙으로 적분하고 finance.npv 의 이산 합산 결과와 비교한다.",
        "steps": [
            {"id": "integral", "tool": "math.integrate_simpson", "args": {"expression": "<f(t) 표현식>", "a": "0", "b": "<T>", "n": "200", "variable": "t"}},
            {"id": "npv",      "tool": "finance.npv",            "args": {"rate": "<할인율>", "cashflows": "<샘플링된 현금흐름 리스트>"}},
        ],
        "expected_output": {"integral": "연속 적분 현재가치", "npv": "이산 NPV"},
        "caveats": ["expression은 core.calc 화이트리스트만 사용", "n은 짝수, 수렴 전 이산 샘플 수 증가 필요"],
    },
    {
        "id": "payroll_full_net",
        "scenario": "월급 + 식대 → 4대보험·소득세 전체 공제 → 실수령액",
        "title": "실수령액 한 번에 (payroll.kr_salary 단일 호출)",
        "description": "tax+core 수동 조합 대신 payroll.kr_salary 한 도구로 4대보험·간이 소득세를 일괄 공제하고 trace 를 보존한다.",
        "steps": [
            {"id": "salary", "tool": "payroll.kr_salary", "args": {"monthly_salary": "<월급>", "year": "<연도>", "meal_allowance": "<식대>"}},
        ],
        "expected_output": {"gross": "세전", "net": "실수령", "insurances": "4대보험 내역", "taxes": "소득세·지방세"},
        "caveats": [
            "meal_allowance 는 월 200,000 한도까지만 비과세",
            "연도별 정책 YAML 경로: policies/payroll/kr_4insurance_<year>.yaml",
        ],
    },
    {
        "id": "engineering_electrical_audit",
        "scenario": "전압·전류·저항·전력 감사 (옴·전력·병렬저항 교차 확인)",
        "title": "전기 회로 파라미터 동시 검증",
        "description": "engineering.electrical_ohm, electrical_power, resistor_parallel 을 core.batch 로 묶어 한 번에 감사한다.",
        "steps": [
            {"id": "bench", "tool": "core.batch", "args": {
                "items": [
                    {"id": "ohm",    "tool": "engineering.electrical_ohm",    "args": {"voltage": "<V>", "resistance": "<R>"}},
                    {"id": "power",  "tool": "engineering.electrical_power",  "args": {"voltage": "<V>", "resistance": "<R>"}},
                    {"id": "rpar",   "tool": "engineering.resistor_parallel", "args": {"resistances": ["<R1>", "<R2>", "<R3>"]}},
                ]
            }},
        ],
        "expected_output": {"ohm": "I=V/R", "power": "P=V^2/R", "rpar": "R_eq"},
        "caveats": ["저항 단위 Ω 일치", "병렬저항 3개 이상 시 resistances 배열에 모두 나열"],
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
    {
        "id": "lunar_holiday_planner",
        "scenario": "Lunar holiday -> solar date + surrounding business days",
        "title": "Lunar holiday calendar (Seollal/Chuseok + business days)",
        "description": "Compute solar dates for Seollal and Chuseok and derive business days ±3 around them.",
        "steps": [
            {"id": "seollal",    "tool": "datetime.lunar_holiday",      "args": {"name": "seollal", "year": "<year>"}},
            {"id": "chuseok",    "tool": "datetime.lunar_holiday",      "args": {"name": "chuseok", "year": "<year>"}},
            {"id": "preholiday", "tool": "datetime.add_business_days",  "args": {"start_date": "${chuseok.solar_date}", "days": "-3", "country": "KR"}},
        ],
        "expected_output": {"seollal": "Seollal solar ISO", "chuseok": "Chuseok solar ISO", "preholiday": "3 business days before"},
        "caveats": ["Lunar year range 2020-2030", "country=KR holidays considered"],
    },
    {
        "id": "medical_dose_with_qtc",
        "scenario": "Weight-based dose + QT correction + stroke risk",
        "title": "Drug dose + QT correction safety panel",
        "description": "Compute weight-based dose then evaluate QTc (Bazett) and CHA2DS2-VASc score for the same patient.",
        "steps": [
            {"id": "dose", "tool": "medical.dose_weight_based", "args": {"weight_kg": "<kg>", "dose_per_kg": "<mg/kg>", "max_dose": "<ceiling>"}},
            {"id": "qtc",  "tool": "medical.qtc_bazett",         "args": {"qt": "<QT ms>", "rr": "<RR ms>"}},
            {"id": "cha",  "tool": "medical.cha2ds2_vasc",        "args": {"age": "<age>", "female": "<bool>", "hypertension": "<bool>", "diabetes": "<bool>", "stroke_or_tia": "<bool>"}},
        ],
        "expected_output": {"dose": "dose", "qtc": "corrected QTc ms", "cha": "CHA2DS2-VASc score"},
        "caveats": ["QT/RR units must match (ms by default)", "CHA ≥2 → consider anticoagulation, use clinical judgement"],
    },
    {
        "id": "math_integration_npv",
        "scenario": "Continuous cash flow integration cross-checked with discrete NPV",
        "title": "NPV validation (discrete vs continuous)",
        "description": "Integrate continuous cash flow f(t) via Simpson's rule and compare against discrete finance.npv.",
        "steps": [
            {"id": "integral", "tool": "math.integrate_simpson", "args": {"expression": "<f(t) expression>", "a": "0", "b": "<T>", "n": "200", "variable": "t"}},
            {"id": "npv",      "tool": "finance.npv",            "args": {"rate": "<rate>", "cashflows": "<sampled cash flows>"}},
        ],
        "expected_output": {"integral": "continuous PV", "npv": "discrete NPV"},
        "caveats": ["expression limited to core.calc whitelist", "n even, increase sampling for convergence"],
    },
    {
        "id": "payroll_full_net",
        "scenario": "Gross salary + meal allowance -> all 4 insurances + income tax -> net pay",
        "title": "One-shot net pay via payroll.kr_salary",
        "description": "Instead of manually chaining tax + core tools, delegate all deductions (4 insurances + simplified income tax) to payroll.kr_salary.",
        "steps": [
            {"id": "salary", "tool": "payroll.kr_salary", "args": {"monthly_salary": "<gross>", "year": "<year>", "meal_allowance": "<meal>"}},
        ],
        "expected_output": {"gross": "pre-tax", "net": "take-home", "insurances": "4-insurance breakdown", "taxes": "income + local"},
        "caveats": [
            "meal_allowance is tax-free only up to 200,000 KRW/month",
            "Per-year YAML: policies/payroll/kr_4insurance_<year>.yaml",
        ],
    },
    {
        "id": "engineering_electrical_audit",
        "scenario": "Simultaneous audit of V/I/R/P with parallel-resistor cross-check",
        "title": "Electrical circuit parameter audit",
        "description": "Bundle engineering.electrical_ohm, electrical_power, and resistor_parallel into a single core.batch for a deterministic audit.",
        "steps": [
            {"id": "bench", "tool": "core.batch", "args": {
                "items": [
                    {"id": "ohm",   "tool": "engineering.electrical_ohm",    "args": {"voltage": "<V>", "resistance": "<R>"}},
                    {"id": "power", "tool": "engineering.electrical_power",  "args": {"voltage": "<V>", "resistance": "<R>"}},
                    {"id": "rpar",  "tool": "engineering.resistor_parallel", "args": {"resistances": ["<R1>", "<R2>", "<R3>"]}},
                ]
            }},
        ],
        "expected_output": {"ohm": "I=V/R", "power": "P=V^2/R", "rpar": "R_eq"},
        "caveats": ["Keep resistance units in ohms", "List all resistors in the resistances array"],
    },
]


def get_playbooks(locale: str = "ko") -> list[dict[str, Any]]:
    """Return playbook definitions for the given locale."""
    if locale == "en":
        return _PLAYBOOKS_EN
    return _PLAYBOOKS_KO
