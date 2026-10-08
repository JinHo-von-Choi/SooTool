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

## 반올림 기본값

`break_even`은 고정비와 단위 변동비가 0 이상이고 판매 단가가 단위 변동비보다 클 때 사용한다. 유한한 Decimal 문자열을 입력하며 50자리 정밀도로 계산한다. 판매량은 기본 소수 4자리 HALF_EVEN 반올림한 문자열로 반환한다. 소수 판매량을 정수 판매 개수로 올림하지 않는다.

|도구|기본값|근거|
|-|-|-|
|`vat_extract`|DOWN|공급가액 역산 시 원 단위 미만 절사(부가가치세법 시행령 제60조, 국세청 계산 방식)|
|`vat_add`|HALF_EVEN|회계 일반 관행|
|`depreciation_*`|HALF_EVEN, 소수 0자리|K-IFRS 일반 관행. 마지막 해는 장부가가 잔존가치에 맞도록 조정|
|`ratios`, `dupont_*`|HALF_EVEN, 소수 4~6자리|비율은 배수로 반환(0.25 = 25%)|

## 출처

- 감가상각 3종: K-IFRS 제1016호(IAS 16) 유형자산
- 부가세 역산: 부가가치세법 시행령 제60조, 공급가액 = 공급대가 / (1 + 세율)
