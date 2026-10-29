# payroll

한국 급여 도구. 월급 명세서(4대보험·소득세·지방소득세), 상여금 세액, 연말정산, 퇴직소득세, 주휴수당, 연장·야간·휴일근로수당, 지급액 기준 세액공제(기부금·교육비·의료비·주거대출), 국민연금 노령연금, 최저임금 검토를 다룬다.

|도구|계산|엔진|
|-|-|-|
|`payroll.hourly_to_monthly_net`|시급을 월급으로 환산해 4대보험과 간이세액을 공제한 실수령액을 구한다.|Decimal|
|`payroll.kr_salary`|세전 월급에서 4대보험과 간이세액표를 적용한 실수령액을 구한다.|Decimal|
|`payroll.kr_bonus_tax`|상여금 원천징수세액을 근로소득 간이세액표로 구한다.|Decimal|
|`payroll.kr_gross_from_net`|세후 월급에서 세전 월급을 역산한다.|Decimal|
|`payroll.kr_year_end_tax_settlement`|연말정산 환급 또는 추가납부액을 계산한다.|Decimal|
|`payroll.kr_severance_pay`|퇴직소득세를 계산한다.|Decimal|
|`payroll.kr_weekly_holiday_pay`|주휴수당을 계산한다.|Decimal|
|`payroll.kr_overtime_pay`|연장·야간·휴일근로수당을 계산한다.|Decimal|
|`payroll.kr_national_pension_benefit`|국민연금 노령연금 예상액을 계산한다.|Decimal|
|`payroll.kr_health_income_premium`|건강보험 보수 외 소득월액보험료와 장기요양보험료를 계산한다.|Decimal|
|`payroll.kr_donation_deduction`|기부금 세액공제를 계산한다.|Decimal|
|`payroll.kr_education_deduction`|교육비 세액공제를 계산한다.|Decimal|
|`payroll.kr_medical_deduction`|의료비 세액공제를 계산한다.|Decimal|
|`payroll.kr_housing_loan_deduction`|장기주택저당차입금 이자상환액 소득공제 대상액을 계산한다.|Decimal|
|`payroll.kr_minimum_wage_check`|한국 최저임금 충족 여부를 검토한다.|Decimal|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

Decimal 전 구간 모듈이다. float64, numpy, mpmath 를 쓰지 않으므로 경계 변환도 없다.

### 캐스팅 정책

- 입력 숫자는 전부 십진 문자열이며 `core.decimal_ops.D()` 로 Decimal 로 읽는다. `D()` 는 float 을 받으면 `allow_float=True` 없이는 `FloatInputError` 를 내므로 이 모듈은 float 입력을 받지 않는다.
- 계산 결과는 `str(Decimal)` 로 문자열 직렬화한다. `core.cast` 의 `decimal_to_float64`, `float64_to_decimal_str`, `mpmath_to_decimal` 을 쓰지 않는다.
- 반올림은 `core.rounding.apply(value, decimals, policy)`(= `round_apply`) 로만 한다. 정책과 자릿수는 법령이 정한 대로 고정돼 있고 호출자가 바꾸지 못한다.
- 4대보험료의 단위 미만 처리는 `core.rounding.truncate_to_unit(value, unit)` 이 0 방향으로 정확히 버린다. 국민연금 기준은 천원(`base_truncation_unit`), 건강보험·장기요양 보험료 기준은 10원(`premium_truncation_unit`)이며 두 값 모두 정책 파일에서 온다.
- 월급 원천징수 지방소득세는 **징수 단계**라서 끝수 단위가 10원이다. 「국고금 관리법」 제47조제1항(국고금의 수입·지출에서 10원 미만 끝수는 계산하지 아니한다)을 「지방세기본법」 제59조가 지방자치단체 징수금에 준용한다. 단위는 정책 키 `local_income_tax.truncation_unit` 에서 온다. 산출세액 단계(「지방세법」 제92조제3항, `tax.kr_local_income_tax`·`tax.kr_comprehensive_income_tax`)와 구분된다.
- `kr_gross_from_net` 은 목표 실수령액을 달성하는 최소 정수 월급을 찾기 위해 `to_integral_value(rounding="ROUND_CEILING")` 을 쓴다.

|도구|반올림|
|-|-|
|`kr_salary`, `hourly_to_monthly_net`, `kr_bonus_tax`, `kr_year_end_tax_settlement`, `kr_donation_deduction`, `kr_education_deduction`, `kr_medical_deduction`, `kr_health_income_premium`, `kr_national_pension_benefit`|원 단위 절사(`RoundingPolicy.DOWN`, 소수 0자리)|
|`kr_salary` 의 지방소득세|10원 단위 절사(징수 끝수, `local_income_tax.truncation_unit`)|
|`kr_severance_pay`|원 단위 반올림(`RoundingPolicy.HALF_UP`, 소수 0자리)|
|`kr_overtime_pay`|시급 환산값 소수 2자리 `HALF_UP`|
|`kr_minimum_wage_check`|시급 환산값 소수 2자리 `DOWN`, 부족액은 `CEIL`|
|`kr_weekly_holiday_pay`|중간값 소수 6자리 `HALF_UP` 후 정책별 반올림|
|`kr_housing_loan_deduction`, `kr_gross_from_net`|반올림 없음|

### 정밀도 한계

- 계산은 `decimal_ops` 가 설정한 Decimal 컨텍스트(정밀도 50자리)에서 돈다. 결과는 십진 문자열이므로 소수점은 정확하다.
- 나눗셈이 반복 소수가 되는 값(예: 간이세액표 조회 결과의 비율)은 컨텍스트 정밀도 50자리에서 멈춘다.
- `kr_gross_from_net` 은 정수 월급을 올림해 찾으므로 목표 실수령액과 정확히 같은 실수령액은 항상 가능하지 않다. 결과의 `residual` 로 차이를 확인한다.

## 사용 시 주의

- 금액 단위는 원이고 입력은 십진 문자열로 받는다.
- `kr_salary` 의 간이세액표는 소득세법 시행령 별표 2 기준이며 `kr_bonus_tax` 는 제136조 평균지급 방식을 기본으로 한다.
- 법정 한도와 요율은 정책 파일에서 읽는다. 연도 값이 다르면 결과가 달라진다.
