# datetime_ 모듈

## 제공 도구

| 도구 | 설명 |
|-|-|
| `datetime.add_business_days` | 영업일 기준 날짜 가산 |
| `datetime.count_business_days` | 두 날짜 간 영업일 수 계산 |
| `datetime.day_count` | 이자 일수 및 연 분율 계산 |
| `datetime.age` | 만나이 계산 |
| `datetime.diff` | 두 날짜 간 기간 차이 |
| `datetime.tz_convert` | IANA 타임존 간 datetime 변환 |

## 공식 출처

- 만나이: 민법 제158조, 연령계산 기준 (생일 당일 증가)
- 영업일: `holidays` 패키지 (pypi.org/project/holidays) - 한국 공휴일 및 대체공휴일 포함
- 이자 일수 컨벤션: ISDA 2006 Definitions (30/360, ACT/ACT, ACT/365, ACT/360)
- 타임존: IANA Time Zone Database, stdlib `zoneinfo` (Python 3.9+)

## 이자 일수 컨벤션 (day_count)

| 컨벤션 | 분자 | 분모 | 설명 |
|-|-|-|-|
| 30/360 | 30/360 환산 일수 | 360 | 채권 기준 |
| ACT/365 | 실제 일수 | 365 | 고정 분모 |
| ACT/ACT | 실제 일수 | 해당 연도 실제 일수 | ISDA 표준 |
| ACT/360 | 실제 일수 | 360 | 머니마켓 |

30/360 공식: `360*(Y2-Y1) + 30*(M2-M1) + (D2-D1)` (D1=31→30, D2=31 and D1=30→30)

## 내부 자료형 및 캐스팅 정책

- 날짜 연산: `datetime.date`, `dateutil.relativedelta` 사용
- 이자 일수 year_fraction: `decimal.Decimal` 정밀 연산, 문자열 직렬화
- 타임존 변환: stdlib `zoneinfo.ZoneInfo`, float 없음
- `holidays.country_holidays(country, years=...)` - 공휴일 데이터는 년도별 캐시 불필요 (패키지 내부 처리)

## ADR-007 준수 (전역 가변 상태 금지)

- 공휴일 집합은 호출 시마다 생성. 전역 캐시 없음.
- 모든 도구 순수 함수. `core.batch` N=100 병렬 호출 시 동일 결과 보장.
