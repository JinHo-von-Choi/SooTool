# tax

한국 세금 도구와 범용 누진세 계산기. 미국 세금은 `tax_us` 네임스페이스에 있다. 모든 계산은 Decimal이며, 법정 값은 정책 파일에서 읽는다.

|도구|계산|엔진|정책|
|-|-|-|-|
|`tax.capital_gains_kr`|양도소득세를 계산한다(소득세법 제89조·제95조·제103조·제104조).|Decimal|예|
|`tax.kr_comprehensive_income_tax`|종합소득세 신고 흐름(소득금액 합산, 종합소득공제, 과세표준, 산출세액, 세액공제, 결정세액, 지방소득세 10%)을 계산한다.|Decimal|예|
|`tax.kr_corporate`|법인세를 계산한다(법인세법 제55조, 조세특례제한법 제132조).|Decimal|예|
|`tax.kr_education_tax_add`|지방교육세를 본세 × 부가세율로 계산한다(지방세법 제151조).|Decimal||
|`tax.kr_eitc`|근로장려금을 산정한다(조세특례제한법 제100조의3·제100조의5·제100조의7).|Decimal|예|
|`tax.kr_gift`|증여세를 계산한다(상속세및증여세법 제53조·제53조의2·제56조·제57조·제69조).|Decimal|예|
|`tax.kr_income`|소득세 산출세액을 소득세법 제55조 기본세율(6~45% 누진)로 계산한다.|Decimal|예|
|`tax.kr_inheritance`|상속세를 계산한다(상속세및증여세법 제18조~제21조·제24조·제26조·제69조).|Decimal|예|
|`tax.kr_local_income_tax`|개인 지방소득세를 소득세의 10%로 계산한다(지방세법 제92조).|Decimal||
|`tax.kr_pension_income`|연금계좌 인출의 원천징수, 분리과세 판정, 연금소득공제를 계산한다.|Decimal|예|
|`tax.kr_registration_license_tax`|부동산 등기의 등록면허세와 지방교육세를 계산한다(지방세법 제28조, 제151조).|Decimal|예|
|`tax.kr_rural_special_tax`|농어촌특별세를 계산한다(농어촌특별세법 제5조).|Decimal||
|`tax.kr_securities_transaction`|주식 양도 시 증권거래세와 농어촌특별세를 계산한다.|Decimal|예|
|`tax.kr_simplified_vat`|간이과세자 부가가치세를 계산한다(부가가치세법 제46조·제61조·제63조·제69조).|Decimal|예|
|`tax.kr_vehicle_tax`|승용자동차 자동차세 연세액과 지방교육세를 계산한다(지방세법 제127조, 제128조, 제151조).|Decimal|예|
|`tax.kr_withholding_simple`|근로소득 월 원천징수세액을 소득세법 시행령 별표 2 간이세액표로 구한다.|Decimal|예|
|`tax.progressive`|임의의 누진세율 구간표로 세액을 계산한다.|Decimal||

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

Decimal 전 구간 모듈이다. float64, numpy, mpmath 를 쓰지 않으므로 경계 변환도 없다.

### 캐스팅 정책

- 입력 숫자는 전부 십진 문자열이며 `core.decimal_ops.D()` 로 Decimal 로 읽는다. float 입력은 받지 않는다.
- 계산 결과는 `str(Decimal)` 또는 `str(round_apply(...))` 로 문자열 직렬화한다. `core.cast` 의 `decimal_to_float64`, `float64_to_decimal_str`, `mpmath_to_decimal` 은 쓰지 않는다.
- 반올림은 `core.rounding.apply(value, decimals, policy)`(= `round_apply`) 로 한다. 누진 구간 세액과 유효세율은 `progressive.py` 의 `_calc_progressive(total_tax, brackets, rounding, decimals)` 가 처리하고, 유효세율은 `round_apply(total_tax / taxable_income, 8, RoundingPolicy.HALF_UP)` 로 고정된다.
- 정책 인자가 있는 도구는 `progressive.py` 의 `_parse_rounding(rounding)` 이 `RoundingPolicy` 를 해석한다. 법령이 정한 절사·반올림은 `RoundingPolicy.DOWN`(예: 지방소득세 `kr_local_income_tax` 는 `decimals` 기본 0이라 원 미만을 버린다. 종합소득세 결정세액도 DOWN) 과 `RoundingPolicy.HALF_UP`(예: 양도소득세 `capital_gains_kr`) 로 고정돼 있다.
- 세율표·공제액·한도는 `sootool.policy_mgmt.loader.load` 로 정책 YAML(`policies/tax/*.yaml`)에서 읽는다. 워크로우 세액공제(`_credits.py`)도 같은 정책 파일의 값을 `D()` 로 읽어 쓴다.
- `kr_comprehensive_income_tax` 는 개인별·연말정산 계산의 허브 역할이라 `payroll.kr_year_end_tax_settlement` 도 이 모듈의 `_calc_progressive` 와 `_credits.py` 를 공유한다.

### 정밀도 한계

- 계산은 `decimal_ops` 컨텍스트(정밀도 50자리)에서 돈다. 결과는 십진 문자열이므로 소수점은 정확하다.
- 나눗셈이 반복 소수가 되는 값(유효세율, 세율 적용 금액)은 컨텍스트 정밀도에서 멈춘 뒤 지정 자릿수로 반올림된다.
- 세율표와 한도가 정책 파일에 묶여 있어 정책 연도나 `include_proposed` 설정이 바뀌면 결과가 달라진다. 응답의 `policy_version` 으로 확인한다.

## 정책 파일

`src/sootool/policies/tax/` 아래 파일에 세율표, 공제액, 한도가 근거 조문(`citations`), 시행일(`effective_date`, `effective_to`), 상태(`status`)와 함께 있다. 연중에 바뀌는 값은 `이름_연도@시행일.yaml`로 나뉘고 호출의 `as_of`로 고른다. 국회 확정 전 개정안은 `status: proposed`이며 `include_proposed=true`일 때만 쓴다. 모든 패키지 정책은 `policy_mgmt/schemas.py`의 구조 스키마로 검증된다.

## 끝수 처리

세액의 끝수는 법령을 따른다(예: 지방세 10원 미만 절사). 적용한 규칙은 도구 설명에 적혀 있다. 법령에 규정이 없는 끝수는 원 미만을 버리고 그 사실을 설명에 적는다.

## 누진 구간 경계

누진세율 구간은 하한 미포함, 상한 포함이다. 과세표준이 구간 상한과 같으면 그 구간에 속하고, 하한과 같으면 아래 구간에 속한다. 예: 2026년 소득세에서 과세표준 14,000,000원은 6% 구간의 끝이다.

## 함께 쓰는 도구

- 지방소득세: `tax.kr_local_income_tax(income_tax=<소득세액>)`. 과세표준이 아니라 산출된 소득세액을 넣는다.
- 근로소득자의 월 원천징수와 실수령액: `payroll.kr_salary`, `payroll.kr_bonus_tax`
- 부동산 양도소득세: `realestate.kr_transfer_tax`(이 모듈의 `capital_gains_kr`에 위임)

호출 예시는 [한국 세금 쿡북](../../../../docs/cookbook/tax_korea_2026.md)에 있다.
