# datetime

날짜 계산 도구. 만 나이, 날짜 차이, 한국 공휴일을 반영한 영업일, 이자 일수 관행, 시간대 변환, 음양력 변환, 24절기, 회계연도와 과세기간을 다룬다. 네임스페이스 이름은 `datetime`이고 파이썬 표준 모듈과 겹치지 않도록 패키지 디렉터리만 `datetime_`이다.

|도구|계산|엔진|
|-|-|-|
|`datetime.add_business_days`|시작일에 영업일 수를 더하거나 뺀 날짜를 구한다.|Decimal|
|`datetime.age`|만 나이를 년, 월, 일로 계산한다.|Decimal|
|`datetime.count_business_days`|두 날짜 사이의 영업일 수를 센다.|Decimal|
|`datetime.day_count`|이자 계산용 일수와 연 환산 비율을 구한다.|Decimal|
|`datetime.diff`|두 날짜의 차이를 지정한 단위(일, 주, 월, 년)로 구한다.|Decimal|
|`datetime.fiscal_quarter`|기준일이 속한 회계분기와 시작·종료일을 구한다.|Decimal|
|`datetime.fiscal_year`|기준일이 속한 회계연도와 시작·종료일을 구한다.|Decimal|
|`datetime.lunar_holiday`|음력 명절을 양력 solar_date 로 환산한다.|Decimal|
|`datetime.lunar_to_solar`|음력 날짜를 양력으로 바꾼다.|Decimal|
|`datetime.payroll_period`|기준일이 속한 월 급여 정산 기간을 구한다.|Decimal|
|`datetime.solar_terms`|해당 연도 24절기의 양력 날짜를 구한다.|Decimal|
|`datetime.solar_to_lunar`|양력 날짜를 음력 날짜와 윤달 여부로 바꾼다.|Decimal|
|`datetime.tax_period_kr`|기준일이 속한 소득세 과세기간(소득세법 제5조)을 구한다.|Decimal|
|`datetime.tz_convert`|IANA 시간대 사이에서 시각을 변환한다.|Decimal|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 이자 일수 관행 (day_count)

|관행|분자|분모|주 용도|
|-|-|-|-|
|30/360|30일 월 기준 환산 일수|360|채권|
|ACT/365|실제 일수|365|원화 대출·예금|
|ACT/ACT|실제 일수|해당 연도 실제 일수(ISDA)|국채|
|ACT/360|실제 일수|360|머니마켓|

30/360 일수 = 360·(Y2−Y1) + 30·(M2−M1) + (D2−D1). D1이 31이면 30으로, D1이 30 이상이고 D2가 31이면 D2도 30으로 바꾼다.

## 출처

- 만 나이: 민법 제158조(연령 계산), 생일 당일에 한 살 증가
- 공휴일: `holidays` 패키지의 한국 공휴일(대체공휴일 포함)
- 이자 일수: 2006 ISDA Definitions
- 시간대: IANA Time Zone Database(표준 라이브러리 `zoneinfo`)
