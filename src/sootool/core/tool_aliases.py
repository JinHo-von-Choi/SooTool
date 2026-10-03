"""도구 검색용 별칭(동의어, 약어, 일상 표현).

도구 설명은 법령 용어(양도소득세, 종합부동산세)를 쓰지만 사용자는 줄임말과 일상 표현(양도세,
종부세, 집 팔 때 세금)으로 찾는다. ``sootool.search`` 의 점수 계산이 이 표를 함께 본다. 이름과
설명에 이미 있는 단어는 적지 않는다. 도구 이름이 바뀌면 ``tests/core/test_catalog_aliases.py`` 가
존재하지 않는 도구를 가리키는 항목을 잡아낸다.

작성자: 최진호
작성일: 2026-10-03
"""
from __future__ import annotations

from typing import Final

ALIASES: Final[dict[str, tuple[str, ...]]] = {
    # 세금
    "tax.capital_gains_kr":              ("양도세", "집 팔 때 세금", "장기보유특별공제", "capital gains tax korea"),
    "realestate.kr_transfer_tax":        ("양도세", "부동산 양도세", "집 팔 때 세금", "주택 양도"),
    "realestate.kr_acquisition_tax":     ("취득세", "집 살 때 세금", "주택 구입 세금", "등기"),
    "realestate.kr_comprehensive":       ("종부세", "보유세", "종합부동산세"),
    "realestate.kr_property_tax":        ("재산세", "보유세", "공시가격", "공시가액"),
    "realestate.kr_local_property":      ("지자체 세율", "서울 경기 세율", "탄력세율"),
    "realestate.kr_ltv":                 ("담보인정비율", "대출 한도", "주택담보대출"),
    "realestate.kr_dti":                 ("총부채상환비율", "대출 한도", "대출 규제"),
    "realestate.kr_dsr":                 ("총부채원리금상환비율", "대출 한도", "대출 규제"),
    "realestate.rental_yield":           ("월세 수익률", "임대 수익", "수익형 부동산"),
    "tax.kr_income":                     ("소득세", "종합소득세", "근로소득세", "종소세", "income tax korea"),
    "tax.kr_corporate":                  ("법인세", "법인 세금", "corporate tax korea"),
    "tax.kr_gift":                       ("증여", "증여세", "자녀에게 증여", "gift tax"),
    "tax.kr_inheritance":                ("상속", "상속세", "유산", "inheritance tax"),
    "tax.kr_simplified_vat":             ("간이과세", "부가세", "부가가치세", "소규모 사업자 부가세"),
    "tax.kr_local_income_tax":           ("지방소득세", "주민세", "소득세의 10%"),
    "tax.kr_education_tax_add":          ("지방교육세", "교육세"),
    "tax.kr_rural_special_tax":          ("농특세", "농어촌특별세", "농특세 20%"),
    "tax.kr_withholding_simple":         ("원천징수", "간이세액표", "월급 원천징수", "withholding"),
    "tax.progressive":                   ("누진세", "세율 구간", "bracket", "progressive tax"),
    "tax_us.federal_income":             ("미국 소득세", "IRS", "us income tax", "federal tax"),
    "tax_us.capital_gains":              ("미국 양도세", "미국 주식 양도", "us capital gains"),
    "tax_us.state_tax":                  ("미국 주세", "캘리포니아", "뉴욕", "텍사스", "state income tax"),
    # 급여
    "payroll.kr_salary":                 ("실수령액", "월급 실수령", "연봉 실수령", "세후 월급", "4대보험", "net salary", "take-home pay"),
    "payroll.hourly_to_monthly_net":     ("시급", "알바", "아르바이트", "시급 월급 환산", "hourly wage"),
    "payroll.kr_severance_pay":          ("퇴직금", "퇴직소득세", "퇴직할 때 세금", "severance"),
    "payroll.kr_year_end_tax_settlement":("연말정산", "환급", "13월의 월급", "공제 합산"),
    "payroll.kr_bonus_tax":              ("상여", "보너스", "성과급", "상여금 세금", "bonus tax"),
    "payroll.kr_medical_deduction":      ("의료비", "병원비 공제", "난임"),
    "payroll.kr_education_deduction":    ("교육비", "학원비 공제", "자녀 교육비"),
    "payroll.kr_donation_deduction":     ("기부금", "기부 공제", "donation"),
    "payroll.kr_housing_loan_deduction": ("주택담보 이자", "대출 이자 공제", "장기주택저당차입금"),
    # 회계
    "accounting.vat_add":                ("부가세", "부가가치세", "VAT", "공급가액", "세금 더하기"),
    "accounting.vat_extract":            ("부가세 역산", "VAT 분리", "공급가액 구하기", "세금 빼기", "부가세 포함 금액"),
    "accounting.depreciation_straight_line": ("감가상각", "정액법", "depreciation"),
    "accounting.depreciation_declining_balance": ("감가상각", "정률법"),
    "accounting.depreciation_units_of_production": ("감가상각", "생산량 비례"),
    "accounting.balance":                ("대차 균형", "차변 대변", "분개 검증", "trial balance"),
    "accounting.ratios":                 ("재무비율", "부채비율", "유동비율", "financial ratios"),
    "accounting.income_statement":       ("손익계산서", "영업이익", "income statement", "P&L"),
    "accounting.cashflow_operating":     ("현금흐름", "영업활동", "CFO", "cash flow"),
    # 금융
    "finance.loan_schedule":             ("대출 상환", "이자 계산", "원리금균등", "원금균등", "할부", "amortization", "mortgage", "loan"),
    "finance.pv":                        ("현재가치", "할인", "discount"),
    "finance.fv":                        ("미래가치", "복리", "compound interest", "적금", "예금 만기"),
    "finance.npv":                       ("순현재가치", "투자 타당성", "현금흐름 할인"),
    "finance.irr":                       ("내부수익률", "투자 수익률", "internal rate of return"),
    "finance.bond_ytm":                  ("채권 수익률", "만기수익률", "yield to maturity"),
    "finance.black_scholes":             ("옵션 가격", "블랙숄즈", "option pricing"),
    "finance.var_historical":            ("위험가치", "손실 한도", "value at risk"),
    "finance.sharpe_ratio":              ("샤프지수", "위험조정수익률"),
    # 날짜
    "datetime.age":                      ("만 나이", "나이 계산", "생일", "법정 나이", "age"),
    "datetime.add_business_days":        ("영업일 더하기", "근무일 계산", "휴일 제외", "business days"),
    "datetime.count_business_days":      ("영업일 수", "근무일 수", "공휴일 제외 일수"),
    "datetime.diff":                     ("날짜 차이", "며칠 남았", "D-day", "기간 계산", "date difference"),
    "datetime.day_count":                ("이자 일수", "일수 계산", "30/360", "ACT/365"),
    "datetime.lunar_to_solar":           ("음력 양력 변환", "음력 생일", "lunar calendar"),
    "datetime.solar_to_lunar":           ("양력 음력 변환", "음력 날짜"),
    "datetime.lunar_holiday":            ("설날", "추석", "명절", "대보름", "초파일"),
    "datetime.solar_terms":              ("절기", "입춘", "동지", "24절기"),
    "datetime.tz_convert":               ("시차", "시간대 변환", "timezone"),
    "datetime.tax_period_kr":            ("과세기간", "과세 기간 판정"),
    "datetime.payroll_period":           ("급여 주기", "월급일 기준 기간"),
    # 단위
    "units.fx_convert":                  ("환율", "환전", "달러 원화", "currency exchange"),
    "units.fx_triangulate":              ("삼각 환율", "교차 환율", "cross rate"),
    "units.temperature":                 ("섭씨", "화씨", "온도 변환"),
    "units.convert":                     ("단위 변환", "unit conversion"),
    # 의료
    "medical.bmi":                       ("비만도", "체질량지수", "body mass index"),
    "medical.bsa":                       ("체표면적", "body surface area"),
    "medical.egfr":                      ("신장 기능", "사구체 여과율", "kidney function"),
    "medical.pregnancy_weeks":           ("임신 주수", "출산 예정일", "due date"),
    # 통계
    "stats.ttest_two_sample":            ("t 검정", "두 집단 비교", "평균 차이 검정"),
    "stats.ttest_one_sample":            ("t 검정", "표본 평균 검정"),
    "stats.ttest_paired":                ("대응표본", "전후 비교", "paired t-test"),
    "stats.anova_oneway":                ("분산분석", "세 집단 이상 비교", "ANOVA"),
    "stats.regression_linear":           ("회귀분석", "선형회귀", "추세선", "linear regression"),
    "stats.descriptive":                 ("기술통계", "평균 표준편차", "summary statistics"),
    "stats.ci_mean":                     ("신뢰구간", "confidence interval"),
    "stats.chi_square_independence":     ("카이제곱", "독립성 검정", "교차표"),
    "stats.mann_whitney_u":              ("비모수 검정", "만휘트니"),
    "stats.bootstrap_ci":                ("부트스트랩", "재표본"),
    # 프로젝트 관리와 계산
    "pm.critical_path":                  ("주공정", "크리티컬 패스", "CPM", "일정 계획"),
    "pm.evm":                            ("획득가치", "EVM", "비용 성과", "일정 성과"),
    "pm.pert":                           ("PERT", "낙관 비관 추정", "일정 추정"),
    "pm.monte_carlo_schedule":           ("몬테카를로", "일정 불확실성", "완료 확률"),
    "core.calc":                         ("수식 계산", "계산기", "expression", "식 평가", "sqrt sin log"),
    "core.add":                          ("더하기", "합계", "sum"),
    "core.sub":                          ("빼기", "차이"),
    "core.mul":                          ("곱하기", "곱셈"),
    "core.div":                          ("나누기", "나눗셈"),
    "core.batch":                        ("일괄 계산", "병렬 계산", "여러 건", "bulk"),
    "core.pipeline":                     ("연속 계산", "단계별 계산", "체인", "workflow"),
    "sootool.verify_receipt":            ("영수증 검증", "계산 증빙", "재실행 검증", "receipt"),
}
