# units

물리 단위, 환율, 온도, 에너지, 압력, 데이터 크기, 짧은 시간 단위 변환 도구.

|도구|계산|엔진|
|-|-|-|
|`units.convert`|pint 로 물리 단위를 변환한다.|Decimal|
|`units.data_size_convert`|데이터 크기 단위를 바이트 기준으로 변환한다.|Decimal|
|`units.energy_convert`|에너지 단위를 J 기준 Decimal 계수로 변환한다.|Decimal|
|`units.fx_convert`|환율로 금액을 바꾸고 대상 통화의 소수 자릿수로 반올림한다.|Decimal|
|`units.fx_triangulate`|중간 통화를 거쳐 환산하고 마지막에 한 번만 반올림한다.|Decimal|
|`units.pressure_convert`|압력 단위를 Pa 기준 Decimal 계수로 변환한다.|Decimal|
|`units.temperature`|섭씨(C), 화씨(F), 켈빈(K), 랭킨(R) 사이에서 온도를 변환한다.|Decimal|
|`units.time_small_convert`|짧은 시간 단위 s, ms, us, ns, ps, min, hour, day 사이를 pint 로 변환한다.|Decimal|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

Decimal 전 구간 모듈이다. float64, numpy, mpmath 를 쓰지 않으므로 경계 변환도 없다. pint 를 쓰는 두 도구도 Decimal non-int 레지스트리로 돌린다.

|도구|내부 자료형|
|-|-|
|`convert`, `time_small_convert`|Decimal (pint `non_int_type=Decimal`)|
|`energy_convert`, `pressure_convert`, `data_size_convert`|Decimal (계수표)|
|`temperature`|Decimal (계수·스케일 상수)|
|`fx_convert`, `fx_triangulate`|Decimal|

### 캐스팅 정책

- 입력 숫자는 전부 십진 문자열이며 `core.decimal_ops.D()` 로 Decimal 로 읽는다. float 입력은 받지 않는다.
- `convert` 와 `time_small_convert` 는 `sootool.core.units._UREG` 로 만든 pint 레지스트리를 쓴다. 이 레지스트리는 `pint.UnitRegistry(non_int_type=Decimal)` 로 만들어 단위 계수가 Decimal 로 계산된다. 결과는 `str(converted.magnitude)` 로 문자열화한다.
- `energy_convert`, `pressure_convert`, `data_size_convert` 는 `D()` 로 만든 Decimal 계수표에 곱하고 나누기만 한다. `temperature` 는 `_ABS_ZERO`, `_KELVIN_OFFSET`, `_RANKINE_FACTOR` 같은 Decimal 상수로 스케일을 변환한다.
- 환율 도구는 `core.rounding.apply(value, decimals, policy)` 로 반올림한다. 정책은 `currency.py` 의 `_parse_policy(rounding)` 가 해석하고 기본값은 `HALF_EVEN` 이다. 자릿수는 ISO 4217 보조 단위 표에서 정한다(아래 "통화별 소수 자릿수" 절).
- `core.cast` 의 `decimal_to_float64`, `float64_to_decimal_str`, `mpmath_to_decimal` 은 쓰지 않는다.

### 정밀도 한계

- 계산은 `decimal_ops` 컨텍스트(정밀도 50자리)에서 돈다. 결과는 십진 문자열이므로 소수점은 정확하다.
- `convert` 와 `time_small_convert` 는 pint 가 정의한 단위 계수를 그대로 쓰므로 그 정의의 정밀도를 따른다. 1 day = 86400 s 같은 정수 계수는 정확하지만, 환율 같은 비정수 계수는 pint 정의 그대로다.
- `temperature` 는 5/9 같은 유리수를 `Decimal("5") / Decimal("9")` 로 계산하므로 결과는 소수 50자리에서 멈춘다. 이 때문에 `convert` 로 온도를 바꾸는 것보다 `units.temperature` 를 쓰는 편이 끝자리가 정확하다.
- `fx_triangulate` 는 중간 통화에서 반올림하지 않으므로 최종 결과가 `fx_convert` 와 달라질 수 있다.

## 사용 시 주의

- `convert`는 pint가 인식하는 단위 이름을 받는다(예: `"meter"`, `"kilogram"`, `"liter"`). 차원이 다른 단위끼리 바꾸면 `invalid_input`을 낸다.
- `temperature`의 척도는 `C`, `F`, `K`, `R`이다.
- 환율 도구는 환율을 조회하지 않는다. 호출자가 `rate`를 넘긴다.

## 통화별 소수 자릿수(ISO 4217)

환산 결과는 대상 통화의 보조 단위 자릿수로 반올림한다(기본 HALF_EVEN). `fx_triangulate`는 중간 통화 단계에서 반올림하지 않고 마지막에 한 번만 반올림한다.

|자릿수|통화|
|-|-|
|0|JPY, KRW, CLP, ISK, UGX, VND, BIF, COP, DJF, GNF, KMF, MGA, PYG, RWF, VUV, XAF, XOF, XPF|
|2|USD, EUR, GBP, AUD, CNY, HKD, CAD, SGD, CHF, SEK, NOK, DKK, NZD, MXN, INR, BRL, RUB, ZAR, TRY, THB, IDR, MYR, PHP, EGP, PLN, CZK, HUF, RON, AED, SAR, QAR, PKR, NGN, UAH|
|3|BHD, KWD, OMR, TND, JOD, IQD, LYD|

표에 없는 통화는 2자리로 처리한다. 전체 목록은 `currency.CURRENCY_DECIMALS`에 있다.
