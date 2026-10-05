"""``sootool.sdk`` 의 정적 타입 선언. scripts/gen_sdk_stubs.py 가 생성한다. 직접 고치지 않는다.

런타임에는 가져오지 않는다(``sootool.sdk`` 가 TYPE_CHECKING 일 때만 참조한다).
"""
# ruff: noqa
# mypy: ignore-errors
from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal, Protocol

import sootool.core.analysis_tools as _m10
import sootool.core.batch as _m8
import sootool.core.calc.api as _m9
import sootool.core.pipeline as _m11
import sootool.modules.accounting.bookkeeping as _m0
import sootool.modules.accounting.cashflow as _m1
import sootool.modules.accounting.depreciation as _m2
import sootool.modules.accounting.dupont as _m3
import sootool.modules.accounting.income_statement as _m4
import sootool.modules.accounting.ratios as _m5
import sootool.modules.accounting.vat as _m6
import sootool.modules.crypto.advanced as _m12
import sootool.modules.crypto.arithmetic as _m13
import sootool.modules.crypto.hash_ops as _m14
import sootool.modules.crypto.primes as _m15
import sootool.modules.datetime_.age as _m17
import sootool.modules.datetime_.business_days as _m16
import sootool.modules.datetime_.day_count as _m18
import sootool.modules.datetime_.fiscal as _m19
import sootool.modules.datetime_.lunar as _m20
import sootool.modules.datetime_.timezone_ops as _m21
import sootool.modules.engineering.control as _m26
import sootool.modules.engineering.electrical as _m31
import sootool.modules.engineering.electrical_ac.combine as _m27
import sootool.modules.engineering.electrical_ac.impedance as _m22
import sootool.modules.engineering.electrical_ac.power as _m35
import sootool.modules.engineering.electrical_ac.signals as _m29
import sootool.modules.engineering.equivalent_circuit as _m34
import sootool.modules.engineering.fluid as _m25
import sootool.modules.engineering.gear_bearing as _m24
import sootool.modules.engineering.materials as _m33
import sootool.modules.engineering.mechanical as _m30
import sootool.modules.engineering.reliability as _m32
import sootool.modules.engineering.si_prefix as _m36
import sootool.modules.engineering.structural as _m23
import sootool.modules.engineering.thermal as _m28
import sootool.modules.finance.bond as _m38
import sootool.modules.finance.derivatives as _m40
import sootool.modules.finance.loan as _m42
import sootool.modules.finance.metrics as _m39
import sootool.modules.finance.option as _m37
import sootool.modules.finance.risk as _m43
import sootool.modules.finance.tvm as _m41
import sootool.modules.geometry.area as _m44
import sootool.modules.geometry.distance as _m45
import sootool.modules.geometry.matrix_ops as _m46
import sootool.modules.geometry.vector_ops as _m47
import sootool.modules.geometry.volume as _m48
import sootool.modules.math.differentiation as _m49
import sootool.modules.math.fft as _m50
import sootool.modules.math.integration as _m51
import sootool.modules.math.interpolation as _m52
import sootool.modules.math.polynomial as _m53
import sootool.modules.medical.body as _m54
import sootool.modules.medical.dose as _m56
import sootool.modules.medical.egfr as _m57
import sootool.modules.medical.pregnancy as _m58
import sootool.modules.medical.qt_correction as _m59
import sootool.modules.medical.risk_scores as _m55
import sootool.modules.payroll.hourly_to_monthly_net as _m60
import sootool.modules.payroll.kr_bonus_tax as _m61
import sootool.modules.payroll.kr_donation_deduction as _m62
import sootool.modules.payroll.kr_education_deduction as _m63
import sootool.modules.payroll.kr_gross_from_net as _m64
import sootool.modules.payroll.kr_health_income_premium as _m65
import sootool.modules.payroll.kr_housing_loan_deduction as _m66
import sootool.modules.payroll.kr_medical_deduction as _m67
import sootool.modules.payroll.kr_minimum_wage_check as _m68
import sootool.modules.payroll.kr_national_pension_benefit as _m69
import sootool.modules.payroll.kr_overtime_pay as _m70
import sootool.modules.payroll.kr_salary as _m71
import sootool.modules.payroll.kr_severance_pay as _m72
import sootool.modules.payroll.kr_weekly_holiday_pay as _m73
import sootool.modules.payroll.kr_year_end_tax_settlement as _m74
import sootool.modules.pm.cpm as _m75
import sootool.modules.pm.earned_schedule as _m76
import sootool.modules.pm.evm as _m77
import sootool.modules.pm.monte_carlo as _m78
import sootool.modules.pm.pert as _m79
import sootool.modules.probability.bayes as _m80
import sootool.modules.probability.combinatorics as _m83
import sootool.modules.probability.distributions._common as _m81
import sootool.modules.probability.expected as _m82
import sootool.modules.realestate.acquisition_tax as _m84
import sootool.modules.realestate.kr_comprehensive as _m85
import sootool.modules.realestate.kr_local_property as _m87
import sootool.modules.realestate.kr_property_tax as _m88
import sootool.modules.realestate.kr_subscription_score as _m89
import sootool.modules.realestate.ratios as _m86
import sootool.modules.realestate.rental_yield as _m91
import sootool.modules.realestate.transfer_tax as _m90
import sootool.modules.science.chemistry as _m96
import sootool.modules.science.electrochemistry as _m92
import sootool.modules.science.optics as _m93
import sootool.modules.science.physics as _m94
import sootool.modules.science.thermo as _m95
import sootool.modules.stats.anova as _m100
import sootool.modules.stats.bootstrap as _m101
import sootool.modules.stats.ci as _m103
import sootool.modules.stats.descriptive as _m105
import sootool.modules.stats.effect_size as _m104
import sootool.modules.stats.inference as _m102
import sootool.modules.stats.nonparametric as _m106
import sootool.modules.stats.regression as _m107
import sootool.modules.symbolic.diff as _m108
import sootool.modules.symbolic.solve as _m109
import sootool.modules.tax.capital_gains as _m110
import sootool.modules.tax.kr_comprehensive_income_tax as _m111
import sootool.modules.tax.kr_corporate as _m112
import sootool.modules.tax.kr_education_tax_add as _m113
import sootool.modules.tax.kr_eitc as _m114
import sootool.modules.tax.kr_gift as _m115
import sootool.modules.tax.kr_income as _m116
import sootool.modules.tax.kr_inheritance as _m117
import sootool.modules.tax.kr_local_income_tax as _m118
import sootool.modules.tax.kr_pension_income as _m119
import sootool.modules.tax.kr_registration_license_tax as _m120
import sootool.modules.tax.kr_rural_special_tax as _m121
import sootool.modules.tax.kr_securities_transaction as _m122
import sootool.modules.tax.kr_simplified_vat as _m123
import sootool.modules.tax.kr_vehicle_tax as _m124
import sootool.modules.tax.kr_withholding as _m125
import sootool.modules.tax.progressive as _m126
import sootool.modules.tax_us.capital_gains as _m127
import sootool.modules.tax_us.federal_income as _m128
import sootool.modules.tax_us.fica as _m129
import sootool.modules.tax_us.state_tax as _m130
import sootool.modules.units.convert as _m131
import sootool.modules.units.currency as _m133
import sootool.modules.units.extended as _m132
import sootool.modules.units.temperature as _m134
import sootool.policy_mgmt.tool_types as _m97
import sootool.receipt_tools as _m99
import sootool.runtime as _m7
import sootool.skill_guide.guide as _m98

Num = str | int | float | Decimal


class _AccountingTools(Protocol):
    def balance(self, entries: list[dict[str, Any]]) -> _m0.BalanceResult:
        """분개 목록의 차변 합계와 대변 합계가 같은지 검증한다. entries 는 {account, debit, credit} 항목의 목록이며 금액은 Decimal 문자열, 비어 있으면 0 으로 본다. 반환값은 balanced 여부, 두 합계, 차이의 절댓값(diff). account 는 합계에 쓰이지 않으므로 계정별 잔액 검증에는 쓸 수 없다."""
        ...
    def cashflow_operating(self, net_income: Num, depreciation: Num = '0', amortization: Num = '0', other_noncash: Num = '0', change_in_receivables: Num = '0', change_in_inventory: Num = '0', change_in_payables: Num = '0', change_in_other_wc: Num = '0') -> _m1.AccountingCashflowOperatingResult:
        """간접법 영업활동현금흐름(CFO)을 계산한다. 당기순이익에 감가상각비, 무형자산상각비, 기타 비현금 항목을 더하고 매출채권 증가와 재고자산 증가는 빼며 매입채무 증가는 더한다. 금액은 Decimal 문자열이며 반올림하지 않는다. 증가는 양수로 넣어야 하며 증가분을 음수로 넣으면 부호가 뒤집힌다."""
        ...
    def depreciation_declining_balance(self, cost: Num, salvage: Num, rate: Num, life_years: int, decimals: int = 0, rounding: Num = 'HALF_EVEN') -> _m2.DepreciationDecliningBalanceResult:
        """정률법 감가상각 스케줄을 계산한다. 연도별 감가비 = 기초 장부가 x 감가율(rate, 0 초과 1 미만 Decimal 문자열)이며 장부가는 잔존가치 아래로 내려가지 않고 도달하면 이후 연도 감가비는 0 이다. decimals(기본 0)자리로 rounding(기본 HALF_EVEN) 처리한다. 감가율은 입력값 그대로 쓰며 내용연수로 역산하지 않는다."""
        ...
    def depreciation_straight_line(self, cost: Num, salvage: Num, life_years: int, decimals: int = 0, rounding: Num = 'HALF_EVEN') -> _m2.DepreciationStraightLineResult:
        """정액법 감가상각 스케줄을 계산한다. 연 감가비 = (취득원가 - 잔존가치) / 내용연수(life_years, 1 이상 정수), 금액은 Decimal 문자열. decimals(기본 0)자리로 rounding(기본 HALF_EVEN) 처리하고 마지막 해는 장부가가 잔존가치에 맞도록 잔액을 상각한다. 월할이나 기중 취득 안분은 지원하지 않는다."""
        ...
    def depreciation_units_of_production(self, cost: Num, salvage: Num, total_units: int, period_units: list[int], decimals: int = 0, rounding: Num = 'HALF_EVEN') -> _m2.DepreciationUnitsOfProductionResult:
        """생산량비례법 감가상각 스케줄을 계산한다. 기간 감가비 = (취득원가 - 잔존가치) / 총생산량 x 기간 생산량. total_units 는 1 이상 정수, period_units 는 기간별 생산량 정수 목록이며 금액은 Decimal 문자열. decimals(기본 0)자리로 rounding(기본 HALF_EVEN) 처리한다. 누적 생산량이 총생산량을 넘어도 오류 없이 장부가가 잔존가치에서 멈춘다."""
        ...
    def dupont_3(self, net_income: Num, revenue: Num, total_assets: Num, total_equity: Num, decimals: int = 6) -> _m3.AccountingDupont3Result:
        """DuPont 3단계 분해로 ROE = 순이익률 x 총자산회전율 x 자기자본승수(재무레버리지)를 계산한다. 금액은 Decimal 문자열이며 매출, 총자산, 자기자본은 0 이 아니어야 한다. 각 값은 decimals(기본 6)자리 HALF_EVEN 반올림이고 음수 자기자본은 막지 않으므로 부호를 확인해야 한다."""
        ...
    def dupont_5(self, net_income: Num, pretax_income: Num, ebit: Num, revenue: Num, total_assets: Num, total_equity: Num, decimals: int = 6) -> _m3.AccountingDupont5Result:
        """DuPont 5단계 분해로 ROE = 세부담비율(순이익/세전이익) x 이자부담비율(세전이익/EBIT) x 영업이익률 x 총자산회전율 x 재무레버리지를 계산한다. 금액은 Decimal 문자열이며 세전이익, EBIT, 매출, 총자산, 자기자본은 0 이 아니어야 한다. 각 값은 decimals(기본 6)자리 HALF_EVEN 반올림이다."""
        ...
    def income_statement(self, revenue: Num, cost_of_sales: Num, operating_expenses: Num = '0', other_income: Num = '0', other_expenses: Num = '0', interest_expense: Num = '0', tax_expense: Num = '0') -> _m4.AccountingIncomeStatementResult:
        """다단계 손익계산서: 매출에서 매출총이익, 영업이익, 세전이익, 당기순이익까지 단계별 이익과 이익률을 계산한다. 금액은 Decimal 문자열이며 매출과 매출원가는 0 이상이어야 한다. 이익은 반올림하지 않고 이익률은 소수 6자리 (0.25 = 25%)로 반올림하며 매출이 0 이면 0 이다. 비용 항목은 양수로 입력한다."""
        ...
    def ratios(self, current_assets: Num, current_liabilities: Num, inventory: Num, total_assets: Num, total_liabilities: Num, total_equity: Num, net_income: Num, revenue: Num, decimals: int = 4) -> _m5.AccountingRatiosResult:
        """재무상태표와 손익 항목으로 유동비율, 당좌비율, 부채/자기자본, 부채/총자산, 자기자본비율, ROE, ROA, 순이익률 8개를 한 번에 계산한다. 금액은 Decimal 문자열이며 비율은 배수(0.5 = 50%)로 decimals(기본 4)자리 HALF_EVEN 반올림한다. 분모(유동부채, 자기자본, 총자산, 매출)가 0 이면 오류이며 백분율로 쓰려면 직접 100 을 곱한다."""
        ...
    def vat_add(self, net: Num, rate: Num = '0.1', rounding: Num = 'HALF_EVEN') -> _m6.VatAddResult:
        """공급가액에 부가세를 더해 공급대가를 계산한다. 부가세 = 공급가액 x rate(기본 0.1)를 정수 자리로 rounding 처리하며 기본은 HALF_EVEN 으로 vat_extract 의 기본(DOWN)과 다르다. 금액은 Decimal 문자열. 공급대가에서 공급가액을 구하려면 vat_extract 를 쓴다."""
        ...
    def vat_extract(self, gross: Num, rate: Num = '0.1', rounding: Num = 'DOWN') -> _m6.VatExtractResult:
        """공급대가(부가세 포함 금액)에서 공급가액과 부가세를 역산한다. 공급가액 = gross / (1 + rate)를 정수 자리로 rounding(기본 DOWN, 절사) 처리하고 부가세 = gross - 공급가액. rate 기본 0.1, 금액은 Decimal 문자열. 공급가액에서 공급대가를 구하는 순방향 계산에는 vat_add 를 쓴다."""
        ...


class _CoreTools(Protocol):
    def add(self, operands: list[Num], trace_level: Num = 'summary') -> _m7.ArithmeticResult:
        """Decimal 정밀 덧셈. operands(쉼표, 단위, 공백 없는 숫자 문자열 목록)의 합을 result 문자열로 반환한다. 유효숫자 50자리 안에서 계산하고 별도 반올림은 없다. trace_level 은 summary(기본), full, none. 합계를 직접 암산하지 말고 이 도구로 구한다."""
        ...
    def batch(self, items: list[dict[str, Any]], max_workers: int = 16, item_timeout_s: float = 10.0, batch_timeout_s: float = 60.0, deterministic: bool = True) -> _m8.BatchResult:
        """서로 독립인 도구 호출 N개를 병렬 실행한다. items 는 id, tool, args 를 가진 객체 목록(최대 500개, id 중복 불가)이고 읽기 전용 도구만 실행된다. 결과는 입력 id 순서이며 항목별 status(ok, error, timeout)와 item_timeout_s, batch_timeout_s 가 적용된다. 앞 결과를 뒤 입력에 쓰려면 core.pipeline 을 쓴다."""
        ...
    def calc(self, expression: Num, variables: dict[str, Num] | None = None, precision: int = 50, trace_level: Num = 'summary') -> _m9.CalcResult:
        """AST 기반 안전 수식 평가기. expression 은 사칙, %, //, **, 괄호, 함수(sqrt, abs, floor, ceil, round, log, ln, exp, 삼각함수 등), 상수(pi, e, tau)를 쓸 수 있고 variables 는 Decimal 문자열 전용이다. 결과는 precision(기본 50)자리 십진 문자열이다. 비교, 조건식, 속성 접근은 거부한다. 세금, 금융 공식은 전용 도구를 쓴다."""
        ...
    def compare(self, tool: Num, base_arguments: dict[str, Any], scenarios: list[dict[str, Any]], fields: list[Num]) -> _m10.CompareResult:
        """시나리오 비교: 읽기 전용 도구 tool 을 base_arguments 로 실행한 기준안과, 각 시나리오의 arguments 로 덮어쓴 실행을 비교한다. fields 는 결과에서 비교할 필드 경로 목록(예: tax, breakdown.0.rate). 숫자 필드는 기준안 대비 차이(delta_vs_baseline)를, 숫자가 아닌 필드는 null 을 반환한다. 시나리오는 이름이 겹치지 않게 최대 50개까지 받는다."""
        ...
    def div(self, a: Num, b: Num, trace_level: Num = 'summary') -> _m7.ArithmeticResult:
        """Decimal 정밀 나눗셈 a / b. a 와 b 는 쉼표, 단위, 공백 없는 숫자 문자열이며 b 가 0 이면 오류를 반환한다. 몫은 유효숫자 50자리로 계산되어 나누어떨어지지 않으면 50자리에서 끊긴다. 정수 몫이나 원 단위 절사가 필요하면 결과를 별도로 반올림한다."""
        ...
    def explain(self, tool: Num, arguments: dict[str, Any], lang: Num = 'ko') -> _m10.ExplainResult:
        """설명 모드: 읽기 전용 도구 tool 을 arguments 로 실행하고, 수식, 입력, 계산 단계, 결과, 적용 정책(상태, 시행 기간)과 근거 조문을 평문(lang: ko 또는 en)으로 풀어 반환한다. 수치는 도구 결과 그대로이며 설명은 trace 를 서술할 뿐이다. 긴 값은 300자에서 줄여 보이고 원본은 result 에 있다."""
        ...
    def mul(self, operands: list[Num], trace_level: Num = 'summary') -> _m7.ArithmeticResult:
        """Decimal 정밀 곱셈. operands(쉼표, 단위, 공백 없는 숫자 문자열 목록)의 곱을 result 문자열로 반환한다. 유효숫자 50자리를 넘는 곱은 그 자릿수로 반올림되며 그 밖의 반올림은 없다. 세금이나 이자 계산에는 전용 도구를 쓴다."""
        ...
    def pipeline(self, steps: list[dict[str, Any]], step_timeout_s: float = 2.0, pipeline_timeout_s: float = 30.0) -> _m11.PipelineResult:
        """의존 관계(DAG)를 가진 도구 호출을 순서대로 실행하고 앞 단계 결과를 뒤 단계 입력으로 전달한다. steps 는 id, tool, args 목록(최대 50단계, 깊이 10)이며 args 에서 ${단계id.result.필드} 로 앞 결과를 참조한다. 실패한 단계의 하류는 skipped 가 되고 pipeline_id 로 재개할 수 있다. 서로 독립인 호출은 core.batch 를 쓴다."""
        ...
    def pipeline_resume(self, pipeline_id: Num, from_step: Num) -> _m11.PipelineResult:
        """이전 core.pipeline 실행을 pipeline_id 로 지정하고 from_step 단계부터 다시 실행한다. from_step 앞쪽의 성공 단계는 결과를 재사용(reused)한다. 실행 기록은 약 10분 동안만 보관되어 만료되면 오류가 난다. 입력을 바꿔 다시 계산하려면 새로 core.pipeline 을 호출한다."""
        ...
    def solve_for(self, tool: Num, arguments: dict[str, Any], variable: Num, target_field: Num, target: Num, lower: Num, upper: Num, tolerance: Num = '0.5', max_iter: int = 100, integer: bool = False) -> _m10.SolveForResult:
        """역산: 읽기 전용 도구 tool 의 결과 필드 target_field 가 target 이 되도록 숫자 문자열 입력 variable 을 [lower, upper] 에서 이분법(Decimal)으로 찾는다. 예: 세후 월급에서 세전 월급 구하기. 구간 양 끝의 함수값 부호가 달라야 하며 단계별 함수는 가장 가까운 해와 residual 을 반환한다. 잔차가 tolerance(기본 0.5) 이내면 converged 가 true 이고 max_iter(기본 100)는 최대 200이다."""
        ...
    def sub(self, a: Num, b: Num, trace_level: Num = 'summary') -> _m7.ArithmeticResult:
        """Decimal 정밀 뺄셈 a - b. a 와 b 는 쉼표, 단위, 공백 없는 숫자 문자열이며 결과는 result 문자열이다. 유효숫자 50자리 안에서 계산하고 별도 반올림은 없다. 순서에 주의한다(a 에서 b 를 뺀다)."""
        ...


class _CryptoTools(Protocol):
    def carmichael_lambda(self, n: Num) -> _m12.CarmichaelLambdaResult:
        """카마이클 함수 λ(n) = lcm(λ(p^k)) 를 구한다. n 은 1 이상 10^14 이하의 정수 문자열이며 시행 나눗셈으로 소인수분해하므로 한도를 넘으면 오류다. 결과 키는 lambda(정수 문자열)와 factorization 이다. λ(n) 은 φ(n) 의 약수이므로 둘을 혼동해 쓰지 않는다."""
        ...
    def crt(self, residues: list[Num], moduli: list[Num]) -> _m12.CrtResult:
        """중국인의 나머지 정리로 연립합동식 x ≡ r_i (mod m_i) 의 해 x 를 구한다. residues, moduli 는 길이가 같은 정수 문자열 리스트이고 moduli 는 모두 양수이며 쌍별 서로소여야 한다. x 는 0 이상 modulus(법의 곱) 미만이다. 서로소가 아닌 법은 해가 있어도 거부한다."""
        ...
    def egcd(self, a: Num, b: Num) -> _m12.EgcdResult:
        """확장 유클리드 알고리즘으로 gcd(a, b) = a*x + b*y 를 만족하는 gcd 와 Bezout 계수 x, y 를 구한다. a, b 는 정수 문자열(자릿수 한도 2048)이고 gcd 는 0 이상이다. 계수 쌍은 유일하지 않으며 이 알고리즘이 내는 한 쌍이다. 모듈러 역원이 목적이면 modinv 가 직접적이다."""
        ...
    def euler_totient(self, n: Num) -> _m12.EulerTotientResult:
        """오일러 토션트 φ(n) = n * Π(1 - 1/p) 를 구한다. n 은 1 이상 10^14 이하의 정수 문자열이며 시행 나눗셈으로 소인수분해하므로 한도를 넘으면 오류다. phi 는 정수 문자열, factorization 은 소수 문자열을 지수에 대응시킨 맵이다. RSA 크기의 수에는 쓸 수 없다."""
        ...
    def gcd(self, a: Num, b: Num) -> _m13.GcdResult:
        """두 정수의 최대공약수(GCD)를 구한다. a, b 는 정수 문자열(부호는 무시, 자릿수 한도 2048)이고 결과 result 는 정수 문자열이다. 둘 다 0 이면 0. 소수점이나 쉼표가 든 값은 거부하며, 세 수 이상은 결과를 다시 넣어 이어서 호출한다."""
        ...
    def hash(self, data: Num, algorithm: Num = 'sha256') -> _m14.HashDataResult:
        """문자열을 UTF-8 로 인코딩해 해시를 소문자 16진수 hex 로 반환한다. algorithm 은 sha256(기본) | sha512 | blake2b(64바이트 출력)이며 대소문자를 구분하지 않는다. 무결성 지문 확인용이고, 솔트와 반복이 없어 비밀번호 저장에는 쓰지 않는다."""
        ...
    def is_prime(self, n: Num, k: int = 20) -> _m15.IsPrimeResult:
        """Miller-Rabin 으로 소수 여부 is_prime(bool)을 판정한다. n 은 정수 문자열(자릿수 한도 2048)이며 2 미만과 음수는 False. 약 3.8e18 미만은 고정 증인이라 결정적이고, 그 이상은 무작위 증인 k 회(기본 20, 1~256)라 확률적이어서 True 가 소수 증명은 아니다. 소인수분해는 하지 않는다."""
        ...
    def lcm(self, a: Num, b: Num) -> _m13.LcmResult:
        """두 정수의 최소공배수(LCM)를 구한다. a, b 는 정수 문자열(부호는 무시, 자릿수 한도 2048)이고 큰 정수도 정확히 계산해 result 를 정수 문자열로 돌려준다. 둘 중 하나가 0 이면 0 이다. 분수의 통분에는 분모들의 LCM 을 쓰되, 소수 입력은 받지 않는다."""
        ...
    def modinv(self, a: Num, m: Num) -> _m13.ModinvResult:
        """모듈러 역원 a^-1 mod m 을 구한다. a, m 은 정수 문자열(자릿수 한도 2048)이고 m 은 2 이상이어야 한다. result 는 0 이상 m 미만이며, gcd(a, m) 이 1 이 아니면 역원이 없어 오류가 난다. a 가 0 이거나 m 과 약수를 공유하면 역원이 없다."""
        ...
    def modpow(self, base: Num, exponent: Num, modulus: Num) -> _m13.ModpowResult:
        """모듈러 거듭제곱 base^exponent mod modulus 를 구한다. 세 인자는 정수 문자열(자릿수 한도 2048)이며 modulus 는 1 이상, exponent 는 0 이상이어야 한다. result 는 0 이상 modulus 미만의 정수 문자열이다. 음수 지수로 역원을 구하려면 modinv 를 쓴다."""
        ...


class _DatetimeTools(Protocol):
    def add_business_days(self, start_date: Num, days: int, country: Num = 'KR', extra_holidays: list[Num] | None = None) -> _m16.AddBusinessDaysResult:
        """start_date 에 영업일 기준으로 days 를 더한(음수면 뺀) 날짜 end_date 를 YYYY-MM-DD 로 반환한다. 토·일, holidays 패키지의 country(기본 KR) 공휴일, extra_holidays 를 건너뛰고 시작일은 세지 않는다. days 는 절대값 100000 이하이며, 0 이면 시작일이 휴일이어도 그대로 반환한다."""
        ...
    def age(self, birth_date: Num, reference_date: Num | None = None) -> _m17.AgeResult:
        """만 나이(한국 법정 연령)를 years, months, days 정수로 계산한다. 날짜는 YYYY-MM-DD 이고 생일 당일에 한 살이 오른다. reference_date 를 생략하면 서버의 오늘 날짜를 쓰므로 실행일마다 결과가 달라진다. 기준일이 생일보다 앞서면 오류이며 세는나이는 계산하지 않는다."""
        ...
    def count_business_days(self, start: Num, end: Num, country: Num = 'KR') -> _m16.CountBusinessDaysResult:
        """start 와 end 사이의 영업일 수 count 를 정수로 센다. 날짜는 YYYY-MM-DD 이고 양 끝 날짜를 포함하며 토·일과 holidays 패키지의 country(기본 KR) 공휴일은 제외한다. end 가 start 보다 앞서거나 구간이 100000일을 넘으면 오류이고, 임시 휴일을 더하는 입력은 없다."""
        ...
    def day_count(self, start: Num, end: Num, convention: Num) -> _m18.DayCountResult:
        """이자 계산용 일수 days(정수)와 연 환산 비율 year_fraction(Decimal 문자열)을 구한다. convention 은 30/360(말일 31일 보정만 적용, 2월 말일 규칙 없음) | ACT/365 | ACT/ACT(연 경계별 윤년 분모) | ACT/360 이며 날짜는 YYYY-MM-DD, end 는 start 이후여야 한다. 비율은 반올림 없이 유효 50자리까지 나온다."""
        ...
    def diff(self, start: Num, end: Num, unit: Num) -> _m17.DiffResult:
        """두 날짜의 차이를 unit(days | weeks | months | years) 단위의 정수 문자열 value 로 돌려준다. 날짜는 YYYY-MM-DD 이다. weeks 는 일수를 7 로 나눈 몫(내림), months 와 years 는 가득 찬 달과 해만 세며 end 가 start 보다 앞서면 음수이다. 소수 단위나 남는 일수는 주지 않는다."""
        ...
    def fiscal_quarter(self, as_of: Num, country: Num = 'KR') -> _m19.FiscalQuarterResult:
        """기준일 as_of(YYYY-MM-DD)가 속한 회계분기 번호 quarter(1~4)와 시작·종료일을 구한다. country(KR | US | JP | UK, 기본 KR)의 회계연도 시작일에서 3개월씩 끊으며 시작일의 일자를 유지한다(UK 는 분기마다 6일 시작). 부가세 신고 등 법정 신고기한은 계산하지 않는다."""
        ...
    def fiscal_year(self, as_of: Num, country: Num = 'KR') -> _m19.FiscalYearResult:
        """기준일 as_of(YYYY-MM-DD)가 속한 회계연도의 라벨 fiscal_year 와 시작·종료일을 구한다. country 는 KR | US(1/1~12/31), JP(4/1~다음 해 3/31), UK(4/6~다음 해 4/5)이며 라벨은 시작일이 속한 해이다. 기업별 결산기는 반영하지 않으므로 고정 국가 기준 연도 판정에만 쓴다."""
        ...
    def lunar_holiday(self, name: Num, year: int) -> _m20.LunarHolidayResult:
        """음력 명절을 양력 solar_date 로 환산한다. name 은 seollal(설날), jeongwol_daeboreum(정월대보름), buddhas_birthday(부처님오신날), dano(단오), chilseok(칠석), chuseok(추석), seotdal_geumum(섣달그믐)이고 year 는 음력년(2020~2030)이라 섣달그믐은 이듬해 양력 1~2월에 나온다. 윤달은 쓰지 않으며 연휴와 대체공휴일은 계산하지 않는다."""
        ...
    def lunar_to_solar(self, lunar_year: int, lunar_month: int, lunar_day: int, is_leap: bool = False) -> _m20.LunarToSolarResult:
        """음력 날짜를 양력 solar_date(YYYY-MM-DD)로 바꾼다. lunar_year 는 2020~2030, lunar_month 는 1~12, lunar_day 는 1~30 정수이고 윤달이면 is_leap=True 를 준다. 그 해에 없는 윤달이나 달 길이를 넘는 일자는 오류이며 범위 밖 연도는 지원하지 않는다."""
        ...
    def payroll_period(self, as_of: Num, start_day: int = 1) -> _m19.PayrollPeriodResult:
        """as_of(YYYY-MM-DD)가 속한 월 단위 급여 정산 기간의 period_start, period_end 를 구한다. start_day(1~28, 기본 1)일에 시작해 다음 달 start_day 전날에 끝난다. 지급일이 아닌 산정 기간이며 29~31일 시작은 지원하지 않는다."""
        ...
    def solar_terms(self, year: int) -> _m20.SolarTermsResult:
        """양력 year 의 24절기 이름과 양력 날짜 24개를 입춘부터의 순서로 반환한다. 연도별 계산이 아닌 고정 일자표이므로 모든 연도에 같은 월일이 나오고 실제 절기일과 하루 어긋날 수 있다. 소한·대한은 같은 해 1월 날짜이며 절기 시각이 필요한 용도에는 쓰지 않는다."""
        ...
    def solar_to_lunar(self, solar_date: Num) -> _m20.SolarToLunarResult:
        """양력 날짜를 음력 년·월·일(lunar_year, lunar_month, lunar_day)과 윤달 여부 is_leap 으로 바꾼다. 입력은 YYYY-MM-DD 이고 내장 조견표의 음력 2020~2030년에 해당하는 2020-01-25~2031-01-22 만 지원하며 범위 밖은 오류이다. 그 밖의 연도 음력 계산에는 쓸 수 없다."""
        ...
    def tax_period_kr(self, as_of: Num) -> _m19.TaxPeriodKrResult:
        """as_of(YYYY-MM-DD)가 속한 한국 소득세 과세기간(소득세법 제5조, 1/1~12/31)의 연도 tax_year 와 경계일을 반환한다. 사업 개시·폐업, 사망, 출국으로 달라지는 중도 종료 기간은 다루지 않으며 법인의 사업연도에는 쓰지 않는다."""
        ...
    def tz_convert(self, iso_datetime: Num, from_tz: Num, to_tz: Num) -> _m21.TzConvertResult:
        """IANA 타임존 사이에서 시각을 변환해 UTC 오프셋이 붙은 ISO 8601 문자열 iso_datetime 으로 돌려준다. 입력은 초 단위(YYYY-MM-DDTHH:MM:SS, 공백 구분 허용, 소수 초 불가)이며 오프셋이 없으면 from_tz 로 해석하고 있으면 from_tz 를 쓰지 않는다. 서머타임 겹침 시각은 앞선 쪽으로 해석한다."""
        ...


class _EngineeringTools(Protocol):
    def ac_impedance(self, frequency: Num, resistance: Num = '0', inductance: Num = '0', capacitance: Num = '0', topology: Num = 'series') -> _m22.AcImpedanceResult:
        """R, L, C 조합의 AC 합성 임피던스 크기와 위상각을 구한다. frequency(Hz, 0 초과), resistance(Ω), inductance(H), capacitance(F)는 0 이상 Decimal 문자열이고 topology='series' 또는 'parallel'. 반환: magnitude(Ω), phase_deg(도), real, imag. 값 0은 그 소자가 없다는 뜻이며 단락이나 0 용량이 아니다. 병렬에서 소자를 모두 생략하면 오류."""
        ...
    def beam_deflection(self, case: Num, length: Num, young: Num, inertia: Num, load: Num) -> _m23.BeamDeflectionResult:
        """표준 하중 조건의 보 최대 처짐 δ_max 를 계산한다. case: cantilever_point_end(PL³/3EI), cantilever_uniform(wL⁴/8EI), simply_supported_point_center(PL³/48EI), simply_supported_uniform(5wL⁴/384EI). length m, young Pa, inertia m⁴, load 는 점하중 N 또는 등분포하중 N/m(모두 0 초과)이며 처짐은 m. 하중 종류와 case 가 어긋나면 값이 틀리고 전단 변형은 무시한다. 반올림 없이 50자리 유효숫자."""
        ...
    def bearing_equivalent_load(self, radial_load: Num, axial_load: Num, x_factor: Num, y_factor: Num) -> _m24.BearingEquivalentLoadResult:
        """베어링 동등가하중 P = X·Fr + Y·Fa 를 계산한다. 반경하중, 축하중, 계수 X 와 Y 는 모두 0 이상이고 두 하중이 동시에 0 이면 오류다. X, Y 는 카탈로그 값을 직접 넣어야 하며 Fa/Fr 과 e 의 비교로 계수를 고르는 과정은 하지 않는다. 순수 반경하중이면 axial_load 와 y_factor 를 0 으로 둔다. 결과는 bearing_life_l10 의 equivalent_load 로 쓴다."""
        ...
    def bearing_life_l10(self, dynamic_capacity: Num, equivalent_load: Num, bearing_type: Num) -> _m24.BearingLifeL10Result:
        """구름 베어링 기본정격수명 L10 = (C/P)^p 를 백만 회전(10⁶ rev) 단위로 계산한다. bearing_type 'ball' 은 p=3(정확 계산), 'roller' 는 p=10/3(30자리 유효숫자). dynamic_capacity 와 equivalent_load 는 같은 힘 단위이고 0 초과여야 한다. 신뢰도나 윤활 보정계수는 적용하지 않으며 등가하중은 bearing_equivalent_load 로 먼저 구한다."""
        ...
    def bending_stress(self, moment: Num, distance_neutral: Num, inertia: Num) -> _m23.BendingStressResult:
        """휨응력 σ = M·c/I 를 계산한다. moment 는 굽힘모멘트(N·m, 부호 유지), distance_neutral 은 중립축에서 응력을 구할 섬유까지 거리 c(m, 0 초과), inertia 는 단면 이차모멘트 I(m⁴, 0 초과)이며 결과는 Pa. 최외곽 응력이 필요하면 c 에 전체 높이가 아니라 중립축에서 바깥 면까지의 거리를 넣어야 한다. 반올림 없이 50자리 유효숫자."""
        ...
    def bernoulli(self, pressure_1: Num, velocity_1: Num, elevation_1: Num, density: Num, pressure_2: Num | None = None, velocity_2: Num | None = None, elevation_2: Num | None = None, gravity: Num = '9.80665') -> _m25.BernoulliResult:
        """베르누이 방정식 P + ½ρv² + ρgz = 일정 을 풀어 상태 2의 미지수 하나를 구한다. pressure_2, velocity_2, elevation_2 중 정확히 하나만 생략(None)하며 압력 Pa, 속도 m/s, 높이 m, 밀도 kg/m³, 중력가속도 기본 9.80665 m/s². 비압축성 비점성 정상류 가정이라 펌프나 마찰 손실이 있는 관로에는 쓰지 않는다. 속도 해는 30자리, 나머지는 반올림 없음."""
        ...
    def bode_magnitude_phase(self, mode: Num, corner_freq: Num, frequency: Num) -> _m26.BodeMagnitudePhaseResult:
        """단일 극점 또는 영점 1차 전달함수의 Bode 크기(dB)와 위상(도)을 구한다. mode='pole'이면 G(jω)=1/(1+jω/ωc), 'zero'이면 G(jω)=1+jω/ωc. corner_freq ωc와 frequency ω는 같은 단위(rad/s 또는 Hz)의 0 초과 Decimal 문자열이며 비율만 쓴다. 유효숫자 30자리. 오용 주의: 극점과 영점이 여러 개인 전달함수는 직접 합산해야 한다."""
        ...
    def capacitor_combine(self, capacitors: list[Num], topology: Num) -> _m27.CombineResult:
        """커패시터 여러 개의 합성 정전용량을 구한다. topology='series'면 1/C=Σ(1/Cᵢ), 'parallel'이면 C=ΣCᵢ. capacitors 는 0 초과 정전용량(F)의 Decimal 문자열 목록이며 최소 1개, total 은 입력과 같은 단위. 계산은 유효숫자 50자리 Decimal. 오용 주의: 저항과 인덕터는 직렬 병렬 공식이 반대다."""
        ...
    def convective_heat_transfer(self, heat_transfer_coefficient: Num, area: Num, temperature_surface: Num, temperature_fluid: Num) -> _m28.HeatRateResult:
        """뉴턴 냉각 법칙에 따른 대류 열전달 Q = h·A·(T_s − T_∞) (W)를 계산한다. heat_transfer_coefficient W/(m²·K), area m², 온도는 K 또는 °C(차이만 사용). 표면이 유체보다 뜨거우면 양수, 차가우면 음수이다. h 는 입력값이며 유동 조건에서 구해 주지 않는다. 반올림 없이 50자리 유효숫자."""
        ...
    def darcy_weisbach(self, friction_factor: Num, length: Num, diameter: Num, velocity: Num, density: Num = '1000', gravity: Num = '9.80665') -> _m25.DarcyWeisbachResult:
        """다르시-바이스바흐 식으로 관 마찰 손실 수두 h_f = f·(L/D)·v²/(2g) (m)와 압력강하 ρ·g·h_f (Pa)를 계산한다. friction_factor 무차원, length 와 diameter m, velocity m/s, density 기본 1000 kg/m³, gravity 기본 9.80665. 마찰계수를 모르면 moody_friction_factor 로 먼저 구하며 밸브나 곡관의 국부 손실은 포함하지 않는다. 반올림 없이 50자리 유효숫자."""
        ...
    def db_convert(self, mode: Num, value: Num, reference: Num = '1') -> _m29.DbConvertResult:
        """dB, Np, dBm과 선형 값을 서로 변환한다. mode: v_to_db(20·log10(value/reference)), p_to_db(10·log10(value/reference)), db_to_v, db_to_p, np_to_db, db_to_np, w_to_dbm(1 mW 기준), dbm_to_w. value 는 Decimal 문자열, reference(기본 1)는 v_to_db와 p_to_db에서만 쓴다. 로그 입력은 0 초과여야 하며 유효숫자 30자리. 오용 주의: 전압비에 p_to_db를 쓰면 값이 절반이 된다."""
        ...
    def elastic_modulus_relate(self, young: Num | None = None, shear: Num | None = None, poisson: Num | None = None, bulk: Num | None = None) -> _m30.ElasticModulusRelateResult:
        """등방성 선형 탄성체에서 영률 E, 전단탄성계수 G, 푸아송비 ν, 체적탄성계수 K 중 정확히 2개를 받아 나머지 2개를 계산한다(E = 2G(1+ν) = 3K(1−2ν)). 탄성계수는 같은 응력 단위로 0 초과, 푸아송비는 -1 초과 0.5 미만이며 입력이 2개가 아니면 오류. 이방성 재료에는 쓸 수 없다. 반올림 없이 50자리 유효숫자."""
        ...
    def electrical_ohm(self, voltage: Num | None = None, current: Num | None = None, resistance: Num | None = None) -> _m31.ElectricalOhmResult:
        """옴의 법칙 V=IR에서 빠진 한 값을 구한다. voltage(V), current(A), resistance(Ω) 중 정확히 2개를 Decimal 문자열로 넣으면 나머지를 계산해 세 값을 모두 돌려준다. current와 resistance는 0 초과, voltage는 입력일 때 0 이상이어야 한다. 오용 주의: 3개 이상이나 1개만 넣으면 오류이고, 교류 임피던스에는 쓸 수 없다(ac_impedance 사용)."""
        ...
    def electrical_power(self, power: Num | None = None, voltage: Num | None = None, current: Num | None = None, resistance: Num | None = None) -> _m31.ElectricalPowerResult:
        """직류 전력 방정식 P=VI=I²R=V²/R에서 나머지 값을 구한다. power(W), voltage(V), current(A), resistance(Ω) 중 정확히 2개를 Decimal 문자열로 넣으면 네 값을 모두 돌려준다. (P,R) 조합은 제곱근을 쓰며 양의 근만 반환한다. 오용 주의: 교류의 유효전력은 역률을 곱해야 하므로 three_phase_power 등을 쓴다."""
        ...
    def euler_buckling(self, young: Num, inertia: Num, length: Num, end_condition: Num | None = None, effective_length_factor: Num | None = None) -> _m23.EulerBucklingResult:
        """오일러 좌굴 임계하중 P_cr = π²EI/(KL)² (N)를 계산한다. end_condition 으로 K 를 자동 설정(fixed_free 2, pinned_pinned 1, fixed_pinned 0.699, fixed_fixed 0.5)하거나 effective_length_factor 를 직접 주되 둘 중 정확히 하나만 지정한다. young Pa, inertia m⁴, length m. 세장한 기둥의 탄성 좌굴 식이라 짧은 기둥에는 항복 하중보다 크게 나올 수 있다. π 는 30자리."""
        ...
    def exponential_reliability(self, failure_rate: Num, time: Num) -> _m32.ExponentialReliabilityResult:
        """지수분포 고장 모델의 신뢰도 R(t) = exp(−λt), 불신뢰도 1−R, 평균 고장간격 MTBF = 1/λ 를 계산한다. failure_rate λ 는 단위시간당 고장률(0 초과), time 은 같은 시간 단위의 t(0 이상)이며 시간 단위가 다르면 틀린다. 고장률이 일정한 우발 고장 구간 가정이라 마모 고장에는 weibull_reliability 를 쓴다. exp 는 30자리 유효숫자."""
        ...
    def first_order_response(self, gain: Num, time_constant: Num, input_step: Num, time: Num) -> _m26.FirstOrderResponseResult:
        """1차 시스템 G(s)=K/(τs+1)의 스텝 응답 y(t)=K·u·(1−exp(−t/τ))를 구한다. gain K, time_constant τ(초, 0 초과), input_step u, time t(초, 0 이상)는 Decimal 문자열. 지수항은 유효숫자 30자리. 반환: response, steady_state(K·u), time_constant. 오용 주의: 2차 이상 시스템이나 임펄스 응답에는 쓸 수 없다."""
        ...
    def fluid_reynolds(self, density: Num, velocity: Num, length: Num, viscosity: Num) -> _m25.FluidReynoldsResult:
        """레이놀즈 수 Re = ρvL/μ 를 계산하고 층류(Re < 2300), 천이(2300 이상 4000 이하), 난류(4000 초과)로 분류한다. 밀도 kg/m³, 속도 m/s, 특성길이 m, 점성계수 Pa·s 를 숫자 문자열로 받고 모두 0 초과여야 한다. 경계값은 관 유동 기준이라 평판 등 다른 형상에는 맞지 않는다. 반올림 없이 50자리 유효숫자로 계산한다."""
        ...
    def fourier_heat_conduction(self, thermal_conductivity: Num, area: Num, temperature_hot: Num, temperature_cold: Num, thickness: Num) -> _m28.HeatRateResult:
        """1차원 정상상태 평판 열전도 Q = k·A·(T_hot − T_cold)/L (W)를 계산한다. thermal_conductivity W/(m·K), area m², thickness m, 온도는 K 또는 °C(차이만 사용). temperature_hot 이 temperature_cold 보다 낮으면 오류이며 역방향은 인자를 바꿔 호출한다. 다층벽은 층별 L/(kA)를 구해 thermal_resistance 로 합성한다. 반올림 없이 50자리 유효숫자."""
        ...
    def gear_ratio(self, teeth_driver: Num, teeth_driven: Num) -> _m24.GearRatioResult:
        """단순 기어쌍의 기어비 i = 피동 잇수 / 구동 잇수 를 계산하고 방향을 함께 반환한다. i > 1 이면 reduction(감속), i < 1 이면 overdrive(증속), 1 이면 direct. 잇수는 0 초과 숫자 문자열이며 구동과 피동 인수를 바꾸면 역수가 나온다. 다단 기어열은 단별로 구해 곱해야 한다. 반올림 없이 50자리 유효숫자."""
        ...
    def gear_torque_transmission(self, input_torque: Num, teeth_driver: Num, teeth_driven: Num, efficiency: Num = '1') -> _m24.GearTorqueTransmissionResult:
        """기어쌍을 통과한 출력 토크 τ_out = τ_in·(피동 잇수/구동 잇수)·η 를 계산하고 기어비도 반환한다. 출력 토크는 input_torque 와 같은 단위(예: N·m)이고 efficiency 는 기본 1, [0, 1] 범위의 소수여야 한다(95 가 아니라 0.95). 속도는 기어비에 반비례해 변하므로 출력 속도는 별도로 구해야 한다. 반올림 없이 50자리 유효숫자."""
        ...
    def hardness_convert(self, value: Num, from_scale: Num, to_scale: Num) -> _m33.HardnessConvertResult:
        """강재의 경도를 HV, HB, HRC 사이에서 근사식(HV ≈ 0.95·HB, HRC ≈ 88.887 − 0.058·HV)으로 환산한다. value 는 0 초과이고 HRC 입력은 88.887 미만이어야 한다. 선형 근사라 적용 범위는 HV 240~800 정도이며 그 밖이나 비철금속은 오차가 크므로 정밀 환산에는 ASTM E140 표를 쓴다. 반올림 없는 Decimal 문자열."""
        ...
    def hazen_williams_flow(self, coefficient: Num, diameter: Num, head_loss: Num, length: Num) -> _m25.HazenWilliamsFlowResult:
        """하젠-윌리엄스 식(SI)으로 관 유량 Q = 0.278·C·D^2.63·S^0.54 (m³/s)를 계산한다. S = head_loss/length 는 동수경사, coefficient 는 관 조도계수 C(무차원), diameter 와 head_loss, length 는 m. 물 관로용 경험식이라 다른 유체에는 쓰지 않는다. 손실수두가 0 이면 유량 0, 지수 계산은 30자리 유효숫자."""
        ...
    def inductor_combine(self, inductors: list[Num], topology: Num) -> _m27.CombineResult:
        """인덕터 여러 개의 합성 인덕턴스를 구한다. topology='series'면 L=ΣLᵢ, 'parallel'이면 1/L=Σ(1/Lᵢ). inductors 는 0 초과 인덕턴스(H)의 Decimal 문자열 목록이며 최소 1개, total 은 입력과 같은 단위. 상호 인덕턴스는 고려하지 않는다. 오용 주의: 커패시터는 직렬 병렬 공식이 반대다."""
        ...
    def lc_resonant_frequency(self, inductance: Num, capacitance: Num) -> _m22.LcResonantFrequencyResult:
        """LC 공진 주파수 f0=1/(2π√(LC))를 구한다. inductance(H)와 capacitance(F)는 0 초과 Decimal 문자열이고 결과는 Hz(각주파수 rad/s가 아님). 이상적인 L, C만 가정하며 저항 손실에 의한 주파수 이동은 반영하지 않는다."""
        ...
    def lmtd(self, delta_t_hot_inlet: Num, delta_t_cold_outlet: Num) -> _m28.LmtdResult:
        """열교환기 대수평균온도차 LMTD = (ΔT₁ − ΔT₂)/ln(ΔT₁/ΔT₂)를 계산한다. 양 끝단의 온도차 두 값(K 또는 °C 차, 모두 0 초과)을 받고 같으면 극한값 ΔT₁ 을 반환한다. 병류와 향류에 맞게 각 끝단의 온도차를 직접 정해 넣어야 하며 다관식 열교환기의 보정계수 F 는 포함하지 않는다. ln 은 30자리 유효숫자."""
        ...
    def max_power_transfer(self, v_th: Num, r_th: Num) -> _m34.MaxPowerTransferResult:
        """최대 전력 전달 정리로 최적 부하와 최대 전력을 구한다. R_L=R_th일 때 P_max=V_th²/(4R_th). v_th(V)와 r_th(Ω, 0 초과)는 Decimal 문자열. 반환: optimal_load(Ω), max_power(W). 오용 주의: 이때 효율은 50%이므로 전력 효율이 중요한 전원 설계의 부하 선정 기준은 아니다."""
        ...
    def mech_strain(self, delta_length: Num, original_length: Num) -> _m30.MechStrainResult:
        """선형 변형률 ε = ΔL / L (무차원)을 계산한다. delta_length 와 original_length 는 같은 길이 단위여야 하며(mm 와 m 을 섞으면 틀림) original_length 는 0 초과, delta_length 는 음수(수축)도 가능하다. 반올림 없이 50자리 유효숫자."""
        ...
    def mech_stress(self, force: Num, area: Num) -> _m30.MechStressResult:
        """수직응력 σ = F / A 를 계산한다. force 는 힘(N), area 는 단면적(m², 0 초과)이며 결과는 Pa(N/m²). 단위 변환은 하지 않고 입력 단위 그대로 나누므로 N 과 mm² 를 넣으면 MPa 가 나온다. force 부호는 유지되며 인장과 압축의 부호 약속은 호출자가 정한다. 반올림 없이 50자리 유효숫자."""
        ...
    def moment_of_inertia(self, shape: Num, mass: Num, radius: Num | None = None, length: Num | None = None) -> _m30.MomentOfInertiaResult:
        """표준 형상의 질량 관성모멘트 I (kg·m²)를 계산한다. solid_disk(½mr²), thin_ring(mr²), solid_sphere(2/5 mr²)는 radius 가, thin_rod_center(mL²/12)와 thin_rod_end(mL²/3)는 length 가 필요하다. mass 와 치수는 0 초과이며 mass 는 kg, 치수는 m. 막대는 중심 또는 끝점을 지나는 축 기준이라 다른 축은 평행축 정리를 따로 적용해야 한다. 반올림 없음."""
        ...
    def moody_friction_factor(self, reynolds: Num, roughness: Num, diameter: Num) -> _m25.MoodyFrictionFactorResult:
        """콜브룩 방정식 1/√f = -2·log10(ε/(3.7D) + 2.51/(Re·√f)) 를 스위미-제인 초기값에서 시작해 최대 100회, 허용오차 1e-10 으로 반복 풀어 다르시 마찰계수 f 를 구한다. Re 2300 미만은 f = 64/Re 로 즉시 반환(iterations 0). reynolds 무차원, roughness 와 diameter 는 같은 길이 단위, 수렴 실패 시 오류. 난류 결과는 30자리 유효숫자."""
        ...
    def norton_equivalent(self, v_th: Num, r_th: Num) -> _m34.NortonEquivalentResult:
        """테브난 등가(V_th, R_th)를 노턴 등가로 변환한다. I_N=V_th/R_th, R_N=R_th. v_th(V)와 r_th(Ω, 0 초과)는 Decimal 문자열. 반환: i_n(A), r_n(Ω). 오용 주의: 개방 전압과 단락 전류에서 바로 구하려면 먼저 thevenin_equivalent 를 쓴다."""
        ...
    def opamp_gain(self, feedback_resistance: Num, input_resistance: Num, configuration: Num = 'inverting') -> _m29.OpampGainResult:
        """이상적 연산증폭기의 폐루프 전압 이득을 구한다. configuration='inverting'이면 -Rf/Rin, 'non_inverting'이면 1+Rf/Rin. feedback_resistance와 input_resistance는 0 초과 Decimal 문자열(Ω)이고 gain 은 배율이다(dB 아님, db_convert로 변환). 오용 주의: 유한 개방 이득, 대역폭, 포화 전압은 반영하지 않는다."""
        ...
    def parallel_reliability(self, component_reliabilities: list[Num]) -> _m32.SystemReliabilityResult:
        """병렬(중복) 시스템 신뢰도 R_sys = 1 − Π(1 − R_i)를 계산한다. component_reliabilities 는 구성요소 신뢰도의 숫자 문자열 목록(1개 이상, 각 0 이상 1 이하)이며 소수로 넣는다(0.99). 하나라도 작동하면 시스템이 작동하는 구조이며 구성요소가 독립이라고 가정한다. 구성요소 k개 이상이 필요한 k-of-n 구조에는 쓸 수 없다. 반올림 없이 50자리 유효숫자."""
        ...
    def pid_discrete_output(self, kp: Num, ki: Num, kd: Num, sample_time: Num, error_curr: Num, error_prev: Num, error_prev2: Num, output_prev: Num) -> _m26.PidDiscreteOutputResult:
        """속도형(velocity form) 이산 PID의 새 출력 u_k=u_{k-1}+Δu를 구한다. Δu=Kp·Δe+Ki·e·Ts+Kd·(Δe−Δe_prev)/Ts. kp, ki, kd, sample_time Ts(0 초과), error_curr, error_prev, error_prev2, output_prev 는 Decimal 문자열. 반환: output, delta_u, p_term, i_term, d_term. 적분항은 현재 오차 e에 Ts를 곱하는 방식이며 출력 포화와 anti-windup은 없다."""
        ...
    def power_factor_correction(self, real_power: Num, current_pf: Num, target_pf: Num, voltage: Num, frequency: Num) -> _m35.PowerFactorCorrectionResult:
        """지상(유도성) 부하의 역률을 목표 역률로 올리는 병렬 커패시턴스를 구한다. Q_c=P·(tanφ₁−tanφ₂), C=Q_c/(2π·f·V²). real_power(W), voltage(V), frequency(Hz)는 0 초과, current_pf와 target_pf는 (0,1] 범위이며 target_pf가 더 커야 한다. 반환: capacitance(F), reactive_power_canceled(VAR). 오용 주의: 3상은 상별 전력과 커패시터 양단 전압으로 환산해 넣는다."""
        ...
    def pump_hydraulic_power(self, density: Num, flow_rate: Num, head: Num, gravity: Num = '9.80665', efficiency: Num | None = None) -> _m25.PumpHydraulicPowerResult:
        """펌프 수력 동력 P = ρ·g·Q·H (W)를 계산하고, efficiency(0 초과 1 이하)를 주면 축동력 P/η 도 반환한다. density kg/m³, flow_rate m³/s, head m, gravity 기본 9.80665. 효율은 백분율(80)이 아니라 소수(0.8)로 넣어야 한다. 반올림 없이 50자리 유효숫자."""
        ...
    def rc_filter_cutoff(self, resistance: Num, capacitance: Num, filter_type: Num = 'low_pass') -> _m22.RcFilterCutoffResult:
        """1차 RC 필터의 -3 dB 차단 주파수 fc=1/(2πRC)를 Hz로 구한다. resistance(Ω)와 capacitance(F)는 0 초과 Decimal 문자열. filter_type 은 'low_pass' 또는 'high_pass'이며 수식은 같고 입력 그대로 반환될 뿐이다. 오용 주의: 2차 이상 필터나 부하가 걸린 필터에는 맞지 않는다."""
        ...
    def resistor_color_code(self, bands: list[Num]) -> _m29.ResistorColorCodeResult:
        """저항기 4밴드 또는 5밴드 컬러코드를 해독해 저항값(Ω)과 허용오차(%)를 구한다. 4밴드는 [자릿수1, 자릿수2, 승수, 허용오차], 5밴드는 [자릿수1, 자릿수2, 자릿수3, 승수, 허용오차] 순서의 영문 색상명(black, brown, red, orange, yellow, green, blue, violet, gray, white, gold, silver)이며 대소문자와 앞뒤 공백은 무시한다. 오용 주의: 6밴드(온도계수)는 지원하지 않으며 읽는 방향이 반대면 값이 틀린다."""
        ...
    def resistor_parallel(self, resistors: list[Num]) -> _m31.ResistorNetworkResult:
        """병렬 연결 저항의 합성 저항 1/R_total=Σ(1/Rᵢ)를 구한다. resistors 는 0 초과 저항값(Ω)의 Decimal 문자열 목록이며 최소 1개. 계산은 유효숫자 50자리 Decimal 이다. 오용 주의: 직렬 연결에는 resistor_series 를 쓴다."""
        ...
    def resistor_series(self, resistors: list[Num]) -> _m31.ResistorNetworkResult:
        """직렬 연결 저항의 합성 저항 R_total=ΣRᵢ를 구한다. resistors 는 0 초과 저항값(Ω)의 Decimal 문자열 목록이며 최소 1개. 계산은 유효숫자 50자리 Decimal 이다. 오용 주의: 병렬 연결에는 resistor_parallel 을 쓴다."""
        ...
    def rlc_time_constant(self, mode: Num, resistance: Num | None = None, inductance: Num | None = None, capacitance: Num | None = None) -> _m22.RlcTimeConstantResult:
        """RC, RL, 직렬 RLC 회로의 시정수 또는 감쇠 특성을 구한다. mode='rc'면 τ=RC, 'rl'이면 τ=L/R, 'rlc'면 α=R/(2L), ω₀=1/√(LC), ζ=α/ω₀와 regime(underdamped, critically_damped, overdamped)을 반환한다. 필요한 R(Ω), L(H), C(F)는 모드별로 0 초과 Decimal 문자열이며 빠뜨리면 오류. 오용 주의: ζ는 직렬 RLC 기준이라 병렬 RLC에는 맞지 않는다."""
        ...
    def safety_factor(self, allowable_stress: Num, applied_stress: Num) -> _m33.SafetyFactorResult:
        """안전율 SF = 허용응력 / |작용응력| 을 계산하고 SF 1 이상이면 'safe', 미만이면 'unsafe' 를 반환한다. 두 응력은 같은 단위(Pa 또는 MPa)이며 allowable_stress 는 0 초과, applied_stress 는 0 이 아니어야 하고 부호는 무시된다. 요구 안전율(예: 1.5)과 비교하지 않으므로 safe 만으로 설계 적합을 판단하면 안 된다. 반올림 없이 50자리 유효숫자."""
        ...
    def second_order_response(self, damping_ratio: Num, natural_freq: Num) -> _m26.SecondOrderResponseResult:
        """2차 시스템 G(s)=ωn²/(s²+2ζωn·s+ωn²)의 감쇠 고유진동수 ωd, 최대 오버슈트, 정착시간을 구한다. damping_ratio ζ(0 이상)와 natural_freq ωn(rad/s, 0 초과)은 Decimal 문자열. overshoot 는 비율(0~1, 백분율 아님)이고 ζ≥1 이면 0, ζ=0 이면 1. settling_time=4/(ζωn)은 2% 기준 근사이며 ζ=0 이면 "Infinity". regime: underdamped, critically_damped, overdamped. 초월함수는 유효숫자 30자리."""
        ...
    def section_moment_inertia(self, shape: Num, width: Num | None = None, height: Num | None = None, diameter: Num | None = None, flange_width: Num | None = None, flange_thickness: Num | None = None, web_height: Num | None = None, web_thickness: Num | None = None) -> _m23.SectionMomentInertiaResult:
        """도심 중립축에 대한 단면 이차모멘트 I 를 계산한다. rectangle(width, height: bh³/12), circle(diameter: πd⁴/64), i_beam(flange_width, flange_thickness, web_height, web_thickness: BH³/12 − (B−t_w)·web_height³/12, H = web_height + 2·flange_thickness). 치수는 모두 0 초과이고 m 로 넣으면 m⁴. rectangle 의 height 는 굽힘 방향 치수이며 중공 단면은 지원하지 않는다. π 는 30자리."""
        ...
    def series_reliability(self, component_reliabilities: list[Num]) -> _m32.SystemReliabilityResult:
        """직렬 시스템 신뢰도 R_sys = ΠR_i 를 계산한다. component_reliabilities 는 구성요소 신뢰도의 숫자 문자열 목록(1개 이상, 각 0 이상 1 이하)이며 백분율(99)이 아니라 소수(0.99)로 넣는다. 구성요소가 서로 독립이라고 가정하므로 고장이 연관된 경우에는 맞지 않다. 반올림 없이 50자리 유효숫자."""
        ...
    def shear_stress(self, mode: Num, shear_force: Num, area: Num | None = None, first_moment_q: Num | None = None, inertia: Num | None = None, width: Num | None = None) -> _m23.ShearStressResult:
        """횡전단응력 τ 를 모드별로 계산한다. average 는 V/A, rectangular_max 는 1.5V/A(직사각형 단면 중립축의 최대값, area 필요), general 은 V·Q/(I·b)(first_moment_q, inertia, width 필요). shear_force 는 N, area 는 m²(0 초과)이고 결과는 Pa. 원형이나 I형 단면에 rectangular_max 를 쓰면 틀리며 필수 인자가 빠지면 오류. 반올림 없음."""
        ...
    def si_prefix_convert(self, value: Num, from_prefix: Num, to_prefix: Num) -> _m36.SiPrefixConvertResult:
        """수치를 SI 접두사 사이에서 환산한다. 결과 = value × 10^(from 지수 − to 지수)를 Decimal 로 정확히 계산한다. 접두사는 이름으로 넣고(yocto 부터 yotta 까지, 대소문자 무시, 빈 문자열이나 base 는 접두사 없음) 기호(k, M, µ)는 받지 않는다. 이진 접두사(KiB 등)와 단위 자체는 다루지 않으며 데이터 크기는 units_data_size_convert 를 쓴다."""
        ...
    def sn_fatigue_life(self, stress_amplitude: Num, fatigue_strength_coeff: Num, basquin_exponent: Num) -> _m33.SnFatigueLifeResult:
        """바스퀸 식 S_a = S_f'·(2N_f)^b 를 N_f = 0.5·(S_a/S_f')^(1/b) 로 풀어 파손까지의 사이클 수를 구한다(반전 횟수 2N_f 가 아니라 사이클 N_f). stress_amplitude 와 fatigue_strength_coeff 는 같은 응력 단위로 0 초과, basquin_exponent 는 음수(통상 -0.05 ~ -0.12). 평균응력 보정과 피로한도는 반영하지 않는다. 거듭제곱은 30자리 유효숫자."""
        ...
    def stefan_boltzmann(self, emissivity: Num, area: Num, temperature_surface: Num, temperature_surround: Num) -> _m28.HeatRateResult:
        """회색체 표면과 주위 사이의 순복사 열전달 Q = ε·σ·A·(T_s⁴ − T_surr⁴) (W)를 계산한다. σ = 5.670374419e-8 W/(m²·K⁴), emissivity 는 [0, 1], area m². 온도는 절대온도 K(0 초과)이므로 섭씨를 그대로 넣으면 틀린다. 작은 표면이 큰 주위에 둘러싸인 경우의 식이며 표면이 더 차가우면 음수. 반올림 없이 50자리 유효숫자."""
        ...
    def thermal_expansion_strain(self, alpha: Num, delta_t: Num, length: Num | None = None) -> _m33.ThermalExpansionStrainResult:
        """선팽창 변형률 ε = α·ΔT 를 계산하고 length(0 초과)를 주면 길이 변화 ΔL = ε·L₀ 도 반환한다. alpha 는 선팽창계수(1/K), delta_t 는 K 또는 °C 의 온도 변화량이며 음수면 수축이다. 온도 자체(예: 20°C)가 아니라 변화량을 넣어야 한다. ΔL 은 length 와 같은 단위. 1차원 자유 팽창만 다루며 구속 열응력은 계산하지 않는다. 반올림 없음."""
        ...
    def thermal_resistance(self, resistances: list[Num], topology: Num) -> _m28.ThermalResistanceResult:
        """열저항 K/W 를 합성한다. topology 'series' 는 R_total = ΣRᵢ, 'parallel' 은 1/R_total = Σ(1/Rᵢ). resistances 는 열저항의 숫자 문자열 목록(1개 이상, 모두 0 초과, 같은 단위)이다. 0 저항(완전 전도)은 입력할 수 없고 직렬과 병렬이 섞인 회로는 단계별로 나눠 호출해야 한다. 반올림 없이 50자리 유효숫자."""
        ...
    def thevenin_equivalent(self, open_circuit_voltage: Num, short_circuit_current: Num) -> _m34.TheveninEquivalentResult:
        """개방 전압과 단락 전류로 테브난 등가 회로를 구한다. V_th=V_oc, R_th=V_oc/I_sc. open_circuit_voltage(V)와 short_circuit_current(A, 0 초과)는 Decimal 문자열. 반환: v_th, r_th. 오용 주의: 독립 전원이 없는 회로는 V_oc가 0이라 R_th가 0으로 계산되므로 저항 합성으로 R_th를 구해야 한다."""
        ...
    def three_phase_power(self, line_voltage: Num, line_current: Num, power_factor: Num, connection: Num = 'wye') -> _m35.ThreePhasePowerResult:
        """균형 3상 회로의 피상, 유효, 무효 전력을 선간 값으로 구한다. S=√3·V_LL·I_L, P=S·cosφ, Q=√(S²−P²). line_voltage(V)와 line_current(A)는 0 초과, power_factor는 -1 이상 1 이하 Decimal 문자열. connection('wye'/'delta')은 검증만 하고 수식은 같다. Q는 항상 0 이상이라 진상 지상을 구분하지 못한다."""
        ...
    def torque_rotational_power(self, torque: Num, angular_velocity: Num) -> _m30.TorqueRotationalPowerResult:
        """회전 일률 P = τ·ω (W)를 계산한다. torque 는 N·m, angular_velocity 는 rad/s 이다. rpm 을 그대로 넣으면 틀리므로 ω = 2π·rpm/60 으로 먼저 환산해야 한다. 두 값의 부호는 그대로 곱해진다. 반올림 없이 50자리 유효숫자."""
        ...
    def weibull_reliability(self, shape: Num, scale: Num, time: Num) -> _m32.WeibullReliabilityResult:
        """2모수 와이블 분포의 신뢰도 R(t) = exp(−(t/η)^β)와 불신뢰도를 계산한다. shape β 와 scale η 는 0 초과, time 은 η 와 같은 단위의 0 이상 값이다(0 이면 R = 1). β < 1 은 초기 고장, β = 1 은 우발 고장, β > 1 은 마모 고장에 해당한다. 위치모수 γ 는 지원하지 않는다. 거듭제곱과 exp 는 30자리 유효숫자."""
        ...


class _FinanceTools(Protocol):
    def black_scholes(self, spot: Num, strike: Num, time_to_expiry: Num, rate: Num, sigma: Num, option_type: Num, dividend_yield: Num = '0') -> _m37.BlackScholesResult:
        """Black-Scholes 유럽형 옵션의 가격과 델타, 감마, 베가, 세타, 로를 계산한다. option_type 은 call 또는 put, rate, sigma, dividend_yield 는 연율 소수, time_to_expiry 는 연 단위, 모두 Decimal 문자열이며 결과는 유효숫자 12자리. 베가는 변동성 1.0 당 변화량, 세타는 연 단위이고 미국형 옵션이나 조기행사에는 맞지 않는다."""
        ...
    def bond_duration(self, face: Num, coupon_rate: Num, years: int, ytm: Num, freq: int = 2) -> _m38.BondDurationResult:
        """채권의 맥컬리 듀레이션과 수정 듀레이션을 연 단위로 계산한다. face 는 양수, coupon_rate 와 ytm 은 연율 소수 Decimal 문자열, years 는 만기 연수 정수, freq 는 연 이자지급 횟수(기본 2). 가격은 ytm 으로 현금흐름을 할인해 구하며 반올림하지 않는다. 시장 가격만 알면 먼저 bond_ytm 으로 ytm 을 구한다."""
        ...
    def bond_ytm(self, price: Num, face: Num, coupon_rate: Num, years: int, freq: int = 2, max_iter: int = 100, tol: Num = '1e-10') -> _m38.BondYtmResult:
        """채권 만기수익률(YTM)을 뉴턴법으로 구한다. price 와 face 는 양수 Decimal 문자열, coupon_rate 는 연 표면이율 소수 (예 0.05), years 는 만기 연수 정수, freq 는 연 이자지급 횟수(기본 2). ytm 은 기간 수익률 x freq 인 연율이다. 수렴하지 못하면 converged=false 로 마지막 추정값이 나오므로 확인해야 하며 이자 지급일 사이의 경과이자는 지원하지 않는다."""
        ...
    def cagr(self, beginning_value: Num, ending_value: Num, periods: int, rounding: Num = 'HALF_EVEN', decimals: int = 6) -> _m39.CagrResult:
        """복합연평균성장률(CAGR)을 계산한다. CAGR = (ending_value / beginning_value)^(1 / periods) - 1. beginning_value 는 0보다 크고 ending_value 는 0 이상인 Decimal 문자열, periods 는 1 이상 정수다. 결과는 배수(0.1 = 10%)이며 decimals(기본 6)자리로 rounding(기본 HALF_EVEN) 처리한다."""
        ...
    def forward_price(self, spot: Num, risk_free_rate: Num, time_to_expiry: Num, income_yield: Num = '0') -> _m40.FinanceForwardPriceResult:
        """무차익 선도가격을 계산한다. F = S x exp((r - y) x T), 연속복리 기준이며 income_yield(배당률이나 쿠폰수익률, 기본 0)를 차감한다. spot 은 양수, time_to_expiry 는 0 초과 연 단위, 모두 Decimal 문자열이고 결과는 소수 8자리. 이산복리 이율은 연속복리로 환산해서 넣어야 한다."""
        ...
    def futures_price(self, spot: Num, risk_free_rate: Num, time_to_expiry: Num, dividend_yield: Num = '0') -> _m40.FinanceFuturesPriceResult:
        """연속복리 보유비용 모형의 선물 이론가격을 계산한다. F = S x exp((r - q) x T). spot 은 양수, risk_free_rate 와 dividend_yield(q, 기본 0)는 연속복리 연율, time_to_expiry 는 0 초과 연 단위, 모두 Decimal 문자열. 결과는 소수 8자리. 이산복리 이율을 그대로 넣으면 값이 어긋난다."""
        ...
    def fv(self, present_value: Num, rate: Num, periods: int, rounding: Num = 'HALF_EVEN', decimals: int = 2) -> _m41.FvResult:
        """현재 금액의 미래가치를 계산한다. FV = PV x (1+r)^n, 기간마다 복리. present_value 와 rate(기간당 이율, 0 이상, 예 0.05)는 Decimal 문자열, periods 는 1 이상 정수. decimals(기본 2)자리로 rounding(기본 HALF_EVEN) 처리한다. 연이율과 월 단위 기간 수처럼 단위가 다른 값을 섞어 넣지 않는다."""
        ...
    def irr(self, cashflows: list[Num], guess: Num = '0.1', max_iter: int = 100, tol: Num = '1e-10') -> _m39.IrrResult:
        """내부수익률(IRR), 즉 NPV 를 0 으로 만드는 기간 수익률을 구한다. cashflows 는 2개 이상이며 index 0 이 t=0, 양수와 음수가 모두 있어야 한다. 뉴턴법이 실패하면 -0.99 이상 10 이하 구간 이분법을 쓰고 max_iter 는 10000 이하. 해를 못 찾으면 irr=null, converged=false 를 돌려준다. 월별 현금흐름의 결과는 연율이 아니라 월 수익률이다."""
        ...
    def loan_schedule(self, principal: Num, annual_rate: Num, months: int, method: Num = 'EQUAL_PAYMENT', rounding: Num = 'HALF_EVEN', decimals: int = 0) -> _m42.LoanScheduleResult:
        """대출 상환 스케줄을 계산한다. method 는 EQUAL_PAYMENT(원리금균등, 기본) 또는 EQUAL_PRINCIPAL(원금균등). annual_rate 는 연이율 소수(예 0.03)이며 월이율 = 연이율 / 12, months 는 1 이상 1200 이하 정수. decimals(기본 0)자리로 rounding(기본 HALF_EVEN) 처리하고 마지막 회차가 잔액을 정리한다. 원금균등은 monthly_payment 가 null 이다. 거치기간과 중도상환은 지원하지 않는다."""
        ...
    def npv(self, rate: Num, cashflows: list[Num], rounding: Num = 'HALF_EVEN', decimals: int = 2) -> _m39.NpvResult:
        """순현재가치를 계산한다. NPV = sum(CF_t / (1+r)^t). cashflows 의 index 0 은 t=0 시점이라 할인하지 않으며 초기 투자는 음수로 넣는다. rate 는 기간당 할인율(0 이상 Decimal 문자열), decimals(기본 2)자리로 rounding(기본 HALF_EVEN) 처리한다. 첫 현금흐름을 1기 말로 보려면 앞에 0 을 추가한다."""
        ...
    def option_payoff(self, option_type: Num, strike: Num, spot_path: list[Num], is_call: bool = True, barrier: Num | None = None, barrier_type: Num | None = None, digital_cash: Num = '1') -> _m40.FinanceOptionPayoffResult:
        """옵션의 만기 payoff 를 계산한다. option_type 은 vanilla, digital(현금 지급), asian(산술평균), barrier(up_in, up_out, down_in, down_out). spot_path 는 기초자산 가격 문자열 목록이며 vanilla 와 digital 은 마지막 값만 쓴다. barrier 유형은 barrier 와 barrier_type 이 필수이고 결과는 소수 8자리. 만기 가치일 뿐 프리미엄이 아니다."""
        ...
    def payback_period(self, cashflows: list[Num], rounding: Num = 'HALF_EVEN', decimals: int = 6) -> _m39.PaybackPeriodResult:
        """단순 투자회수기간을 계산한다. cashflows 의 index 0 은 음수인 초기 투자이고 이후 값은 기간별 현금흐름이다. 누적 현금흐름이 처음 0 이상이 되는 기간 안에서 선형 보간하며, 회수되지 않으면 payback_period=null 과 recovered=false 를 반환한다. 화폐의 시간가치는 반영하지 않으며 decimals(기본 6)자리로 rounding(기본 HALF_EVEN) 처리한다."""
        ...
    def pv(self, future_value: Num, rate: Num, periods: int, rounding: Num = 'HALF_EVEN', decimals: int = 2) -> _m41.PvResult:
        """미래 현금흐름의 현재가치를 계산한다. PV = FV / (1+r)^n. future_value 와 rate(기간당 이율, 0 이상, 예 0.05)는 Decimal 문자열, periods 는 1 이상 정수. decimals(기본 2)자리로 rounding(기본 HALF_EVEN) 처리한다. 연이율과 월 단위 기간 수처럼 단위가 다른 값을 섞어 넣지 않는다."""
        ...
    def roi(self, net_profit: Num, investment_cost: Num, rounding: Num = 'HALF_EVEN', decimals: int = 4) -> _m39.RoiResult:
        """투자수익률(ROI)을 계산한다. ROI = net_profit / investment_cost. net_profit 은 손실이면 음수인 Decimal 문자열이고 investment_cost 는 0보다 커야 한다. 결과는 배수(0.25 = 25%)이며 decimals(기본 4)자리로 rounding(기본 HALF_EVEN) 처리한다. 기간을 반영한 연환산 수익률은 아니다."""
        ...
    def sharpe_ratio(self, returns: list[Num], risk_free_rate: Num = '0', periods_per_year: int = 0) -> _m43.FinanceSharpeRatioResult:
        """샤프지수 = (평균수익률 - 무위험수익률) / 표본표준편차(n-1)를 계산한다. returns 는 기간 수익률 문자열 목록(2개 이상), risk_free_rate 는 같은 기간 단위(기본 0), periods_per_year 가 0 보다 크면 sqrt(periods_per_year)를 곱해 연환산한다. 표준편차가 0 이면 오류, 결과는 소수 8자리. 연 무위험수익률을 일간 수익률에서 그대로 빼지 않는다."""
        ...
    def sortino_ratio(self, returns: list[Num], risk_free_rate: Num = '0', periods_per_year: int = 0) -> _m43.FinanceSortinoRatioResult:
        """소르티노 비율 = (평균수익률 - 무위험수익률) / 하방편차를 계산한다. 하방편차 = sqrt(mean(min(r - rf, 0)^2)), 평균은 전체 표본 수로 나눈다. returns 는 기간 수익률 문자열 목록(2개 이상), risk_free_rate 는 같은 기간 단위(기본 0), periods_per_year 가 0 보다 크면 연환산. 하방편차가 0 이면 오류, 결과는 소수 8자리."""
        ...
    def var_historical(self, returns: list[Num], confidence: Num = '0.95') -> _m43.FinanceVarHistoricalResult:
        """과거 수익률의 경험적 분위수로 VaR 와 CVaR(기대부족액)을 계산한다. returns 는 기간 수익률 문자열 목록(2개 이상), confidence 는 0 초과 1 미만(기본 0.95)이며 분위수는 선형보간한다. 손실을 양수로 나타낸 소수 8자리 값이고 분포 가정은 없다. 표본이 적으면 꼬리 추정이 불안정하다."""
        ...
    def var_parametric(self, returns: list[Num], confidence: Num = '0.95') -> _m43.FinanceVarParametricResult:
        """정규분포를 가정한 모수적 VaR 와 CVaR 를 계산한다. 표본 평균과 표본표준편차(n-1)로 VaR = -(mu + z x sigma). returns 는 기간 수익률 문자열 목록(2개 이상), confidence 는 0 초과 1 미만(기본 0.95). 손실을 양수로 나타낸 소수 8자리 값. 꼬리가 두꺼운 분포에서는 손실을 작게 추정하므로 var_historical 과 비교한다."""
        ...


class _GeometryTools(Protocol):
    def area_circle(self, radius: Num) -> _m44.AreaCircleResult:
        """원의 넓이 π * r² 를 계산한다. radius 는 0 이상 Decimal 문자열이며 단위는 자유(결과는 그 단위의 제곱). π 는 mpmath 50자리로 계산하고 유효숫자 30자리 문자열로 반환한다. 지름을 radius 로 넣으면 4배 큰 값이 나오므로 반지름을 넣는다."""
        ...
    def area_polygon(self, vertices: list[list[Num]]) -> _m44.AreaPolygonResult:
        """다각형 넓이를 신발끈 공식(Shoelace)으로 계산한다. vertices 는 [[x, y], ...] 형태 Decimal 문자열 좌표이고 꼭짓점 3개 이상을 변을 따라 순서대로 준다. 마지막 점은 첫 점과 자동으로 이어지며 결과는 항상 0 이상이다. 변이 서로 교차하거나 점 순서가 뒤섞이면 실제 면적과 다르다."""
        ...
    def area_rectangle(self, width: Num, height: Num) -> _m44.AreaRectangleResult:
        """직사각형 넓이 width * height 를 Decimal 로 계산한다. 두 값은 0 이상 Decimal 문자열이며 단위는 같아야 하고 float 를 거치지 않는다. 대각선 길이나 둘레를 넣으면 의미 없는 값이 나온다. 정사각형은 두 값에 같은 변 길이를 넣는다."""
        ...
    def area_triangle(self, base: Num, height: Num) -> _m44.AreaTriangleResult:
        """삼각형 넓이 (base * height) / 2 를 Decimal 로 계산한다. base 는 밑변, height 는 그 밑변에 수직인 높이이며 둘 다 0 이상 Decimal 문자열, 단위는 같아야 한다. float 를 거치지 않는다. 비스듬한 변의 길이를 height 로 넣으면 틀리므로 수직 높이를 넣는다."""
        ...
    def haversine(self, lat1: Num, lon1: Num, lat2: Num, lon2: Num, earth_radius_km: Num = '6371') -> _m45.HaversineResult:
        """하버사인 공식으로 두 지점의 지구 표면 대원 거리(km)를 계산한다. 위도(-90~90)와 경도(-180~180)는 도 단위 Decimal 문자열이고 지구 반지름 기본값은 6371km 다. mpmath 50자리 계산 후 유효숫자 30자리로 반환한다. 구면 근사이므로 실제 도로 거리나 타원체 거리와 다르며 라디안을 넣으면 안 된다."""
        ...
    def matrix_determinant(self, M: list[list[Num]]) -> _m46.MatrixDeterminantResult:
        """정방행렬 M 의 행렬식을 계산한다. M 은 n×n Decimal 문자열 2차원 리스트(n 은 200 이하). n 이 3 이하면 Decimal 로 정확히 전개하고 n 이 4 이상이면 numpy float64 로 계산해 약 15자리 정밀도만 보장한다. 정방행렬이 아니면 오류이며 n≥4 결과는 근사값임에 유의한다."""
        ...
    def matrix_inverse(self, M: list[list[Num]]) -> _m46.MatrixInverseResult:
        """정방행렬의 역행렬을 numpy.linalg.inv(float64)로 계산한다. M 은 n×n Decimal 문자열 2차원 리스트(n 은 200 이하). 결과 원소는 float64 repr 문자열이라 '1e-05' 같은 지수 표기가 나올 수 있고 정밀도는 약 15자리다. 특이행렬이면 오류. 연립방정식 해가 목적이면 역행렬을 곱하지 말고 matrix_solve 를 쓴다."""
        ...
    def matrix_multiply(self, A: list[list[Num]], B: list[list[Num]]) -> _m46.MatrixMultiplyResult:
        """행렬 곱 A @ B 를 Decimal 로 계산한다. A 는 m×k, B 는 k×n 의 Decimal 문자열 2차원 리스트이며 A 의 열 수와 B 의 행 수가 같아야 한다. 행과 열은 각각 200 이하. float 를 거치지 않아 반올림 오차가 없다. 행렬 곱은 교환법칙이 성립하지 않으므로 A @ B 와 B @ A 는 다르다."""
        ...
    def matrix_solve(self, A: list[list[Num]], b: list[Num]) -> _m46.MatrixSolveResult:
        """연립일차방정식 Ax = b 의 해 x 를 numpy.linalg.solve(float64)로 구한다. A 는 n×n Decimal 문자열 2차원 리스트, b 는 길이 n 리스트. 해는 float64 repr 문자열이며 정밀도는 약 15자리다. 특이행렬이거나 b 의 길이가 n 과 다르면 오류. 비정방(과결정, 부족결정) 시스템은 지원하지 않는다."""
        ...
    def vector_cross(self, a: list[Num], b: list[Num]) -> _m47.VectorCrossResult:
        """3차원 벡터의 외적 a × b 를 Decimal 로 계산한다. a, b 는 정확히 3개 원소의 Decimal 문자열 리스트이고 결과도 3개 원소 리스트다. 외적은 순서를 바꾸면 부호가 반대가 되므로 a × b 와 b × a 를 혼동하지 않는다. 2차원 벡터는 z 성분 0 을 직접 채워 넣는다."""
        ...
    def vector_dot(self, a: list[Num], b: list[Num]) -> _m47.VectorDotResult:
        """두 벡터의 내적 Σ a_i * b_i 를 Decimal 로 계산한다. a, b 는 같은 길이의 비어 있지 않은 Decimal 문자열 리스트이며 반올림 없는 정확한 합이다. 길이가 다르면 오류. 3차원 벡터의 직교 방향이 필요하면 vector_cross 를 쓴다."""
        ...
    def vector_norm(self, v: list[Num], p: int = 2) -> _m47.VectorNormResult:
        """벡터의 L-p 노름 (Σ |v_i|^p)^(1/p) 을 계산한다. v 는 비어 있지 않은 Decimal 문자열 리스트, p 는 1 이상의 정수(기본 2, 유클리드 길이). mpmath 50자리 계산 후 유효숫자 30자리로 반환한다. 최댓값 노름(p=∞)과 정수가 아닌 p 는 지원하지 않는다."""
        ...
    def volume_cuboid(self, length: Num, width: Num, height: Num) -> _m48.VolumeCuboidResult:
        """직육면체 부피 length * width * height 를 Decimal 로 계산한다. 세 값은 0 이상 Decimal 문자열이며 같은 길이 단위여야 하고 float 를 거치지 않는다. cm 와 m 처럼 단위를 섞어 넣으면 틀린 값이 나온다."""
        ...
    def volume_cylinder(self, radius: Num, height: Num) -> _m48.VolumeCylinderResult:
        """원기둥 부피 π * r² * h 를 계산한다. radius(밑면 반지름)와 height 는 0 이상 Decimal 문자열이며 같은 길이 단위여야 한다. π 는 mpmath 50자리로 계산하고 유효숫자 30자리 문자열로 반환한다. 지름을 radius 로 넣으면 4배 큰 값이 나온다."""
        ...
    def volume_sphere(self, radius: Num) -> _m48.VolumeSphereResult:
        """구의 부피 (4/3) * π * r³ 를 계산한다. radius 는 0 이상 Decimal 문자열이며 결과 단위는 길이 단위의 세제곱이다. π 는 mpmath 50자리로 계산하고 유효숫자 30자리 문자열로 반환한다. 지름이 아니라 반지름을 넣는다."""
        ...


class _MathTools(Protocol):
    def diff_central(self, expression: Num, x: Num, h: Num = '0.001', variable: Num = 'x') -> _m49.DiffCentralResult:
        """중심 차분 f'(x) ≈ (f(x+h) - f(x-h)) / (2h) 로 x 에서의 1차 도함수를 수치 근사한다. expression 은 core.calc 문법의 수식, variable(기본 x)이 자유 변수, h 는 양수 Decimal 문자열(기본 0.001). float64 계산이며 결과는 유효숫자 12자리다. h 를 지나치게 작게 잡으면 상쇄 오차가 커지고, 도함수 식 자체가 필요하면 symbolic.diff 를 쓴다."""
        ...
    def diff_five_point(self, expression: Num, x: Num, h: Num = '0.001', variable: Num = 'x') -> _m49.DiffFivePointResult:
        """5점 공식 f'(x) ≈ (-f(x+2h) + 8 f(x+h) - 8 f(x-h) + f(x-2h)) / (12 h) 로 x 에서의 1차 도함수를 수치 근사한다. 중심 차분보다 정확도가 높다(O(h⁴)). expression 은 core.calc 문법, h 는 양수(기본 0.001), float64 계산이며 유효숫자 12자리다. x±2h 구간에서 정의되지 않는 함수에는 쓸 수 없다."""
        ...
    def fft(self, samples: list[Num]) -> _m50.FftResult:
        """실수 샘플의 이산 푸리에 변환(DFT)을 numpy.fft 로 계산한다. samples 는 2개 이상 65536개 이하의 Decimal 문자열 리스트. 각 bin 은 k, magnitude, phase_rad 를 담으며 float64 계산에 유효숫자 12자리이고 1/N 정규화는 하지 않는다. k 는 주파수가 아니라 인덱스이므로 Hz 는 k * 샘플링주파수 / N 으로 직접 계산한다."""
        ...
    def ifft(self, bins: list[dict[str, Num]], real_output: bool = True) -> _m50.IfftResult:
        """fft 결과의 bin 리스트({magnitude, phase_rad})에서 시간 영역 샘플을 복원한다(1/N 정규화 포함). 최대 65536개. real_output 기본 true 는 허수부 절대값이 1e-9 를 넘으면 오류를 내고 문자열 리스트를 반환하며, false 면 {real, imag} 쌍을 반환한다. bin 은 N개 전체를 순서대로 넣어야 하며 일부만 넣으면 다른 신호가 복원된다."""
        ...
    def integrate_gauss_legendre(self, expression: Num, a: Num, b: Num, degree: int = 20, variable: Num = 'x') -> _m51.IntegrateGaussLegendreResult:
        """가우스-르장드르 구적법(mpmath.quadgl)으로 정적분 ∫_a^b f(x) dx 의 근삿값을 구한다. expression 은 core.calc 문법, a 와 b 는 a < b 인 Decimal 문자열, degree 는 2 이상 100 이하(기본 20). 피적분 함수는 float64 로 평가하고 결과는 유효숫자 12자리다. 매끄러운 함수에 적합하며 불연속이 있는 구간은 나누어 적분한다."""
        ...
    def integrate_simpson(self, expression: Num, a: Num, b: Num, n: int = 100, variable: Num = 'x') -> _m51.IntegrateSimpsonResult:
        """합성 심프슨 1/3 법으로 정적분 ∫_a^b f(x) dx 의 근삿값을 구한다. expression 은 core.calc 문법, a 와 b 는 a < b 인 Decimal 문자열, 부구간 수 n 은 2 이상 20000 이하의 짝수(기본 100). float64 계산이며 유효숫자 12자리다. 하한이 상한보다 크면 오류이므로 부호를 직접 뒤집어야 하고, 특이점이 있는 구간은 정확하지 않다."""
        ...
    def interpolate_cubic_spline(self, xs: list[Num], ys: list[Num], x_query: Num, bc_type: Num = 'natural') -> _m52.InterpolateCubicSplineResult:
        """3차 스플라인 보간(scipy CubicSpline)으로 x_query 에서의 값을 구한다. xs 는 엄격히 증가하는 4개 이상의 Decimal 문자열 리스트, ys 는 같은 길이. bc_type 은 natural(기본), clamped, not-a-knot 중 하나. x_query 가 표본 구간 밖이면 외삽하지 않고 오류를 낸다. 유효숫자 12자리."""
        ...
    def interpolate_linear(self, xs: list[Num], ys: list[Num], x_query: Num) -> _m52.InterpolateLinearResult:
        """표본점 (xs, ys) 를 직선으로 이어 x_query 에서의 값을 구하는 1차원 선형 보간이다. xs 는 엄격히 증가하는 2개 이상의 Decimal 문자열 리스트, ys 는 같은 길이. x_query 가 [min(xs), max(xs)] 밖이면 외삽하지 않고 오류를 낸다. float64 계산, 유효숫자 12자리."""
        ...
    def polynomial_horner(self, coefficients: list[Num], x: Num) -> _m53.PolynomialHornerResult:
        """호너 방법으로 다항식 P(x) 를 Decimal 로 평가한다. coefficients 는 높은 차수부터 내림차순(예 [1, 0, -4] 는 x² - 4), x 는 Decimal 문자열이다. float 를 거치지 않으며 degree 도 함께 반환한다. 계수를 오름차순으로 넣으면 다른 다항식이 평가된다."""
        ...
    def polynomial_roots(self, coefficients: list[Num]) -> _m53.PolynomialRootsResult:
        """다항식의 모든 근(복소근 포함)을 numpy.roots 로 구한다. coefficients 는 높은 차수부터 내림차순 Decimal 문자열 리스트(예 [1, 0, -4] 는 x² - 4)이며 1차 이상 256차 이하, 최고차 계수는 0 이 아니어야 한다. 각 근은 {real, imag} 12자리 문자열이고 정렬되어 있지 않다. 오름차순으로 넣으면 다른 다항식이 되며 중근이 많으면 정밀도가 떨어진다."""
        ...


class _MedicalTools(Protocol):
    def bmi(self, height_m: Num, weight_kg: Num) -> _m54.MedicalBmiResult:
        """체질량지수(BMI)를 계산하고 WHO 기준으로 분류한다. BMI = weight_kg / height_m^2, 입력은 미터와 킬로그램의 Decimal 문자열, 결과는 소수 2자리 HALF_EVEN 반올림. 분류는 underweight(<18.5), normal(<25), overweight(<30), obese_1(<35), obese_2(<40), obese_3(40 이상)이며 반올림한 값으로 판정한다. 신장을 cm 단위로 넣으면 결과가 100배 이상 어긋난다."""
        ...
    def bsa(self, height_cm: Num, weight_kg: Num, method: Num = 'dubois') -> _m54.MedicalBsaResult:
        """체표면적(BSA)을 m² 단위로 계산한다. 입력은 신장 cm, 체중 kg의 Decimal 문자열, 결과는 소수 4자리 HALF_EVEN 반올림. method=dubois(기본)는 0.007184 * h^0.725 * w^0.425, method=mosteller는 sqrt(h*w/3600). 항암제 용량 산정 등에 쓰며, 신장을 m 단위로 넣으면 결과가 크게 어긋난다. 비정수 지수는 float64로 계산한다."""
        ...
    def cha2ds2_vasc(self, age: int, female: bool, chf: bool = False, hypertension: bool = False, diabetes: bool = False, stroke_or_tia: bool = False, vascular_disease: bool = False) -> _m55.Cha2ds2VascResult:
        """심방세동 환자의 뇌졸중 위험 점수 CHA2DS2-VASc를 계산한다. C=울혈성심부전, H=고혈압, A2=75세 이상(2점), D=당뇨, S2=뇌졸중/TIA(2점), V=혈관질환, A=65~74세(1점), Sc=여성. 총 0~9점이며 risk_level은 0점 low, 1점 moderate, 2점 이상 high. age는 0~130 정수, 나머지는 bool이어야 하고 문자열 'true'는 거부한다. 판단 보조용이며 임상 결정을 대신하지 않는다."""
        ...
    def dose_weight_based(self, weight_kg: Num, dose_per_kg: Num, max_dose: Num | None = None, unit: Num = 'mg') -> _m56.MedicalDoseWeightBasedResult:
        """체중 기반 약물 용량을 계산한다. dose = weight_kg * dose_per_kg, max_dose를 주면 초과 시 max_dose로 제한하고 capped=true를 돌려준다. 입력은 kg과 kg당 용량의 Decimal 문자열(0 이상), 결과는 소수 4자리 HALF_EVEN 반올림 후 후행 0을 제거한 고정소수점 문자열. unit은 표시용 문자열이며 환산하지 않는다. 단위가 다른 dose_per_kg와 max_dose를 섞으면 안 된다."""
        ...
    def egfr(self, creatinine_mg_dl: Num, age: int, sex: Num, race: Num = 'non_black') -> _m57.MedicalEgfrResult:
        """혈청 크레아티닌으로 추정 사구체여과율(eGFR)을 CKD-EPI 2021(인종 계수 없음) 식으로 계산하고 KDIGO 2012 CKD 병기(G1~G5)를 돌려준다. 입력은 mg/dL Decimal 문자열, 정수 나이, sex=male|female. 결과 단위는 mL/min/1.73m², 소수 1자리 HALF_EVEN 반올림이며 병기는 반올림한 값으로 정한다. race 인자는 무시된다. 시스타틴 C 기반 식이나 소아 식에는 쓸 수 없다."""
        ...
    def framingham_cvd_10y(self, sex: Num, age: int, total_chol: Num, hdl: Num, sbp: Num, treated_htn: bool, smoker: bool, diabetes: bool) -> _m55.FraminghamCvd10yResult:
        """Framingham 일반 10년 심혈관질환 발생 확률을 계산한다(D'Agostino 2008 일반 CVD 모델). sex=male|female, age 30~74 정수, total_chol과 hdl은 mg/dL, sbp는 mmHg(모두 Decimal 문자열), treated_htn, smoker, diabetes는 bool. risk는 0~1 확률(유효숫자 10자리), risk_pct는 백분율이다. 범위를 벗어난 나이에는 쓸 수 없다. float64 로그 회귀식이라 Decimal 정확 연산이 아니다."""
        ...
    def has_bled(self, hypertension: bool, abnormal_renal: bool, abnormal_liver: bool, stroke: bool, bleeding_history: bool, labile_inr: bool, elderly: bool, drugs: bool, alcohol: bool) -> _m55.HasBledResult:
        """항응고 치료 환자의 주요 출혈 위험 점수 HAS-BLED를 계산한다. H=고혈압, A=신장 또는 간 기능 이상(각 1점), S=뇌졸중, B=출혈력, L=불안정 INR, E=고령(65세 초과), D=약물 또는 음주(각 1점). 총 0~9점이며 risk_level은 2점 이하 low, 3점 이상 high. 아홉 항목을 모두 bool로 넣어야 하며 기본값이 없다. 판단 보조용이다."""
        ...
    def pregnancy_weeks(self, lmp_date: Num, reference_date: Num | None = None) -> _m58.MedicalPregnancyWeeksResult:
        """최종 월경일(LMP)로 임신 주수와 분만예정일(EDD)을 계산한다. 입력은 YYYY-MM-DD 문자열이며 reference_date를 생략하면 서버의 오늘 날짜를 쓴다. EDD = LMP + 280일(Naegele 법칙), 주수와 일수는 0~42주로 제한하고 삼분기(1~3)도 함께 반환한다. 초음파 계측으로 조정한 예정일은 반영하지 않는다."""
        ...
    def qtc_bazett(self, qt: Num, rr: Num, unit: Num = 'ms') -> _m59.QtcResult:
        """Bazett 공식으로 QT 간격을 심박수에 맞춰 보정한다. QTc = QT / sqrt(RR). qt와 rr은 Decimal 문자열이며 unit='ms'(기본) 또는 's'로 둘 다 같은 단위로 넣고, 결과 단위도 같다. 내부는 mpmath 40자리로 계산해 유효숫자 20자리 문자열로 돌려준다(반올림 소수 자릿수 고정 없음). 빠른 심박(RR 짧음)에서는 과대 보정되므로 그 구간엔 Fridericia를 고려한다."""
        ...
    def qtc_framingham(self, qt: Num, rr: Num, unit: Num = 'ms') -> _m59.QtcResult:
        """Framingham 선형 공식으로 QT 간격을 보정한다. QTc = QT + 0.154 * (1 - RR_초). qt와 rr은 Decimal 문자열이며 unit='ms'(기본) 또는 's'로 둘 다 같은 단위로 넣고, 내부에서 초로 환산해 계산한 뒤 입력 단위로 돌려준다. Decimal 정확 연산이며 반올림하지 않는다. RR을 심박수(bpm)로 넣으면 안 된다."""
        ...
    def qtc_fridericia(self, qt: Num, rr: Num, unit: Num = 'ms') -> _m59.QtcResult:
        """Fridericia 공식으로 QT 간격을 심박수에 맞춰 보정한다. QTc = QT / RR^(1/3). qt와 rr은 Decimal 문자열이며 unit='ms'(기본) 또는 's'로 둘 다 같은 단위로 넣고, 결과 단위도 같다. 내부는 mpmath 40자리로 계산해 유효숫자 20자리 문자열로 돌려준다. RR을 심박수(bpm)로 넣으면 안 된다. RR은 R-R 간격 시간이다."""
        ...
    def qtc_hodges(self, qt: Num, rr: Num, unit: Num = 'ms') -> _m59.QtcHodgesResult:
        """Hodges 공식으로 QT 간격을 심박수에 맞춰 보정한다. QTc_ms = QT_ms + 1.75 * (HR - 60), HR = 60 / RR_초. qt와 rr은 Decimal 문자열이며 unit='ms'(기본) 또는 's'로 둘 다 같은 단위로 넣고, 결과는 입력 단위로 돌려주며 계산에 쓴 심박수 hr_bpm도 함께 반환한다. Decimal 연산이며 반올림하지 않는다. RR 대신 심박수를 넣으면 안 된다."""
        ...


class _PayrollTools(Protocol):
    def hourly_to_monthly_net(self, hourly_wage: Num, year: int, monthly_hours: Num = '209', meal_allowance: Num = '0', num_dependents: int = 1, children_8_20: int = 0, *, as_of: Num | None = None, include_proposed: bool = False) -> _m60.HourlyToMonthlyNetResult:
        """시급(원, 문자열)을 월 환산시간(기본 209시간, 주 40시간과 주휴 포함)에 곱해 월급으로 바꾸고 원 미만을 버린 뒤 payroll.kr_salary 로 4대보험과 간이세액표 소득세를 공제한 실수령액을 구한다. 식대 비과세 한도, 공제대상가족 수, 8~20세 자녀 수(children_8_20)를 받는다. 주 40시간이 아닌 근로는 monthly_hours 를 직접 줘야 한다."""
        ...
    def kr_bonus_tax(self, bonus_amount: Num, monthly_salary: Num, year: int, dependents: int = 1, method: Num = 'averaging', payment_period_months: int = 12, children_8_20: int = 0, *, as_of: Num | None = None, include_proposed: bool = False) -> _m61.KrBonusTaxResult:
        """상여금 원천징수세액을 근로소득 간이세액표로 구한다. method=averaging(기본, 소득세법 제136조제1항제1호)은 상여를 지급대상기간 월수(1~12, 기본 12)로 안분해 월급여에 더한 간이세액에서 월급여 간이세액을 빼고 월수를 곱하며, simple 은 1개월분으로 본다. 금액은 원 문자열이고 세액은 원 미만 버림이다. 비과세 상여는 빼고 넣어야 한다."""
        ...
    def kr_donation_deduction(self, earned_income: Num, year: int, legal_donation: Num = '0', designated_donation: Num = '0', political_donation: Num = '0', religious_donation: Num = '0', carryover_loss: Num = '0', hometown_donation: Num = '0', esop_donation: Num = '0', *, as_of: Num | None = None, include_proposed: bool = False) -> _m62.KrDonationDeductionResult:
        """기부금 세액공제(소득세법 제59조의4제4항, 조세특례제한법 제76조)를 구한다. 근로소득금액(원 문자열) 기준 한도 안에서 특례·일반기부금 합계 1천만원 이하 15%, 초과 30%(특례 먼저), 정치자금 10만원까지 110분의 100과 초과분 15%(3천만원 초과분 25%)를 적용하고 원 미만 버린다. 고향사랑·우리사주 기부금은 한도 순서에만 반영하며 공제액은 계산하지 않는다. 종교단체 기부는 religious_donation 에 따로 넣어야 한다."""
        ...
    def kr_education_deduction(self, expenses: dict[str, Num], year: int, counts: dict[str, int] | None = None, *, as_of: Num | None = None, include_proposed: bool = False) -> _m63.KrEducationDeductionResult:
        """교육비 세액공제(소득세법 제59조의4제3항)를 구한다. expenses 는 self, preschool, elementary, middle_high, university, disabled_special 별 지출액(원 문자열), counts 는 범주별 인원이다. 공제율 15%를 정책의 인당 한도(영유아·초중고 300만원, 대학 900만원, 본인·장애인 특수교육 무한도)에 인원을 곱한 한도까지 적용해 원 미만 버린다. 여러 자녀 지출을 한 범주에 합치고 counts 를 생략하면 1명분 한도만 적용된다."""
        ...
    def kr_gross_from_net(self, net_monthly: Num, year: int, meal_allowance: Num = '0', num_dependents: int = 1, children_8_20: int = 0, *, as_of: Num | None = None, include_proposed: bool = False) -> _m64.KrGrossFromNetResult:
        """역산: 세후 월급(net_monthly, 원 문자열)에서 세전 월급을 구한다. payroll.kr_salary 의 실수령액이 목표 이상이 되는 가장 작은 정수 월급을 공제 합계의 고정점 반복으로 찾고, 달성한 실수령액과 차이(residual)를 함께 반환한다. 정확히 같은 실수령액이 불가능한 목표도 있으니 exact 를 확인하고, 연봉이 아닌 월 단위 실수령액을 넣어야 한다."""
        ...
    def kr_health_income_premium(self, year: int, interest_income: Num = '0', dividend_income: Num = '0', business_income: Num = '0', wage_income: Num = '0', pension_income: Num = '0', other_income: Num = '0', annual_remuneration_total: Num | None = None, start_month: int = 1, end_month: int = 12, health_premium_paid: Num | None = None, ltc_premium_paid: Num | None = None, *, as_of: Num | None = None, include_proposed: bool = False) -> _m65.KrHealthIncomePremiumResult:
        """건강보험 직장가입자의 보수 외 소득월액보험료(국민건강보험법 제71조: 연 2천만원 초과분의 1/12, 근로·연금소득 50% 평가, 이자·배당 1천만원 이하 제외, 월 상한 4,591,740원)와 장기요양보험료, 보수총액 기준 보수월액보험료 연간 정산 차액과 분할납부 가능 여부를 계산한다. 소득은 소득 종류별 연간 소득금액(원 문자열), year 는 부과 또는 보수 귀속 연도, 원 미만 버림. 지역가입자 보험료 계산에 쓰면 오용이다."""
        ...
    def kr_housing_loan_deduction(self, interest_paid: Num, term_years: int, is_fixed_rate: bool, is_non_grace: bool, year: int, *, as_of: Num | None = None, include_proposed: bool = False) -> _m66.KrHousingLoanDeductionResult:
        """장기주택저당차입금 이자상환액 소득공제(소득세법 제52조제5항·제6항)의 공제 대상액을 구한다. 이자상환액(원 문자열), 상환기간(년), 고정금리와 비거치식 여부로 한도(15년 이상 고정금리+비거치식 2천만원 등)를 정해 그 이하만 인정하며, 10년 미만과 10~15년 변동·거치식은 0이다(limit_key 는 빈 문자열). 소득공제액이지 세액이 아니므로 세율을 곱해야 한다."""
        ...
    def kr_medical_deduction(self, gross_income: Num, general_medical: Num, year: int, special_medical: Num = '0', infertility: Num = '0', premature: Num = '0', *, as_of: Num | None = None, include_proposed: bool = False) -> _m67.KrMedicalDeductionResult:
        """의료비 세액공제(소득세법 제59조의4제2항)를 구한다. 총급여(원 문자열)의 3% 미달분을 일반, 특수, 미숙아, 난임 순으로 차감한 뒤 일반 의료비 15%(연 700만원 한도), 본인·6세 이하·65세 이상·장애인 등 특수 15%(한도 없음), 미숙아 20%, 난임 30%를 적용하고 원 미만 버린다. 본인·65세 이상 의료비를 일반에 넣으면 700만원 한도가 걸린다."""
        ...
    def kr_minimum_wage_check(self, wage_amount: Num, year: int, wage_unit: Num = 'monthly', weekly_contract_hours: Num = '40', daily_contract_hours: Num | None = None, weekly_paid_hours: Num | None = None, monthly_standard_hours: Num | None = None, monthly_bonus: Num = '0', monthly_welfare_cash: Num = '0', on_probation: bool = False, contract_one_year_or_more: bool = False, simple_labor_job: bool = False, *, as_of: Num | None = None, include_proposed: bool = False) -> _m68.MinimumWageCheckResult:
        """한국 최저임금 충족 여부를 검토한다(최저임금법 제5조·제6조, 시행령 제5조, 연도별 고시). wage_amount 는 wage_unit 단위의 매월 정기 지급 소정근로 임금(원)이고 월급은 주 40시간이면 209시간으로 시급 환산한다. 매월 주는 상여금과 현금 복리후생비는 산입 제외 비율(2024년부터 0%)을 빼고 더하며, 수습 감액 10%는 세 요건을 모두 줄 때만 적용한다. 비교는 정밀 값이고 부족액은 원 미만 올림이다. 연장·휴일·야간 수당, 연차 미사용수당, 현물 복리후생, 1개월 초과 주기 상여는 넣지 않는다. 도급제, 택시 운전, 적용 제외 인가는 다루지 않는다."""
        ...
    def kr_national_pension_benefit(self, year: int, contribution_months: int | None = None, b_value: Num | None = None, monthly_income: Num | None = None, income_history: list[dict[str, Any]] | None = None, contribution_end_year: int | None = None, claim_offset_months: int = 0, deferral_ratio: Num = '1', dependent_spouse: bool = False, dependent_children_parents: int = 0, *, as_of: Num | None = None, include_proposed: bool = False) -> _m69.KrNationalPensionBenefitResult:
        """국민연금 노령연금 예상액을 국민연금법 제51조 기본연금액 산식(A값, 구간별 비례상수 2.4~1.29, 20년 초과 연 5% 가산), 제63조 가입기간별 지급률, 조기수령 월 0.5% 감액(최대 60개월), 연기 월 0.6% 가산(최대 60개월), 부양가족연금으로 계산한다. year 는 지급 개시 연도, 금액은 원 문자열, B는 b_value·monthly_income(현재 소득 유지 가정)·income_history(재평가율 적용) 중 하나. 월 지급액은 10원 미만 버리고 제53조 최고한도(평균 기준소득월액)를 적용한다. 크레딧과 재직자 감액은 빠지므로 공단 확정 연금액 대용으로 쓰면 오용이다."""
        ...
    def kr_overtime_pay(self, ordinary_wage: Num, year: int, employee_count: int, wage_unit: Num = 'hourly', overtime_hours: Num = '0', night_hours: Num = '0', holiday_hours_by_day: list[Num] | None = None, weekly_contract_hours: Num = '40', daily_contract_hours: Num | None = None, weekly_paid_hours: Num | None = None, monthly_standard_hours: Num | None = None, *, as_of: Num | None = None, include_proposed: bool = False) -> _m70.OvertimePayResult:
        """한국 연장·야간·휴일근로수당을 계산한다(근로기준법 제56조, 시행령 제6조). ordinary_wage 는 통상임금(원)이고 wage_unit 으로 시급·일급·주급·월급을 고른다(월급은 주 40시간이면 209시간으로 환산). 시간은 Decimal 문자열이며 휴일근로는 하루별 목록으로 받아 8시간 이내 50%, 초과 100%를, 연장 50%와 야간(22~06시) 50%는 겹치면 더한다. employee_count 4명 이하는 가산 없이 근로시간분만 주고 금액은 원 미만 올림이다. 휴일근로 시간을 overtime_hours 에도 넣으면 이중 가산이다."""
        ...
    def kr_salary(self, monthly_salary: Num, year: int, meal_allowance: Num = '0', num_dependents: int = 1, children_8_20: int = 0, *, as_of: Num | None = None, include_proposed: bool = False) -> _m71.KrSalaryResult:
        """세전 월급(원, 문자열)에서 한국 실수령액을 구한다. 비과세 식대 한도를 뺀 과세급여로 4대보험 근로자 부담분(국민연금 상·하한, 건강보험, 장기요양, 고용보험)과 근로소득 간이세액표 소득세, 지방소득세(소득세의 10%)를 공제하며 건강보험과 장기요양은 10원 미만 버림, 그 밖의 보험료와 지방소득세는 원 미만 버림이다. 시행일별 정책을 as_of 로 고른다. 연봉을 월급 자리에 넣으면 안 된다."""
        ...
    def kr_severance_pay(self, severance_amount: Num, service_years: Num, year: int, non_taxable: Num = '0', *, as_of: Num | None = None, include_proposed: bool = False) -> _m72.KrSeverancePayResult:
        """퇴직소득세(소득세법 제48조·제55조)를 구한다. 퇴직급여총액, 근속연수(년, 소수 가능), 비과세액(원 문자열)에서 근속연수공제, 환산급여(12배 후 근속연수로 나눔)공제, 기본세율 누진을 적용하고 근속연수 비율로 환원해 원 단위 반올림한다. 1년 미만 끝수는 1년으로 올려 쓰며 지방소득세는 포함하지 않는다. 근속연수를 개월 수로 넣으면 안 된다."""
        ...
    def kr_weekly_holiday_pay(self, weekly_contract_hours: Num, hourly_ordinary_wage: Num, year: int, perfect_attendance: bool = True, employed_through_week: bool = True, regular_worker_weekly_days: int = 5, *, as_of: Num | None = None, include_proposed: bool = False) -> _m73.WeeklyHolidayPayResult:
        """한국 주휴수당을 계산한다(근로기준법 제55조제1항·제18조제3항, 시행령 제30조·별표 2). weekly_contract_hours 는 4주 평균 1주 소정근로시간, hourly_ordinary_wage 는 시간급 통상임금(원)이다. 15시간 이상, 소정근로일 개근, 그 주까지 근로관계 존속이면 주휴시간 = min(주 소정근로시간 / 통상 근로자 주 소정근로일 수, 8)에 시급을 곱하고 원 미만은 올린다. 시급제·일급제 근로자용이며 주휴분이 이미 포함된 월급에 더하면 이중 계산이다."""
        ...
    def kr_year_end_tax_settlement(self, annual_gross: Num, prepaid_tax: Num, year: int, dependents: int = 1, extra_deductions: Num = '0', extra_tax_credits: Num = '0', *, as_of: Num | None = None, include_proposed: bool = False) -> _m74.KrYearEndTaxSettlementResult:
        """연말정산 환급 또는 추가납부액을 간이 모델로 구한다. 연간 총급여에서 근로소득공제, 인당 기본공제, 추가 소득공제를 뺀 과세표준에 소득세 누진세율을 적용하고 근로소득세액공제, 표준세액공제 13만원, 추가 세액공제를 차감해 결정세액(원 미만 버림)을 낸 뒤 기납부세액과 비교한다. 의료비·교육비·기부금은 각 도구로 따로 구해 extra_* 로 넣어야 한다."""
        ...


class _PmTools(Protocol):
    def critical_path(self, tasks: list[dict[str, Any]]) -> _m75.CriticalPathResult:
        """작업 의존 관계로 주공정법(CPM) 일정을 계산해 각 작업의 ES, EF, LS, LF, 여유(slack)와 총 기간, 여유가 0인 주공정 작업 목록을 돌려준다. tasks는 {id, duration(Decimal 문자열, 0 이상, 단위 통일), predecessors(선행 id 목록)}의 리스트이며 결과는 위상 정렬 순서다. 반올림하지 않는다. 순환 의존이나 없는 선행 id는 오류이고, 작업 간 지연(lag)과 시작 제약은 지원하지 않는다."""
        ...
    def earned_schedule(self, pv_timeline: list[dict[str, Num]], earned_value: Num, actual_time: Num, planned_duration: Num) -> _m76.EarnedScheduleResult:
        """획득일정(Earned Schedule) 지표를 계산한다. ES는 획득가치(EV)에 해당하는 계획 시점으로 pv_timeline을 선형 보간해 역산하고, SPI(t)=ES/AT, TSPI(t)=(PD-ES)/(PD-AT), IEAC(t)=PD/SPI(t). pv_timeline은 [{time, cumulative_pv}] 시간 오름차순에 누적 PV 비감소이며 모든 수는 Decimal 문자열, 시간 단위를 통일한다. AT와 PD는 양수여야 하고 PD와 AT가 같으면 TSPI는 0을 돌려준다. 반올림하지 않는다."""
        ...
    def evm(self, pv: Num, ev: Num, ac: Num, bac: Num) -> _m77.EvmResult:
        """획득가치관리(EVM) 지표를 계산한다. SPI=EV/PV, CPI=EV/AC, SV=EV-PV, CV=EV-AC, EAC=BAC/CPI, ETC=EAC-AC, VAC=BAC-EAC. pv, ev, ac, bac는 같은 통화 단위의 Decimal 문자열이며 반올림 없이 Decimal 나눗셈 정밀도로 돌려준다. pv와 ac가 0이면 오류이고 bac는 양수여야 한다. EAC는 현재 비용 효율이 계속된다는 가정의 추정이며 etc_ 키는 예약어 회피용 이름이다."""
        ...
    def monte_carlo_schedule(self, tasks: list[dict[str, Num]], n: int = 1000, seed: int = 0) -> _m78.MonteCarloScheduleResult:
        """작업별 낙관, 최빈, 비관 추정으로 프로젝트 총 소요 시간의 분포를 몬테카를로로 시뮬레이션해 P10, P50, P90, 평균, 표본 표준편차를 돌려준다. tasks는 {id, optimistic, most_likely, pessimistic}(Decimal 문자열), n은 100 이상 1,000,000 이하 정수(기본 1000), seed 기본 0이면 결과가 재현된다. float64 계산이며 유효숫자 10자리 문자열이다. 작업 기간을 단순 합산하므로 병렬 경로나 선후 관계는 반영하지 않는다."""
        ...
    def pert(self, optimistic: Num, most_likely: Num, pessimistic: Num) -> _m79.PertResult:
        """단일 작업의 PERT 삼점 추정으로 기대 기간, 분산, 표준편차를 계산한다. E=(O+4M+P)/6, V=((P-O)/6)², 표준편차는 sqrt(V). 낙관, 최빈, 비관 값은 같은 시간 단위의 Decimal 문자열이며 낙관이 비관을 넘으면 오류다. 반올림하지 않고 표준편차만 유효숫자 30자리까지 구한다. 여러 작업의 합산 일정에는 critical_path 나 monte_carlo_schedule 을 쓴다."""
        ...


class _ProbabilityTools(Protocol):
    def bayes(self, prior: Num, likelihood: Num, marginal: Num) -> _m80.BayesResult:
        """베이즈 정리로 사후확률 P(A|B) = P(A)P(B|A)/P(B)를 구한다. prior, likelihood, marginal 은 [0, 1] 구간 십진 문자열이고 marginal 은 0 이 될 수 없으며 Decimal 50자리 정밀도로 계산한다. 입력 간 정합성(P(B) ≥ P(A)P(B|A))은 검사하지 않으므로 marginal 은 전체 확률 법칙으로 먼저 구해야 한다."""
        ...
    def beta_cdf(self, x: Num, alpha: Num, beta: Num) -> _m81.DistributionResult:
        """베타분포의 누적확률 P(X ≤ x) = I_x(α, β)를 구한다. x 는 [0, 1] 구간, alpha 와 beta 는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. alpha 와 beta 를 서로 바꾸면 결과가 달라진다."""
        ...
    def beta_pdf(self, x: Num, alpha: Num, beta: Num) -> _m81.DistributionResult:
        """베타분포의 확률밀도 f(x; α, β)를 구한다. x 는 [0, 1] 구간, alpha 와 beta 는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 밀도값은 1 을 넘을 수 있고 확률이 아니다."""
        ...
    def beta_ppf(self, q: Num, alpha: Num, beta: Num) -> _m81.DistributionResult:
        """베타분포의 분위수를 구한다. q 는 0 초과 1 미만, alpha 와 beta 는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. q 가 0 또는 1 이면 오류이며 결과는 [0, 1] 구간의 값이다."""
        ...
    def binomial_cdf(self, k: int, n: int, p: Num) -> _m81.DistributionResult:
        """이항분포의 누적확률 P(X ≤ k; n, p)를 구한다. k 와 n 은 0 이상 정수(k ≤ n), p 는 [0, 1] 구간 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 'k 회 이상'은 1 - cdf(k-1)로 구해야 하며 cdf(k)는 'k 회 이하'다."""
        ...
    def binomial_pmf(self, k: int, n: int, p: Num) -> _m81.DistributionResult:
        """이항분포의 확률질량 P(X=k; n, p)를 구한다. k 와 n 은 0 이상 정수(k ≤ n), p 는 [0, 1] 구간 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 'k 회 이하' 확률이 필요하면 binomial_cdf 를 쓴다."""
        ...
    def chi_square_cdf(self, x: Num, df: Num) -> _m81.DistributionResult:
        """카이제곱분포의 누적확률 P(X ≤ x)를 구한다. x 는 0 이상, df(자유도)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 검정의 p 값은 1 에서 이 값을 뺀 오른쪽 꼬리다."""
        ...
    def chi_square_pdf(self, x: Num, df: Num) -> _m81.DistributionResult:
        """카이제곱분포의 확률밀도를 구한다. x 는 0 이상, df(자유도)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 밀도값이지 확률이 아니므로 누적확률은 chi_square_cdf 를 쓴다."""
        ...
    def chi_square_ppf(self, q: Num, df: Num) -> _m81.DistributionResult:
        """카이제곱분포의 분위수를 구한다. q 는 0 초과 1 미만, df(자유도)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 유의수준 α 의 임계값은 q 에 1-α 를 넣는다."""
        ...
    def expected_value(self, values: list[Num], probabilities: list[Num]) -> _m82.ExpectedValueResult:
        """이산 확률변수의 기댓값 E[X] = Σ value_i * prob_i 를 구한다. values 와 probabilities 는 같은 길이의 십진 문자열 리스트이며 각 확률은 [0, 1], 합은 1 에서 1e-9 이내여야 한다. Decimal 50자리로 계산하며 연속분포에는 쓸 수 없다."""
        ...
    def exponential_cdf(self, x: Num, rate: Num) -> _m81.DistributionResult:
        """지수분포의 누적확률 P(X ≤ x) = 1 - e^(-λx)를 구한다. x 는 0 이상, rate(λ)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. rate 에 평균(1/λ)을 넣으면 틀린다."""
        ...
    def exponential_pdf(self, x: Num, rate: Num) -> _m81.DistributionResult:
        """지수분포의 확률밀도 f(x; λ) = λe^(-λx)를 구한다. x 는 0 이상, rate(λ)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. rate 에 평균(1/λ)을 넣으면 틀린다."""
        ...
    def exponential_ppf(self, q: Num, rate: Num) -> _m81.DistributionResult:
        """지수분포의 분위수 x = -ln(1-q)/λ 를 구한다. q 는 0 초과 1 미만, rate(λ)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. rate 에 평균(1/λ)을 넣으면 틀린다."""
        ...
    def f_cdf(self, x: Num, dfn: Num, dfd: Num) -> _m81.DistributionResult:
        """F 분포의 누적확률 P(X ≤ x)를 구한다. x 는 0 이상, dfn 은 분자 자유도, dfd 는 분모 자유도(둘 다 양수 십진 문자열)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 검정의 p 값은 1 에서 이 값을 뺀 오른쪽 꼬리다."""
        ...
    def f_pdf(self, x: Num, dfn: Num, dfd: Num) -> _m81.DistributionResult:
        """F 분포의 확률밀도를 구한다. x 는 0 이상, dfn 은 분자 자유도, dfd 는 분모 자유도(둘 다 양수 십진 문자열)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. dfn 과 dfd 를 바꾸면 결과가 달라진다."""
        ...
    def f_ppf(self, q: Num, dfn: Num, dfd: Num) -> _m81.DistributionResult:
        """F 분포의 분위수를 구한다. q 는 0 초과 1 미만, dfn 은 분자 자유도, dfd 는 분모 자유도(둘 다 양수 십진 문자열)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 유의수준 α 의 임계값은 q 에 1-α 를 넣는다."""
        ...
    def factorial(self, n: int) -> _m83.CombinatoricsResult:
        """n!을 정확한 정수 문자열로 반환한다. n 은 0 이상 정수이며 상한은 20000(환경변수 SOOTOOL_LIMIT_COMBINATORICS_N 으로 조정), 1000 미만은 math.factorial, 이상은 mpmath 로 계산하며 반올림은 없다. 결과 자릿수가 매우 커서 float 로 변환하면 정밀도를 잃는다."""
        ...
    def gamma_cdf(self, x: Num, shape: Num, scale: Num = '1') -> _m81.DistributionResult:
        """감마분포의 누적확률 P(X ≤ x)를 구한다. x 는 0 이상, shape(k)는 양수, scale(θ, 기본 1)은 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. scale 은 rate 의 역수이므로 rate 를 그대로 넣으면 틀린다."""
        ...
    def gamma_pdf(self, x: Num, shape: Num, scale: Num = '1') -> _m81.DistributionResult:
        """감마분포의 확률밀도 f(x; k, θ)를 구한다. x 는 0 이상, shape(k)는 양수, scale(θ, 기본 1)은 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. scale 은 rate 의 역수이므로 rate 를 그대로 넣으면 틀린다."""
        ...
    def gamma_ppf(self, q: Num, shape: Num, scale: Num = '1') -> _m81.DistributionResult:
        """감마분포의 분위수를 구한다. q 는 0 초과 1 미만, shape(k)는 양수, scale(θ, 기본 1)은 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. scale 은 rate 의 역수이므로 rate 를 그대로 넣으면 틀린다."""
        ...
    def lognormal_cdf(self, x: Num, mu: Num = '0', sigma: Num = '1') -> _m81.DistributionResult:
        """로그정규분포의 누적확률 P(X ≤ x) = Φ((ln x - μ)/σ)를 구한다. x 는 양수, mu 와 sigma 는 ln X 의 평균과 표준편차(sigma 는 양수, 기본 0 과 1)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. mu 와 sigma 에 X 자체의 통계량을 넣으면 틀린다."""
        ...
    def lognormal_pdf(self, x: Num, mu: Num = '0', sigma: Num = '1') -> _m81.DistributionResult:
        """로그정규분포의 확률밀도를 구한다. x 는 양수, mu 와 sigma 는 ln X 의 평균과 표준편차(sigma 는 양수, 기본 0 과 1)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. mu 와 sigma 는 X 자체의 평균과 표준편차가 아니다."""
        ...
    def lognormal_ppf(self, q: Num, mu: Num = '0', sigma: Num = '1') -> _m81.DistributionResult:
        """로그정규분포의 분위수 exp(μ + σΦ⁻¹(q))를 구한다. q 는 0 초과 1 미만, mu 와 sigma 는 ln X 의 평균과 표준편차(sigma 는 양수, 기본 0 과 1)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. mu 와 sigma 에 X 자체의 통계량을 넣으면 틀린다."""
        ...
    def nCr(self, n: int, r: int) -> _m83.CombinatoricsResult:
        """이항계수 C(n, r) = n!/(r!(n-r)!)을 정확한 정수 문자열로 반환한다. n, r 은 0 이상 정수(r ≤ n, n 상한 20000)이며 반올림은 없다. 순서를 구분하는 선택에 쓰면 r! 배 작게 나오므로 그 경우는 nPr 을 쓴다."""
        ...
    def nPr(self, n: int, r: int) -> _m83.CombinatoricsResult:
        """순열 P(n, r) = n!/(n-r)!을 정확한 정수 문자열로 반환한다. n, r 은 0 이상 정수(r ≤ n, n 상한 20000)이며 반올림은 없다. 순서를 구분하지 않는 선택에 쓰면 r! 배 크게 나오므로 그 경우는 nCr 을 쓴다."""
        ...
    def normal_cdf(self, x: Num, mu: Num = '0', sigma: Num = '1') -> _m81.DistributionResult:
        """정규분포의 누적확률 P(X ≤ x)를 구한다. x, mu(평균, 기본 0), sigma(표준편차, 양수, 기본 1)는 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. sigma 에 분산을 넣으면 틀리므로 표준편차를 넣는다."""
        ...
    def normal_pdf(self, x: Num, mu: Num = '0', sigma: Num = '1') -> _m81.DistributionResult:
        """정규분포의 확률밀도 f(x; μ, σ)를 구한다. x, mu(평균, 기본 0), sigma(표준편차, 양수, 기본 1)는 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 밀도값이지 확률이 아니므로 구간 확률은 normal_cdf 의 차로 구한다."""
        ...
    def normal_ppf(self, q: Num, mu: Num = '0', sigma: Num = '1') -> _m81.DistributionResult:
        """정규분포의 분위수 x = μ + σΦ⁻¹(q)를 구한다. q 는 0 초과 1 미만 확률, mu(기본 0), sigma(표준편차, 양수, 기본 1)이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. q 가 0 또는 1 이면 오류이고, 양측 임계값은 q 에 1-α/2 를 넣는다."""
        ...
    def poisson_cdf(self, k: int, lam: Num) -> _m81.DistributionResult:
        """포아송분포의 누적확률 P(X ≤ k; λ)를 구한다. k 는 0 이상 정수, lam(λ)은 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. 'k 회 이상'은 1 - cdf(k-1)로 구해야 하며 cdf(k)는 'k 회 이하'다."""
        ...
    def poisson_pmf(self, k: int, lam: Num) -> _m81.DistributionResult:
        """포아송분포의 확률질량 P(X=k; λ)를 구한다. k 는 0 이상 정수, lam(λ)은 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을 반환한다. lam 은 관측 구간 길이에 맞춘 평균 발생 횟수여야 하며 단위 시간당 비율을 그대로 넣으면 틀린다."""
        ...


class _RealestateTools(Protocol):
    def kr_acquisition_tax(self, price: Num, house_count: int, is_regulated: bool, area_m2: Num, year: int, is_corporate: bool = False, is_heavy_excluded: bool = False, *, as_of: Num | None = None, include_proposed: bool = False) -> _m84.RealestateKrAcquisitionTaxResult:
        """한국 주택 유상취득 취득세와 농어촌특별세·지방교육세를 계산한다. 표준세율은 6억 이하 1%, 6억 초과 9억 이하 산식 세율, 9억 초과 3%이고, 조정 2주택·비조정 3주택 8%, 조정 3주택 이상·비조정 4주택 이상·법인 12% 중과세율이 표준세율을 대체한다. 금액은 원 단위 문자열, 세목별 원 미만 절사. 농어촌특별세는 전용 85㎡ 초과만 과세. 오용 예: house_count 에 취득 전 주택 수 입력."""
        ...
    def kr_comprehensive(self, total_published_price: Num, year: int, house_count: int, is_corporate: bool = False, age: int | None = None, holding_years: int | None = None, residence_years: int | None = None, resident_house_price: Num | None = None, property_tax_levied: Num | None = None, prior_year_total_tax: Num | None = None, *, as_of: Num | None = None, include_proposed: bool = False) -> _m85.RealestateKrComprehensiveResult:
        """주택분 종합부동산세와 농어촌특별세(종부세의 20%)를 계산한다. 공시가격 합계(원)에서 기본공제 후 공정시장가액비율을 곱한 과세표준에 2주택 이하·3주택 이상 누진세율 또는 법인 단일세율을 적용하고, 재산세 상당액 공제, 1세대 1주택 연령·보유 세액공제, 세부담상한(직전 연도 총세액 입력 시)을 반영한다. policy_status 로 확정 전 개정안 여부를 확인. 오용 예: 토지분에 사용."""
        ...
    def kr_dsr(self, annual_debt_payment: Num, annual_income: Num, year: int, is_nonbank: bool = False, mortgage_region: Num | None = None, *, as_of: Num | None = None, include_proposed: bool = False) -> _m86.RealestateKrDsrResult:
        """DSR(총부채원리금상환비율 = 연간 원리금 상환액 / 연간 소득, 원 단위 문자열)을 계산하고 한도 이내인지 판정한다. 소수 4자리 HALF_EVEN 반올림, 한도는 은행권 40%, 2금융권(is_nonbank) 50%. mortgage_region 을 주면 스트레스 금리 하한을 반환하지만 상환액에 가산해 주지는 않는다. 오용 예: 월 상환액과 연 소득을 섞어 입력."""
        ...
    def kr_dti(self, monthly_debt_payment: Num, monthly_income: Num, year: int, is_regulated: bool, is_capital_area: bool = False, *, as_of: Num | None = None, include_proposed: bool = False) -> _m86.RealestateKrDtiResult:
        """DTI(총부채상환비율 = 월 원리금 상환액 / 월 소득, 원 단위 문자열)를 계산하고 한도 이내인지 판정한다. 소수 4자리 HALF_EVEN 반올림, 규제지역 40%, 규제지역 외 수도권(아파트 담보) 60%, 수도권 외 비규제지역은 한도 없음(cap 이 null, within_cap 은 true). 오용 예: 연간 금액을 월 금액 자리에 입력."""
        ...
    def kr_local_property(self, region: Num, mode: Num, price: Num, year: int, area_m2: Num = '0', include_urban: bool = True, is_one_house: bool = False, *, as_of: Num | None = None, include_proposed: bool = False) -> _m87.RealestateKrLocalPropertyResult:
        """광역자치단체(seoul, gyeonggi, busan, incheon, daegu, daejeon, gwangju, ulsan, sejong)별 주택 취득세 또는 재산세를 조례 가감 계수로 계산한다. mode 는 acquisition(취득가액) 또는 property(공시가격), 금액은 원 단위 문자열. 취득세와 부가분은 원 미만 절사, 재산세는 구간 세액 반올림 후 계수를 곱해 절사. 재산세 가감과 도시지역분은 자치구·시·군 조례 사항이라 광역 계수는 대표값이다. 오용 예: 구·군 단위 세율 확정에 사용."""
        ...
    def kr_ltv(self, loan_amount: Num, property_value: Num, year: int, is_regulated: bool, house_count: int, is_capital_area: bool = False, is_first_time_buyer: bool = False, *, as_of: Num | None = None, include_proposed: bool = False) -> _m86.RealestateKrLtvResult:
        """LTV(대출액 / 주택가액, 원 단위 문자열, 소수 4자리 HALF_EVEN)를 계산하고 한도 이내 여부와 최대 대출액을 구한다. 한도 비율은 규제지역·수도권, 주택 수, 생애최초 여부로 정해지며 규제지역·수도권 다주택은 추가 구입 0%다. 수도권·규제지역은 시가 15억 이하 6억, 25억 이하 4억, 초과 2억 금액 한도도 적용. 오용 예: house_count 에 대출 전 주택 수 입력."""
        ...
    def kr_property_tax(self, published_price: Num, year: int, include_urban: bool = True, is_one_house: bool = False, prior_year_published_price: Num | None = None, *, as_of: Num | None = None, include_proposed: bool = False) -> _m88.RealestateKrPropertyTaxResult:
        """한국 주택 재산세(지방세법 §110~§111의2)와 지방교육세·도시지역분을 계산한다. 공시가격(원)에 공정시장가액비율(일반 60%, 1세대 1주택은 시가표준액 구간별)을 곱해 과세표준을 구하고, 직전 연도 공시가격을 주면 과세표준상한을 적용한다. 누진세율, 9억 이하 1세대 1주택은 특례세율. 재산세는 원 미만 반올림, 부가분은 절사. 오용 예: 토지·건축물에 사용."""
        ...
    def kr_subscription_score(self, year: int, homeless_months: int, dependents: int, savings_months: int, homeless_period_applicable: bool = True, spouse_savings_months: int | None = None, *, as_of: Num | None = None, include_proposed: bool = False) -> _m89.SubscriptionScoreResult:
        """주택공급에 관한 규칙 별표 1의 청약 가점제 점수(무주택기간 32, 부양가족 35, 청약저축 가입기간 17, 합계 84점)를 계산한다. 기간은 입주자모집공고일 현재 개월 수 정수, 부양가족은 인원 정수로 넣는다. 배우자 가입기간은 50%로 환산해 3점 한도로 합산하고 저축 점수는 17점 한도다. 주택 소유 세대나 만 30세 미만 미혼은 homeless_period_applicable=false 로 0점이다. 만 나이 전체를 무주택기간으로 넣는 것은 오용이며 30세 또는 혼인신고일부터 센다."""
        ...
    def kr_transfer_tax(self, acquisition_price: Num, sale_price: Num, holding_years: int, is_one_house: bool, year: int, decimals: int = 0, *, as_of: Num | None = None, include_proposed: bool = False) -> _m90.RealestateKrTransferTaxResult:
        """한국 부동산 양도소득세를 tax.capital_gains_kr 에 위임해 계산하고 domain, module 표식을 붙인다. 금액은 원 단위 문자열, 세액은 decimals 자리 HALF_UP 반올림. is_one_house=true 는 주택(1세대 1주택 비과세·고가주택 안분·보유 거주 공제), false 는 주택 외 토지·건물로 처리한다. 오용 예: 다주택 주택 양도에 false 입력(중과·분양권·미등기는 tax.capital_gains_kr 직접 사용)."""
        ...
    def rental_yield(self, annual_rent: Num, property_price: Num, annual_expenses: Num = '0', yield_type: Num = 'gross', rounding: Num = 'HALF_EVEN', decimals: int = 2) -> _m91.RealestateRentalYieldResult:
        """임대수익률을 백분율(%) 문자열로 계산한다. gross 는 연간 임대수입 / 매입가격, net 은 (연간 임대수입 - 연간 비용) / 매입가격이며 금액은 원 단위 문자열이다. rounding(기본 HALF_EVEN)으로 decimals(기본 2) 자리까지 반올림하고, 비용이 임대수입보다 크면 net 은 음수다. gross 는 비용을 보지 않는다. 오용 예: 월 임대료를 연 환산하지 않고 annual_rent 에 입력."""
        ...


class _ScienceTools(Protocol):
    def battery_capacity(self, value: Num, voltage: Num, mode: Num = 'ah_to_wh') -> _m92.BatteryCapacityResult:
        """배터리 용량을 Ah와 Wh 사이에서 변환한다. Wh = Ah * V, Ah = Wh / V. mode='ah_to_wh'(기본) 또는 'wh_to_ah', value는 0 이상, voltage는 양수(V)이며 Decimal 문자열이다. 나눗셈은 반올림하지 않는다. 직렬이나 병렬 구성 용량은 계산하지 않으므로 팩 전체 전압과 용량을 쌍으로 넣어야 한다."""
        ...
    def bragg(self, order: int, wavelength: Num | None = None, spacing: Num | None = None, angle: Num | None = None, unit: Num = 'deg') -> _m93.BraggResult:
        """브래그 회절 조건 n*lambda = 2 d sin(theta)에서 파장, 면간격, 회절각 중 하나를 구한다. order는 양의 정수이고 wavelength, spacing, angle 중 정확히 하나를 생략하며 나머지는 Decimal 문자열이다. 파장과 면간격은 같은 길이 단위로 넣고, angle은 unit='deg'(기본) 또는 'rad'이며 브래그각 theta 기준이다(2theta 아님). mpmath 40자리 계산 후 유효숫자 20자리로 돌려주며 sin theta가 1을 넘는 조합은 오류다."""
        ...
    def faraday_electrolysis(self, current_a: Num, time_s: Num, molar_mass_g: Num, n_electrons: int) -> _m92.FaradayElectrolysisResult:
        """패러데이 법칙으로 전기분해 시 석출되는 질량(g)을 계산한다. m = (I * t * M) / (n * F). current_a는 암페어, time_s는 초, molar_mass_g는 g/mol(모두 양수 Decimal 문자열), n_electrons는 양의 정수. F=96485.33212 C/mol이며 반올림하지 않는다. 시간을 분이나 시간 단위로 넣으면 안 되고 전류 효율은 100%로 가정한다."""
        ...
    def half_life(self, initial_amount: Num, half_life: Num, elapsed_time: Num) -> _m94.HalfLifeResult:
        """방사성 붕괴로 남은 양을 계산한다. N(t) = N0 x 0.5^(t/T). initial_amount는 양수, half_life는 양수, elapsed_time은 0 이상의 Decimal 문자열이며 half_life와 elapsed_time은 같은 시간 단위여야 한다. mpmath 50자리로 계산해 유효숫자 30자리 문자열로 돌려주며 남은 비율(fraction)도 함께 반환한다. 단위가 다른 반감기와 경과 시간을 섞으면 안 된다."""
        ...
    def ideal_gas(self, pressure: Num | None = None, volume: Num | None = None, moles: Num | None = None, temperature: Num | None = None) -> _m95.IdealGasResult:
        """이상 기체 법칙 PV = nRT에서 빠진 변수 하나를 계산한다. 압력 Pa, 부피 m³, 물질량 mol, 온도 K 중 정확히 3개를 Decimal 문자열로 주고 나머지는 생략한다. R = 8.314462618 J/(mol K)(CODATA 2018), Decimal 정확 연산이며 반올림하지 않는다. 계산값이 음수이거나 0으로 나누면 오류다. atm, L, 섭씨를 그대로 넣으면 안 되고 SI 단위로 환산해야 한다."""
        ...
    def intensity(self, power_w: Num, area_m2: Num) -> _m93.IntensityResult:
        """빛이나 복사의 세기(단위 면적당 전력)를 계산한다. I = P / A. power_w는 0 이상 와트, area_m2는 양수 제곱미터의 Decimal 문자열이며 결과 단위는 W/m^2, 반올림하지 않는다. 입사각에 따른 유효 면적 보정이나 파장별 분광 세기는 다루지 않는다. 면적을 cm² 단위로 넣으면 안 된다."""
        ...
    def molar_mass(self, formula: Num) -> _m96.MolarMassResult:
        """화학식으로 몰질량(g/mol)을 계산하고 원소별 원자 수(composition)를 돌려준다. 원소 기호는 대소문자를 구분하며 괄호 Ca(OH)2, 수화물 CuSO4.5H2O 표기를 지원한다. IUPAC 2021 관례값 원자량을 Decimal로 합산하며 반올림하지 않는다. H~Pb 사이 일반 원소 27종만 지원하고 그 밖의 원소와 이온 전하 표기는 오류다."""
        ...
    def nernst(self, e0: Num, n: int, reaction_q: Num, temperature: Num = '298.15') -> _m92.NernstResult:
        """Nernst 방정식으로 비표준 조건의 전극 전위를 V 단위로 계산한다. E = E0 - (RT / nF) * ln(Q). e0(V)와 reaction_q(양수)는 Decimal 문자열, n은 양의 정수 전자수, temperature는 켈빈(기본 298.15). R=8.314462618, F=96485.33212를 쓰고 결과는 소수 20자리로 맞춘다. 섭씨 온도를 그대로 넣거나 Q 대신 ln(Q)를 넣으면 안 된다."""
        ...
    def snell_law(self, n1: Num, n2: Num, theta1: Num, unit: Num = 'deg') -> _m93.SnellLawResult:
        """스넬의 법칙으로 굴절각을 계산한다. n1 sin(theta1) = n2 sin(theta2), theta2 = asin(n1/n2 * sin(theta1)). n1, n2는 양수 굴절률, theta1은 입사각이며 모두 Decimal 문자열이다. unit='deg'(기본) 또는 'rad'이고 결과도 같은 단위다. mpmath 40자리 계산 후 유효숫자 20자리로 돌려준다. 전반사가 일어나는 입사각이면 오류이며 각도는 법선 기준이다(표면 기준 각을 넣으면 안 된다)."""
        ...
    def stoichiometry(self, reactants: list[dict[str, Any]], products: list[dict[str, Any]], coefficients: dict[str, int]) -> _m96.StoichiometryResult:
        """균형 맞춘 반응식 계수로 한계 반응물을 찾고 각 물질의 몰수(mol)와 질량(g)을 계산한다. reactants는 {formula, mass(g) 또는 moles} 목록, products는 {formula} 목록, coefficients는 {화학식: 정수 계수}이며 수치는 Decimal 문자열이다. 몰질량은 molar_mass 와 같은 원자량을 쓰고 반올림하지 않는다. 계수가 균형 상태가 아니면 결과가 틀리며 수율이나 불순물은 반영하지 않는다."""
        ...
    def thin_lens(self, focal_length: Num | None = None, object_dist: Num | None = None, image_dist: Num | None = None) -> _m93.ThinLensResult:
        """얇은 렌즈 방정식 1/f = 1/p + 1/q에서 빠진 값 하나(초점거리, 물체거리, 상거리)를 구하고 배율 m = -q/p도 돌려준다. 세 인자 중 정확히 2개를 Decimal 문자열로 주며 길이 단위는 통일한다. 반올림하지 않으며 0 거리나 평행광선(무한대) 조합은 오류다. 실상은 양, 허상은 음의 거리 부호 규약을 따르므로 부호를 맞춰 넣어야 한다."""
        ...


class _SootoolTools(Protocol):
    def policy_activate(self, draft_id: Num) -> _m97.PolicyActivateResult:
        """[관리자] 검증을 통과한 초안을 덮어쓰기 저장소에 반영하고 캐시를 비우며 감사 기록을 남긴다. 검증 오류가 있는 초안은 validation_failed 로 거부하고, 관리자 모드가 아니면 admin_required 를 반환한다. 반영된 초안은 삭제된다."""
        ...
    def policy_diff(self, domain: Num, name: Num, year_from: int | None = None, year_to: int | None = None, draft_id: Num | None = None) -> _m97.PolicyDiffResult:
        """정책 두 버전의 구간별 세율과 주요 값 변경을 비교한다. year_from 과 year_to 로 연도 간 비교하거나 draft_id 로 초안과 현재 시행본을 비교한다. 인자가 모자라거나 비교할 시행본이 없으면 error 필드로 알린다. 변경 이력은 sootool.policy_history 를 쓴다."""
        ...
    def policy_export(self, domain: Num, name: Num, year: int, include_signature: bool = False, *, as_of: Num | None = None, include_proposed: bool = False) -> _m97.PolicyExportResult:
        """정책 하나를 이식 가능한 묶음(원본 YAML과 메타데이터)으로 내보낸다. domain, name, year 로 지정하고 as_of, include_proposed 로 버전을 고른다. include_signature 가 참이면 환경변수 SOOTOOL_POLICY_KEY_FILE 이 가리키는 키 파일(권한 0600)로 ed25519 서명을 붙인다. 묶음은 sootool.policy_import 가 받는다."""
        ...
    def policy_get(self, domain: Num, name: Num, year: int, *, as_of: Num | None = None, include_proposed: bool = False) -> _m97.PolicyGetResult:
        """정책 파일 하나의 내용(data)과 출처(package 또는 override), 버전 정보를 반환한다. domain, name, year 로 지정하고 as_of(YYYY-MM-DD)로 그날 시행 중인 버전을, include_proposed 로 확정 전 개정안까지 고를 수 있다. 존재하지 않는 연도를 지정하면 오류가 난다."""
        ...
    def policy_history(self, domain: Num, name: Num) -> _m97.PolicyHistoryResult:
        """정책 하나(domain, name)의 변경 감사 기록을 기록된 순서대로 반환한다. 항목마다 action(activate, rollback, import), 시각, audit_id, 변경 전후 sha256 이 있고 기록이 없으면 빈 목록이다. 정책 내용 자체는 sootool.policy_get 으로 본다."""
        ...
    def policy_import(self, bundle: dict[str, Any], require_signature: bool = False, public_key_b64: Num | None = None) -> _m97.PolicyImportResult:
        """[관리자] sootool.policy_export 가 만든 묶음을 검증한 뒤 덮어쓰기 저장소에 반영한다. require_signature 와 public_key_b64 로 ed25519 서명을 검증하며 환경변수 SOOTOOL_POLICY_REQUIRE_SIGNATURE 가 켜져 있으면 서명이 필수다. 검증 오류는 validation_failed 로 거부하고, 관리자 모드가 필요하다."""
        ...
    def policy_list(self) -> _m97.PolicyListResult:
        """패키지와 덮어쓰기 저장소의 모든 정책 파일 목록을 반환한다. 항목마다 영역, 이름, 연도, 출처(package 또는 override), 시행일, 종료일, 상태, sha256 이 있다. 인자가 없고 읽기 전용이며, 정책 내용이 필요하면 sootool.policy_get 을 쓴다."""
        ...
    def policy_propose(self, domain: Num, name: Num, year: int, yaml_content: Num, source_url: Num = '', notice_no: Num = '', effective_date: Num = '', sensitivity_threshold: float | None = None, auto_fix_sha256: bool = False, draft_id: Num | None = None) -> _m97.PolicyProposeResult:
        """[관리자] 정책 초안을 만든다. 6단계 검증 보고서와 전년도 대비 변경점을 반환하며 아직 시행되지 않는다. 관리자 모드(SOOTOOL_ADMIN_MODE=1)가 아니면 error=admin_required 를 반환한다. 초안은 expires_at 에 만료되고 반영은 sootool.policy_activate 로 한다."""
        ...
    def policy_rollback(self, domain: Num, name: Num, year: int, effective_date: Num = '') -> _m97.PolicyRollbackResult:
        """[관리자] 덮어쓰기 저장소의 정책 버전 파일을 지워 패키지 기본값으로 되돌린다. 같은 연도에 덮어쓴 버전이 여럿이면 effective_date(YYYY-MM-DD)로 고르며 지정하지 않으면 ambiguous_version 을 반환한다. 지울 파일이 없으면 rolled_back 이 false 다. 관리자 모드가 필요하다."""
        ...
    def policy_validate(self, yaml_content: Num, domain: Num, name: Num | None = None, sensitivity_threshold: float | None = None, auto_fix_sha256: bool = False) -> _m97.PolicyValidateResult:
        """정책 YAML 문자열을 검증해 보고서(status, findings, sha256)를 반환한다. name 을 주면 도메인 스키마까지 검사하고 파일은 저장하지 않는다. auto_fix_sha256 이 참이면 계산한 해시를 fixed_sha256 으로 알려 준다. 실제 반영은 sootool.policy_propose 와 sootool.policy_activate 를 쓴다."""
        ...
    def skill_guide(self, section: Num = 'all', lang: Num | None = None) -> _m98.SkillGuideResult:
        """에이전트용 능동 활용 가이드를 반환한다. section 은 triggers(호출 신호표), examples, anti_patterns, playbooks, all(기본) 중 하나이고 lang 은 ko 또는 en 이다. lang 을 생략하면 요청 언어와 SOOTOOL_LOCALE 환경변수를 거쳐 ko 로 정해진다. 세션을 시작할 때 한 번 읽는다."""
        ...
    def verify_receipt(self, tool: Num, arguments: dict[str, Any], receipt: dict[str, Any], public_key_b64: Num | None = None, require_signature: bool = False) -> _m99.VerifyReceiptResult:
        """계산 영수증(_meta.integrity)을 재실행으로 검증한다. tool 과 arguments 로 같은 계산을 다시 실행해 입력 해시, 결과 해시, 도구 버전, 정책 해시를 대조하고, 서명이 있으면 public_key_b64 로 서명을 검증한다. valid 와 mismatches 를 반환한다. core.batch, core.pipeline 처럼 실행마다 결과가 달라지는 도구는 대상이 아니다."""
        ...


class _StatsTools(Protocol):
    def anova_oneway(self, groups: list[list[Num]], alpha: float = 0.05, include_tukey: bool = True) -> _m100.StatsAnovaOnewayResult:
        """둘 이상 집단의 평균 차이를 일원분산분석(one-way ANOVA)으로 검정하고 Tukey HSD 쌍별 비교를 덧붙인다. groups는 집단별 Decimal 문자열 목록(집단 2개 이상, 각 2개 이상), alpha는 유의수준 실수(기본 0.05), include_tukey 기본 True. 집단 크기가 다르면 Tukey-Kramer 방식이다. F는 유효숫자 6자리, 나머지는 10자리 문자열이다. 정규성과 등분산을 가정하므로 어긋나면 kruskal_wallis 를 쓴다."""
        ...
    def bootstrap_ci(self, values: list[Num], statistic: Num = 'mean', confidence: float = 0.95, n_resamples: int = 1000, seed: int = 42) -> _m101.StatsBootstrapCiResult:
        """표본 평균 또는 중앙값의 부트스트랩 신뢰구간을 백분위수법으로 구한다. values는 Decimal 문자열 2개 이상, statistic은 mean 또는 median, confidence는 0과 1 사이 실수(기본 0.95), n_resamples는 100 이상 100,000 이하(기본 1000), seed 기본 42로 같은 입력이면 결과가 재현된다. float64 계산 결과를 유효숫자 10자리 문자열로 돌려준다. 표본이 매우 작으면 구간이 불안정하다."""
        ...
    def chi_square_independence(self, observed: list[list[Num]]) -> _m102.StatsChiSquareIndependenceResult:
        """분할표의 두 범주형 변수가 독립인지 카이제곱 검정으로 판정해 chi2, df, p_value, 기대빈도 표를 돌려준다. observed는 관측 빈도의 2x2 이상 Decimal 문자열 행렬이다. scipy 기본값에 따라 2x2 표에는 Yates 연속성 보정이 적용된다. 결과는 유효숫자 10자리 문자열이다. 비율 자료나 기대빈도가 5 미만인 칸이 많은 표에는 부적합하다."""
        ...
    def ci_mean(self, values: list[Num], confidence: Num = '0.95') -> _m103.StatsCiMeanResult:
        """표본 평균의 양측 신뢰구간을 t-분포로 계산해 mean, lower, upper를 돌려준다. values는 Decimal 문자열 2개 이상, confidence는 0과 1 사이 Decimal 문자열(기본 "0.95")이다. 표준오차는 표본 표준편차(ddof=1) 기반이며 float64 계산 결과를 유효숫자 10자리 문자열로 돌려준다. confidence에 95처럼 백분율을 넣으면 오류이고, 모집단 비율의 구간에는 쓸 수 없다."""
        ...
    def cohens_d(self, a: list[Num], b: list[Num]) -> _m104.StatsCohensDResult:
        """두 독립 표본의 효과크기 Cohen's d와 소표본 보정값 Hedges's g를 계산한다. d = (a 평균 - b 평균) / 풀드 표준편차이며 a 평균이 크면 양수다. a, b는 Decimal 문자열 각 2개 이상이고 풀드 표준편차가 0이면 오류다. 결과는 유효숫자 6자리 문자열이다. 대응표본(전후 비교)에는 쓰지 않는다."""
        ...
    def descriptive(self, values: list[Num], ddof: int = 1) -> _m105.StatsDescriptiveResult:
        """숫자 목록의 기술통계량(n, mean, median, variance, stdev, min, max, q1, q3)을 계산한다. values는 Decimal 문자열 2개 이상, ddof 기본 1은 표본 분산과 표준편차, 0이면 모집단 값이다. q1과 q3는 numpy 선형 보간 백분위수이고 float64 계산 결과를 유효숫자 10자리 문자열로 돌려준다. 모집단 전체 자료에는 ddof=0을 지정해야 한다."""
        ...
    def eta_squared(self, groups: list[list[Num]]) -> _m104.StatsEtaSquaredResult:
        """일원분산분석의 효과크기 eta^2(편향 있음)와 omega^2(편향 보정)를 계산하고 F, p값, 자유도도 함께 돌려준다. groups는 집단별 Decimal 문자열 목록이며 집단 2개 이상, 각 집단 2개 이상이다. eta^2 = SS_between / SS_total, 효과크기와 F는 유효숫자 6자리, p값은 10자리 문자열이다. 표본이 작으면 eta^2가 과대 추정되므로 omega^2를 함께 본다."""
        ...
    def kruskal_wallis(self, groups: list[list[Num]]) -> _m106.StatsKruskalWallisResult:
        """독립 여러 집단의 분포 위치 차이를 순위 기반 Kruskal-Wallis H 검정으로 판정해 h_stat, p_value, df(집단 수-1)를 돌려준다. groups는 집단별 Decimal 문자열 목록이며 집단 2개 이상, 각 집단 1개 이상이다. 정규성 가정이 필요 없고 H는 유효숫자 6자리, p값은 10자리 문자열이다. 사후 쌍별 비교는 제공하지 않는다."""
        ...
    def mann_whitney_u(self, a: list[Num], b: list[Num], tail: Num = 'two') -> _m106.StatsMannWhitneyUResult:
        """독립 두 표본의 분포 위치 차이를 순위 기반 Mann-Whitney U 검정으로 판정해 u_stat, p_value, n_a, n_b를 돌려준다. a, b는 Decimal 문자열 각 1개 이상, tail은 two(기본), less, greater이며 u_stat은 a 표본 기준이다. 정규성 가정이 필요 없고 u는 유효숫자 6자리, p값은 10자리 문자열이다. 같은 대상의 전후 측정에는 wilcoxon 을 쓴다."""
        ...
    def regression_linear(self, X: list[list[Num]], y: list[Num], add_intercept: bool = True) -> _m107.StatsRegressionLinearResult:
        """최소제곱(OLS) 선형회귀로 계수, 절편, R², 계수별 p값, 잔차를 구한다. X는 표본 수 x 특징 수의 Decimal 문자열 행렬, y는 표본 수 길이의 목록이며 표본 수는 특징 수 + 절편 수보다 커야 한다. add_intercept 기본 True이고 False면 절편은 "0"이다. p_values는 절편을 제외한 계수 순서이며 float64 계산 결과를 유효숫자 10자리 문자열로 돌려준다. 범주형 변수는 수치로 부호화해 넣어야 한다."""
        ...
    def ttest_one_sample(self, values: list[Num], popmean: Num, tail: Num = 'two') -> _m102.StatsTtestOneSampleResult:
        """표본 평균이 기준값 popmean과 다른지 일표본 t-검정으로 판정해 t, df(n-1), p_value, ci_95를 돌려준다. values는 Decimal 문자열 2개 이상, popmean은 Decimal 문자열, tail은 two(기본), less, greater이며 p값은 방향에 맞게 scipy가 계산한다. ci_95는 방향과 무관한 표본 평균의 95% t-구간이다. t는 유효숫자 6자리, p값은 10자리 문자열이다. 두 집단 비교에는 ttest_two_sample 을 쓴다."""
        ...
    def ttest_paired(self, a: list[Num], b: list[Num], tail: Num = 'two') -> _m102.StatsTtestPairedResult:
        """같은 대상의 전후 측정 등 대응표본의 평균 차이를 t-검정으로 판정해 t, df(n-1), p_value, ci_95(a 평균 - b 평균의 95% 구간)를 돌려준다. a, b는 같은 길이의 Decimal 문자열 목록(2개 이상)이고 같은 위치끼리 짝이다. tail은 two(기본), less, greater. t는 유효숫자 6자리, p값은 10자리다. 서로 다른 대상의 두 집단에는 ttest_two_sample 을 쓴다."""
        ...
    def ttest_two_sample(self, a: list[Num], b: list[Num], equal_var: bool = False, tail: Num = 'two') -> _m102.StatsTtestTwoSampleResult:
        """독립 두 표본의 평균 차이를 t-검정으로 판정해 t, df, p_value, ci_95(a 평균 - b 평균의 95% 구간)를 돌려준다. a, b는 Decimal 문자열 각 2개 이상, equal_var 기본 False는 Welch 검정(df는 소수 가능)이고 True면 Student 검정이다. tail은 two(기본), less, greater이며 df는 문자열이다. 같은 대상의 전후 측정에는 ttest_paired 를 쓴다."""
        ...
    def wilcoxon(self, a: list[Num], b: list[Num] | None = None, tail: Num = 'two') -> _m106.StatsWilcoxonResult:
        """Wilcoxon 부호순위 검정으로 대응표본의 차이 또는 단일 표본의 0 기준 위치 이동을 판정해 w_stat, p_value, n을 돌려준다. b를 주면 a와 b는 같은 길이(1개 이상)의 짝지은 Decimal 문자열 목록이고, b를 생략하면 a 자체를 차이값으로 보고 0과 비교한다. tail은 two(기본), less, greater. w는 유효숫자 6자리, p값은 10자리 문자열이다. 독립 두 집단에는 mann_whitney_u 를 쓴다."""
        ...


class _SymbolicTools(Protocol):
    def diff(self, expression: Num, var: Num, order: int = 1, variables: dict[str, Num] | None = None, numeric_eval: bool = True) -> _m108.DiffResult:
        """sympy 로 n차 기호 도함수를 구하고, variables 로 값을 치환하면 그 지점의 수치를 Decimal 문자열(50자리)로 함께 반환한다. var 는 미분 변수, order 는 1~20(기본 1). variables 가 없거나 치환 후에도 기호가 남거나 numeric_eval=false 이면 numeric 은 null 이다. 연산은 5초로 제한되며 sympy extra 가 필요하다."""
        ...
    def solve(self, equation: Num, var: Num, variables: dict[str, Num] | None = None, numeric_eval: bool = True) -> _m109.SolveResult:
        """sympy 로 방정식을 기호 풀이한다. equation 은 'lhs = rhs' 또는 단일식(=0 가정), var 는 풀 변수이며 variables 값은 풀기 전에 치환한다. solutions 에는 실수해만 50자리 Decimal 문자열로 담기고(소수 리터럴과 variables 값은 정확한 유리수로 해석), 복소해와 기호해는 symbolic 에만 담기며 numeric_eval=false 면 solutions 는 빈 리스트다. 연산은 5초로 제한되며 sympy extra 가 필요하다."""
        ...


class _TaxTools(Protocol):
    def capital_gains_kr(self, acquisition_price: Num, sale_price: Num, holding_years: int, is_one_house: bool, year: int, decimals: int = 0, residence_years: int | None = None, acquired_in_regulated_area: bool = False, asset_type: Num | None = None, is_non_business_land: bool = False, is_unregistered: bool = False, multi_house_surcharge: Num = 'none', transfer_date: Num | None = None, apply_basic_deduction: bool = True, *, as_of: Num | None = None, include_proposed: bool = False) -> _m110.TaxCapitalGainsKrResult:
        """한국 양도소득세를 계산한다(소득세법 제89조·제95조·제103조·제104조). 금액은 원 단위 Decimal 문자열, 보유·거주 기간은 만 년 정수다. 1세대1주택 비과세와 12억 초과 고가주택 안분, 장기보유특별공제(표 1, 보유·거주 표 2), 기본공제 250만원, 단기보유·분양권·비사업용 토지·미등기·조정대상지역 다주택 중과 세율 중 해당 경로의 큰 세액을 적용한다. 세액은 decimals(기본 0)자리 HALF_UP 이고 지방소득세는 포함하지 않는다. 보유 2년 이상 다주택 중과 제외 판정에는 transfer_date 가 필요하다."""
        ...
    def kr_comprehensive_income_tax(self, year: int, total_salary: Num = '0', business_income: Num | None = None, business_revenue: Num = '0', business_expenses: Num = '0', interest_income: Num = '0', dividend_gross_up_eligible: Num = '0', dividend_other: Num = '0', pension_gross: Num = '0', other_income_deemed_revenue: Num = '0', other_income_actual_expenses: Num = '0', other_income_amount: Num = '0', other_income_aggregate: bool = False, dependents: int = 1, elderly_count: int = 0, disabled_count: int = 0, woman_deduction: bool = False, single_parent: bool = False, other_income_deductions: Num = '0', children_count: int = 0, newborn_birth_orders: list[int] | None = None, other_tax_credits: Num = '0', apply_standard_tax_credit: bool = False, diligent_business_operator: bool = False, *, as_of: Num | None = None, include_proposed: bool = False) -> _m111.TaxKrComprehensiveIncomeTaxResult:
        """종합소득세 신고 흐름(소득금액 합산, 종합소득공제, 과세표준, 산출세액, 세액공제, 결정세액, 지방소득세 10%)을 계산한다. 금액은 원 단위 Decimal 문자열, year 필수, 원 미만 버림. 근로(총급여), 사업, 이자·배당(2천만원 초과 시 배당가산 10%, 제62조 비교과세, 배당세액공제), 연금(총연금액), 기타소득(60% 의제경비, 300만원 이하 분리과세)을 받는다. 결손금 통산, 중간예납·기납부세액, 외국납부세액공제는 계산하지 않고 특별공제는 합계로 넣는다. 근로소득만 있는 연말정산에는 payroll.kr_year_end_tax_settlement 를 쓴다."""
        ...
    def kr_corporate(self, taxable_income: Num, year: int, is_small: bool = False, rounding: Num = 'HALF_UP', decimals: int = 0, is_small_rental_corp: bool = False, sme_graduation_period: Num = 'none', reductions: Num = '0', pre_deduction_income: Num | None = None, *, as_of: Num | None = None, include_proposed: bool = False) -> _m112.TaxKrCorporateResult:
        """한국 법인세를 계산한다(법인세법 제55조, 조세특례제한법 제132조). taxable_income 은 과세표준(원, Decimal 문자열)이고 누진 구간 산출세액(base_tax)에서 reductions 를 빼되 최저한세에 미달하는 감면은 배제해 tax 를 정한다. is_small_rental_corp 는 제55조제1항제2호 세율, is_small 과 sme_graduation_period 는 최저한세율을 바꾼다. 감면 전 과세표준이 다르면 pre_deduction_income 을 따로 넣어야 최저한세가 맞는다."""
        ...
    def kr_education_tax_add(self, base_tax: Num, rate: Num = '0.20', rounding: Num = 'DOWN', decimals: int = 0) -> _m113.TaxKrEducationTaxAddResult:
        """한국 지방교육세를 본세 x 부가세율로 계산한다(지방세법 제151조). base_tax 는 재산세·취득세·등록면허세 등 본세액(원, 0 이상 Decimal 문자열), rate 기본 0.20(0 이상 1 이하), rounding 기본 DOWN, decimals 기본 0이라 원 미만을 버린다. 본세마다 세율이 다르므로 rate 를 확인하지 않고 기본값을 쓰면 틀릴 수 있다."""
        ...
    def kr_eitc(self, year: int, household_type: Num, property_total: Num, earned_income: Num = '0', business_income: list[dict[str, Num]] | None = None, religious_income: Num = '0', spouse_earned_income: Num = '0', spouse_business_income: list[dict[str, Num]] | None = None, spouse_religious_income: Num = '0', other_income: Num = '0', late_application: bool = False, *, as_of: Num | None = None, include_proposed: bool = False) -> _m114.KrEitcResult:
        """한국 근로장려금(조특법 §100의3·§100의5·§100의7) 산정. year 는 소득 귀속연도, 금액은 원 단위 숫자 문자열. 가구유형(single/one_earner/dual_earner)과 부부의 근로 총급여액, 사업 총수입금액(업종별 조정률 적용), 종교인소득, 재산 합계액으로 요건을 판정하고 시행령 별표 11 산정표 금액에 재산 1.7억원 이상 50%, 기한 후 95% 감액과 최소지급액 규칙을 적용한다. 산정표가 천원 단위라 별도 반올림은 없다. 자녀장려금, 반기 신청, 체납 충당, 국적·부양자녀·전문직 요건은 판정하지 않는다. 사업소득에 필요경비를 뺀 소득금액을 넣는 것은 오용이다."""
        ...
    def kr_gift(self, gift_amount: Num, relationship: Num, year: int, rounding: Num = 'HALF_UP', decimals: int = 0, prior_deduction_used_10y: Num = '0', marriage_birth_gift: bool = False, prior_marriage_birth_deduction: Num = '0', generation_skip: bool = False, timely_filing: bool = True, *, as_of: Num | None = None, include_proposed: bool = False) -> _m115.TaxKrGiftResult:
        """한국 증여세를 계산한다(상속세및증여세법 제53조·제53조의2·제56조·제57조·제69조). 금액은 원 단위 Decimal 문자열이다. 관계별 증여재산공제에서 10년 내 기공제액을 빼고, marriage_birth_gift=true 이면 직계존속 증여에 혼인·출산 공제 1억을 더하며, 10~50% 누진세율에 generation_skip=true 일 때 세대생략 할증(30%, 미성년 20억 초과 40%)과 기한 내 신고세액공제 3%를 반영한다. tax 는 신고세액공제 전 금액이고 공제 후는 tax_after_filing_credit 이다. 10년 내 기공제액은 prior_deduction_used_10y 로 직접 넣는다."""
        ...
    def kr_income(self, taxable_income: Num, year: int, rounding: Num = 'HALF_UP', decimals: int = 0, *, as_of: Num | None = None, include_proposed: bool = False) -> _m116.TaxKrIncomeResult:
        """한국 종합소득세·근로소득세 산출세액을 소득세법 제55조 기본세율(6~45% 누진, 정책 YAML)로 계산한다. taxable_income 은 공제를 모두 뺀 과세표준(원, Decimal 문자열)이고 year 는 필수다. 구간별 세액과 실효·한계세율을 돌려주며 rounding(기본 HALF_UP)으로 decimals(기본 0)자리에 맞춘다. 근로소득공제와 세액공제는 반영하지 않으므로 총급여를 그대로 넣으면 안 된다."""
        ...
    def kr_inheritance(self, gross_estate: Num, spouse_inheritance: Num, year: int, use_lump_sum: bool = True, rounding: Num = 'HALF_UP', decimals: int = 0, has_spouse: bool | None = None, spouse_legal_share_cap: Num | None = None, spouse_sole_heir: bool = False, children_count: int = 0, minor_years_total: int = 0, elderly_count: int = 0, disabled_life_years_total: int = 0, bequest_to_non_heirs: Num = '0', renounced_inheritance: Num = '0', pre_gift_added: Num = '0', timely_filing: bool = True, skipped_generation_amount: Num = '0', skipped_generation_minor: bool = False, *, as_of: Num | None = None, include_proposed: bool = False) -> _m117.TaxKrInheritanceResult:
        """한국 상속세를 계산한다(상속세및증여세법 제18조~제21조·제24조·제26조·제69조). 금액은 원 단위 Decimal 문자열이다. 기초·인적공제와 일괄공제 5억 중 큰 금액, 배우자공제(법정상속분 한도와 30억 중 작은 값, 최소 5억), 공제 종합한도를 적용한 뒤 10~50% 누진세율로 산출하고 세대생략 할증(제27조, 산출세액 x 받은 재산 비율 x 30%, 미성년 20억 초과 40%)을 더한 뒤 신고세액공제 3%를 따로 보여 준다. gross_estate 는 사전증여 가산 후 과세가액이며 할증 비율의 분모다. 배우자가 있으나 상속받지 않았으면 has_spouse=true 를 지정한다."""
        ...
    def kr_local_income_tax(self, income_tax: Num, rounding: Num = 'DOWN', decimals: int = 0) -> _m118.TaxKrLocalIncomeTaxResult:
        """한국 개인 지방소득세를 소득세 본세의 10% 고정 비율로 계산한다(지방세법 제92조). income_tax 는 이미 산출된 소득세액(원, 0 이상 Decimal 문자열)이며 rounding 기본 DOWN, decimals 기본 0이라 원 미만을 버린다. 과세표준이나 소득금액을 넣으면 안 되고 소득세 산출 후 그 세액을 넣어야 한다."""
        ...
    def kr_pension_income(self, year: int, private_pension_amount: Num = '0', age: int | None = None, lifetime_annuity: bool = False, deferred_retirement_amount: Num = '0', deferred_retirement_tax_rate: Num | None = None, actual_receipt_years: int | None = None, non_pension_withdrawal_amount: Num = '0', public_pension_amount: Num = '0', annual_private_pension_total: Num | None = None, *, as_of: Num | None = None, include_proposed: bool = False) -> _m119.PensionIncomeResult:
        """한국 사적연금(연금계좌) 인출 원천징수, 분리과세 판정, 연금소득공제를 계산한다(소득세법 제129조, 제14조, 제47조의2). 금액은 원 문자열이며 private_pension_amount 는 나이별 5·4·3%(종신 3%), deferred_retirement_amount 는 이연퇴직소득으로 연금외수령 세율의 70·60·50%, non_pension_withdrawal_amount 는 연금외수령 15%. 지방소득세 10% 별도, 원 미만 절사. 사적연금 연 1,500만원 이하 분리과세. 공적연금 간이세액표 원천징수는 계산하지 않으므로 공적연금 월 원천징수액 용도로 쓰면 오용이다."""
        ...
    def kr_registration_license_tax(self, registration_type: Num, year: int, tax_base: Num | None = None, *, as_of: Num | None = None, include_proposed: bool = False) -> _m120.RegistrationLicenseTaxResult:
        """부동산 등기의 등록면허세와 지방교육세(20%)를 계산한다(지방세법 제28조제1항제1호, 제151조). 저당권, 전세권, 지상권, 지역권, 임차권, 경매신청, 가압류, 가처분, 가등기는 과세표준(원 문자열) × 2/1000, 6천원 미만이면 6천원이고 other 는 건당 6천원이다. 세액은 10원 미만 버림. 소유권 보존과 이전 등기는 취득세로 과세되므로 다루지 않는다. 임차권 과세표준을 보증금으로 넣는 것은 오용이며 월 임대차금액을 넣는다."""
        ...
    def kr_rural_special_tax(self, amount: Num, mode: Num = 'base', rounding: Num = 'DOWN', decimals: int = 0) -> _m121.TaxKrRuralSpecialTaxResult:
        """한국 농어촌특별세를 계산한다(농어촌특별세법 제5조). mode=base 는 본세액 x 10%, mode=reduced 는 감면세액 x 20%이고 amount 는 해당 금액(원, 0 이상 Decimal 문자열)이다. rounding 기본 DOWN, decimals 기본 0이라 원 미만을 버린다. 과세표준이 아니라 본세 또는 감면액을 넣어야 하며 mode 를 바꾸면 세율이 달라진다."""
        ...
    def kr_securities_transaction(self, transfer_amount: Num, market: Num, year: int, *, as_of: Num | None = None, include_proposed: bool = False) -> _m122.SecuritiesTransactionTaxResult:
        """한국 주식 양도 시 증권거래세와 농어촌특별세를 계산한다(증권거래세법 제8조, 시행령 제5조 탄력세율, 농특세법 제5조). transfer_amount 는 양도가액(원), market 은 kospi, kosdaq, konex, k_otc(금융투자협회 장외), other(그 밖의 장외·비상장, 기본세율 0.35%). year 는 결제일 연도이며 2023~2026 을 지원한다. 세액은 원 미만 절사. 2026 코스피는 0.05%와 농특세 0.15%로 실효 0.20%. 대체거래소 거래와 비과세 양도는 반영하지 않는다. 체결일 연도로 year 를 넣는 것은 오용이다."""
        ...
    def kr_simplified_vat(self, supply_value: Num, business_type: Num, year: int, input_tax_amount: Num = '0', card_sales_amount: Num = '0', prior_year_supply: Num | None = None, restricted_business: bool = False, *, as_of: Num | None = None, include_proposed: bool = False) -> _m123.TaxKrSimplifiedVatResult:
        """한국 간이과세자 부가가치세를 계산한다(부가가치세법 제46조·제61조·제63조·제69조). 금액은 원 단위 Decimal 문자열이다. 공급대가 x 업종별 부가가치율 x 10%에서 세금계산서등 수취분 0.5%와 신용카드 등 매출세액공제를 빼며, 공급대가가 4,800만원 미만이면 납부 면제로 0을 돌려준다. 모든 금액은 원 미만을 버리고 일반과세자 계산에는 쓸 수 없다. 간이과세 기준(1억4백만원) 초과여도 계산은 하며 threshold_exceeded 로만 표시하고, prior_year_supply 를 생략하면 당해 공급대가로 판정한다."""
        ...
    def kr_vehicle_tax(self, year: int, vehicle_type: Num = 'passenger', displacement_cc: int | None = None, business_use: bool = False, age_start_date: Num | None = None, annual_payment: Num = 'none', *, as_of: Num | None = None, include_proposed: bool = False) -> _m124.VehicleTaxResult:
        """한국 승용자동차 자동차세 연세액과 지방교육세(비영업용 30%)를 계산한다(지방세법 제127조, 제128조, 제151조). 배기량은 cc 정수, 차령기산일은 YYYY-MM-DD(보통 최초 신규등록일)이다. 비영업용은 차령 3년부터 연 5%, 최대 50% 경감하고 annual_payment 로 1월, 3월, 6월, 9월 연납 공제(이자율 5%)를 적용한다. 세액은 기분마다 10원 미만 버림. 승합, 화물, 특수차, 신규등록 일할계산, 조례 세율 조정은 다루지 않으며, 차령을 연식 차이로 넣으면 기산일 규칙과 어긋난다."""
        ...
    def kr_withholding_simple(self, monthly_salary: Num, dependents: int, year: int, children_8_20: int = 0, *, as_of: Num | None = None, include_proposed: bool = False) -> _m125.TaxKrWithholdingSimpleResult:
        """근로소득 월 원천징수세액을 소득세법 시행령 별표 2 간이세액표로 구한다. monthly_salary 는 비과세·학자금을 뺀 월급여액(원, Decimal 문자열)이며 천원 미만을 버려 [이상, 미만) 행을 찾고, 10,000천원 초과 산식, 공제대상가족 11명 초과 규정, 8세 이상 20세 이하 자녀 차감을 적용한다. 세액은 원 단위이며 지방소득세 10%는 포함하지 않는다. dependents 는 본인 포함 인원이고 연간 정산(연말정산)에는 쓰지 않는다."""
        ...
    def progressive(self, taxable_income: Num, brackets: list[dict[str, Any]], rounding: Num = 'HALF_UP', decimals: int = 0) -> _m126.TaxProgressiveResult:
        """임의의 누진세율 구간표로 세액을 계산한다. taxable_income 은 0 이상의 Decimal 문자열, brackets 는 오름차순 {upper, rate} 목록이며 마지막 upper 는 null, rate 는 0.1 처럼 소수다. 구간은 하한 초과 상한 이하이고 구간별 세액 합계를 rounding(기본 HALF_UP)으로 decimals(기본 0)자리에 맞춘다. 법정 세율표를 직접 입력해 쓰면 개정을 반영하지 못하므로 정책을 읽는 kr_income 등을 우선 쓴다."""
        ...


class _TaxUsTools(Protocol):
    def capital_gains(self, gain: Num, filing_status: Num, year: int, term: Num = 'long', magi: Num | None = None, apply_niit: bool = False, ordinary_taxable_income: Num | None = None, rounding: Num = 'HALF_UP', decimals: int = 2, *, as_of: Num | None = None, include_proposed: bool = False) -> _m127.TaxUsCapitalGainsResult:
        """미국 연방 자본이득세를 계산한다. 장기(long)는 0%/15%/20% 구간을 신고 유형별로 적용하며 ordinary_taxable_income 위에 양도소득을 쌓아 과세하고, 단기(short)는 그 증가분에 일반 소득세율을 쓴다. apply_niit=true 이면 순투자소득세 3.8%를 더한다. 금액은 USD Decimal 문자열이고 기본은 소수 둘째 자리 HALF_UP이다. ordinary_taxable_income 을 생략하면 0으로 보므로 다른 소득이 있으면 반드시 넣어야 한다."""
        ...
    def federal_income(self, taxable_income: Num, filing_status: Num, year: int, apply_standard_deduction: bool = False, rounding: Num = 'HALF_UP', decimals: int = 2, *, as_of: Num | None = None, include_proposed: bool = False) -> _m128.TaxUsFederalIncomeResult:
        """미국 연방 소득세(일반 세율)를 계산한다. IRS 2025·2026 tax year, 7개 누진 구간, 4개 신고 유형이며 qualifying_surviving_spouse 는 공동 신고 표를 쓴다. 금액은 USD Decimal 문자열이고 기본은 소수 둘째 자리 HALF_UP이다. apply_standard_deduction=true 이면 taxable_income 을 AGI 로 보고 표준공제를 뺀다. 이미 공제를 뺀 과세표준에 true 를 주면 공제가 두 번 빠지고, 장기 양도소득이나 FICA 는 반영하지 않는다."""
        ...
    def fica(self, year: int, mode: Num = 'employee', wages: Num = '0', net_profit: Num = '0', filing_status: Num | None = None, other_medicare_wages: Num = '0', rounding: Num = 'HALF_UP', decimals: int = 2, *, as_of: Num | None = None, include_proposed: bool = False) -> _m129.FicaResult:
        """미국 FICA 급여세(IRC 3101, 3111) 근로자·고용주 부담분과 자영업세 SECA(IRC 1401, 순이익의 92.35%)를 과세연도 정책으로 계산한다. 금액은 USD 연간 합계 문자열, 세목별로 decimals 자리 반올림(기본 HALF_UP 2자리). 추가 Medicare 0.9%는 고용주 원천징수(20만 달러 초과)와 filing_status 별 신고 정산(25만/12.5만/20만)을 나눠 낸다. 사회보장 기준액은 고용주 한 곳 기준이며 복수 고용주 초과징수 환급, 선택적 계산법, RRTA, 배우자 자영업 소득 합산은 다루지 않는다. 오용 예: 급여 1회분을 연간 임금으로 넣기."""
        ...
    def state_tax(self, taxable_income: Num, state: Num, filing_status: Num, year: int, apply_standard_deduction: bool = False, rounding: Num = 'HALF_UP', decimals: int = 2, state_agi: Num | None = None, *, as_of: Num | None = None, include_proposed: bool = False) -> _m130.TaxUsStateTaxResult:
        """미국 주 소득세를 계산한다(CA, NY, TX). 신고 유형별 누진 구간과 주별 표준공제를 반영하고 TX 는 소득세가 없어 0이다. NY 는 조정총소득(state_agi)이 107,650 을 넘으면 세액 환수(recapture) 워크시트를, CA 는 과세표준 1,000,000 초과분에 1% 가산세를 적용한다. 금액은 USD Decimal 문자열이고 기본은 소수 둘째 자리 HALF_UP이다. 연도별 지원 범위가 다르고(CA 2025), 지방세나 FICA 는 포함하지 않는다."""
        ...


class _UnitsTools(Protocol):
    def convert(self, magnitude: Num, from_unit: Num, to_unit: Num) -> _m131.ConvertResult:
        """pint 로 물리 단위를 변환한다. magnitude 는 Decimal 문자열, from_unit 과 to_unit 은 pint 단위 이름(meter, foot, km 등)이고 차원이 다르거나 모르는 단위는 오류이다. 결과 magnitude 는 문자열이며 1E+3 같은 지수 표기가 나올 수 있다. 섭씨·화씨는 끝자리 오차가 생기므로 units.temperature 를 쓴다."""
        ...
    def data_size_convert(self, magnitude: Num, from_unit: Num, to_unit: Num, mode: Num = 'si') -> _m132.DataSizeConvertResult:
        """데이터 크기 단위를 바이트 기준으로 변환한다. mode 'si'(b, B, kB, MB, GB, TB, PB, 1000 배, b 는 비트, 기본)와 'iec'(B, KiB, MiB, GiB, TiB, PiB, 1024 배)는 각 표의 단위만, 'mixed' 는 두 표를 함께 허용한다. magnitude 는 0 이상 Decimal 문자열이고 단위는 대소문자를 구분한다(KB 는 오류, kB 만 유효)."""
        ...
    def energy_convert(self, magnitude: Num, from_unit: Num, to_unit: Num) -> _m132.EnergyConvertResult:
        """에너지 단위를 J 기준 Decimal 계수로 변환한다. 지원 단위는 J, kJ, cal, kcal, eV, BTU, Wh, kWh 이며 대소문자를 구분하고 magnitude 는 Decimal 문자열이다. cal 은 열화학 칼로리(4.184 J)이고 결과는 magnitude 와 unit 이다. 목록에 없는 단위(MJ, 국제표 칼로리 등)는 오류이다."""
        ...
    def fx_convert(self, amount: Num, from_ccy: Num, to_ccy: Num, rate: Num, rounding: Num = 'HALF_EVEN') -> _m133.FxConvertResult:
        """amount * rate 를 to_ccy 의 소수 자릿수로 반올림해 amount(문자열)와 currency 를 반환한다. 자릿수는 JPY, KRW 등 0, USD 등 2, KWD 등 3 이고 표에 없는 통화는 2 이다. rounding 은 HALF_EVEN(기본), HALF_UP, DOWN, UP, FLOOR, CEIL. rate 는 from_ccy 에서 to_ccy 방향의 양수이며 환율을 조회하지는 않는다."""
        ...
    def fx_triangulate(self, amount: Num, from_ccy: Num, via_ccy: Num, to_ccy: Num, rate1: Num, rate2: Num, rounding: Num = 'HALF_EVEN') -> _m133.FxTriangulateResult:
        """중간 통화를 거치는 삼각 환산 amount * rate1 * rate2 를 to_ccy 의 소수 자릿수로 한 번만 반올림해 amount(문자열)와 currency 를 반환한다. rate1 은 from_ccy 에서 via_ccy, rate2 는 via_ccy 에서 to_ccy 방향의 양수이며 중간 금액은 반올림하지 않는다. rounding 기본값은 HALF_EVEN 이다."""
        ...
    def pressure_convert(self, magnitude: Num, from_unit: Num, to_unit: Num) -> _m132.PressureConvertResult:
        """압력 단위를 Pa 기준 Decimal 계수로 변환한다. 지원 단위는 Pa, kPa, MPa, atm, bar, mbar, psi, mmHg, torr 이며 대소문자를 구분하고 magnitude 는 Decimal 문자열이다. 단순 배율 변환이라 게이지압과 절대압의 차이는 반영하지 않는다. 결과는 magnitude 와 unit 이다."""
        ...
    def temperature(self, value: Num, from_scale: Num, to_scale: Num) -> _m134.TemperatureResult:
        """섭씨(C), 화씨(F), 켈빈(K), 랭킨(R) 사이에서 온도를 변환한다. value 는 Decimal 문자열, from_scale 과 to_scale 은 대소문자 구분 없는 한 글자이며 결과는 value 와 대문자 scale 이다. 절대영도 미만 입력은 오류이다. 온도 차이(Δ)가 아닌 절대 온도 값 변환용이고, 5/9 계수는 유효 50자리로 근사한다."""
        ...
    def time_small_convert(self, magnitude: Num, from_unit: Num, to_unit: Num) -> _m132.TimeSmallConvertResult:
        """짧은 시간 단위 s, ms, us, ns, ps, min, hour, day 사이를 pint 로 변환한다. magnitude 는 Decimal 문자열이고 단위는 대소문자를 구분하며 1 day 는 86400 s 이다. 월과 연은 길이가 일정하지 않아 지원하지 않으므로 날짜 간격에는 datetime.diff 를 쓴다."""
        ...


accounting: _AccountingTools
core: _CoreTools
crypto: _CryptoTools
datetime: _DatetimeTools
engineering: _EngineeringTools
finance: _FinanceTools
geometry: _GeometryTools
math: _MathTools
medical: _MedicalTools
payroll: _PayrollTools
pm: _PmTools
probability: _ProbabilityTools
realestate: _RealestateTools
science: _ScienceTools
sootool: _SootoolTools
stats: _StatsTools
symbolic: _SymbolicTools
tax: _TaxTools
tax_us: _TaxUsTools
units: _UnitsTools
