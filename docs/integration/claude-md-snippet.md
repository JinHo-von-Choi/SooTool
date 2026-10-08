# Claude Code용 SooTool 규칙

프로젝트나 사용자 `CLAUDE.md`에 구분선 아래 내용을 붙여 넣는다. Claude Code가 숫자 계산을 직접 하지 않고 SooTool 도구를 부르게 된다.

---

## SooTool 사용 규칙

### 세션 시작 시
- 반드시 `sootool.skill_guide()` 를 호출하여 트리거 테이블을 숙지한다.

### 아래 요청이 보이면 직접 계산하지 말고 해당 도구를 호출한다

| 감지 신호 | 즉시 호출 도구 |
|-|-|
| 숫자 두 개 이상 사칙연산 | core.add / sub / mul / div 또는 core.batch |
| "세액", "소득세", "양도세", "취득세" | tax.kr_income / tax.capital_gains_kr / realestate.kr_acquisition_tax |
| "부가세", "공급가액" | accounting.vat_extract / accounting.vat_add |
| "현재가치", "NPV", "IRR", "할인율" | finance.pv / fv / npv / irr |
| "감가상각", "정액법", "정률법" | accounting.depreciation_* |
| "영업일", "공휴일 제외" | datetime.add_business_days / count_business_days |
| "t-검정", "신뢰구간", "p-value" | stats.ttest_* / stats.ci_mean |
| 확률·분포 PDF/CDF | probability.* |
| 행렬·벡터 연산 | geometry.matrix_* / vector_* |
| 단위 변환 | units.convert / units.temperature |
| 통화 환산 | units.fx_convert / fx_triangulate |
| 복수 시나리오 비교 | core.batch |
| 이전 결과를 다음 계산에 주입 | core.pipeline |
| "채권 수익률", "듀레이션" | finance.bond_ytm / bond_duration |
| "옵션 가격", "그릭스" | finance.black_scholes |
| "근로장려금" | tax.kr_eitc |
| "종합소득세 신고", "금융소득 종합과세" | tax.kr_comprehensive_income_tax |
| "증권거래세", "연금소득", "자동차세", "등록면허세" | tax.kr_securities_transaction / kr_pension_income / kr_vehicle_tax / kr_registration_license_tax |
| "연장·야간·휴일수당", "주휴수당", "최저임금" | payroll.kr_overtime_pay / kr_weekly_holiday_pay / kr_minimum_wage_check |
| "국민연금 수령액", "소득월액보험료" | payroll.kr_national_pension_benefit / kr_health_income_premium |
| "세후에서 세전 역산" | payroll.kr_gross_from_net / core.solve_for |
| "청약 가점" | realestate.kr_subscription_score |
| "미국 급여세", "FICA" | tax_us.fica |

### 하지 말 것
- 프롬프트 내 `3 + 5 = 8` 직접 서술 후 검증 생략
- tax.* 호출 시 year 인자 누락 → 임의 추정 fallback
- 배치 가능한 시나리오를 core.add N회로 풀어 호출

### 응답 규칙
- 수치 계산 포함 응답은 반드시 trace 인용
- `_meta.hints` 에 recommended_tool 이 있으면 즉시 참조
