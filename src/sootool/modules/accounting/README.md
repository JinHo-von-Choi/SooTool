# accounting

부가세, 감가상각, 재무제표 분석 도구. 모든 계산을 Decimal로 하며 전역 상태가 없어 `core.batch`로 병렬 호출해도 결과가 같다.

|도구|계산|엔진|
|-|-|-|
|`accounting.balance`|분개 목록의 차변 합계와 대변 합계가 같은지 검증한다.|Decimal|
|`accounting.break_even`|고정비 / (판매 단가 - 단위 변동비)로 손익분기 판매량을 계산한다.|Decimal|
|`accounting.cashflow_operating`|간접법 영업활동현금흐름(CFO)을 계산한다.|Decimal|
|`accounting.depreciation_declining_balance`|정률법 감가상각 스케줄을 계산한다.|Decimal|
|`accounting.depreciation_straight_line`|정액법 감가상각 스케줄을 계산한다.|Decimal|
|`accounting.depreciation_units_of_production`|생산량비례법 감가상각 스케줄을 계산한다.|Decimal|
|`accounting.dupont_3`|DuPont 3단계 분해로 ROE를 순이익률, 총자산회전율, 재무레버리지로 나눈다.|Decimal|
|`accounting.dupont_5`|DuPont 5단계 분해로 ROE를 세부담, 이자부담, 영업이익률, 총자산회전율, 재무레버리지로 나눈다.|Decimal|
|`accounting.income_statement`|다단계 손익계산서의 단계별 이익과 이익률을 계산한다.|Decimal|
|`accounting.ratios`|유동비율, 당좌비율, 부채비율, ROE, ROA 등 재무비율 8개를 계산한다.|Decimal|
|`accounting.vat_add`|공급가액에 부가세를 더해 공급대가를 계산한다.|Decimal|
|`accounting.vat_extract`|공급대가(부가세 포함 금액)에서 공급가액과 부가세를 역산한다.|Decimal|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

Decimal 전 구간 모듈이다. float64, numpy, mpmath 를 쓰지 않으므로 경계 변환도 없다. 위 표의 엔진 열이 전부 Decimal 인 이유다.

### 캐스팅 정책

- 입력 숫자는 전부 십진 문자열이며 `core.decimal_ops.D()` 로 Decimal 로 읽는다. float 입력은 받지 않는다.
- 계산 결과는 `str(Decimal)` 또는 `str(round_apply(...))` 로 문자열 직렬화한다. `core.cast` 의 `decimal_to_float64`, `float64_to_decimal_str`, `mpmath_to_decimal` 은 쓰지 않는다.
- 반올림은 `core.rounding.apply(value, decimals, policy)`(= `round_apply`) 로만 한다. 정책과 자릿수는 위 "반올림 기본값" 표를 따른다.
- Decimal 컨텍스트는 도구마다 다르다. `income_statement` 와 `ratios` 는 `localcontext(Context(prec=50))` 로 고정 50자리를 쓰고, `cashflow`·`depreciation`·`vat` 는 입력 자릿수에서 파생한 가변 정밀도(최소 50자리)를 쓴다. 어느 쪽이든 호출자의 Decimal 설정을 따르지 않는다.
- `balance`(분개 검증)는 `core.decimal_ops.add` / `sub` 로 합계만 내고 반올림하지 않는다.

### 정밀도 한계

- 계산은 위 컨텍스트 정밀도에서 돈다. 결과는 십진 문자열이므로 소수점은 정확하다.
- 나눗셈이 반복 소수가 되는 값(이익률, 재무비율)은 컨텍스트 정밀도에서 멈춘 뒤 지정 자릿수로 반올림된다.
- 모든 계산은 전역 상태 없이 동작하므로 `core.batch` 로 병렬 호출해도 결과가 같다.

## 반올림 기본값

`income_statement`는 모든 항목에 유한한 Decimal 문자열을 받으며 매출과 매출원가는 0 이상이어야 한다. 호출자의 Decimal 설정과 독립적인 50자리 정밀도로 계산한다. 이익 금액에는 별도 반올림을 적용하지 않고 이익률은 소수 6자리 HALF_EVEN으로 반환한다. 매출이 0이면 모든 이익률은 `0`이며 계산 범위를 초과하면 입력 오류를 반환한다.

`break_even`은 고정비와 단위 변동비가 0 이상이고 판매 단가가 단위 변동비보다 클 때 사용한다. 유한한 Decimal 문자열을 입력하며 50자리 정밀도로 계산한다. 판매량은 기본 소수 4자리 HALF_EVEN 반올림한 문자열로 반환한다. 소수 판매량을 정수 판매 개수로 올림하지 않는다.

|도구|기본값|근거|
|-|-|-|
|`vat_extract`|DOWN|공급가액 역산 시 원 단위 미만 절사(부가가치세법 시행령 제60조, 국세청 계산 방식)|
|`vat_add`|HALF_EVEN|회계 일반 관행|
|`depreciation_*`|HALF_EVEN, 소수 0자리|K-IFRS 일반 관행. 마지막 해는 장부가가 잔존가치에 맞도록 조정|
|`ratios`, `dupont_*`|HALF_EVEN, 소수 4~6자리|비율은 배수로 반환(0.25 = 25%)|

`ratios`는 모든 금액에 유한한 Decimal 문자열을 받는다. 호출자의 Decimal 설정과 독립적인 50자리 정밀도로 계산하며 `decimals`는 0 이상 정수여야 한다. 분모가 0이거나 계산 범위를 초과하면 입력 오류를 반환한다.

## 출처

- 감가상각 3종: K-IFRS 제1016호(IAS 16) 유형자산
- 부가세 역산: 부가가치세법 시행령 제60조, 공급가액 = 공급대가 / (1 + 세율)
