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
