# accounting 모듈

## 제공 도구

| 도구 | 설명 |
|-|-|
| `accounting.balance` | 차변/대변 균형 검증 |
| `accounting.depreciation_straight_line` | 정액법 감가상각 |
| `accounting.depreciation_declining_balance` | 정률법 감가상각 |
| `accounting.depreciation_units_of_production` | 생산량비례법 감가상각 |
| `accounting.vat_extract` | 공급대가 → 공급가액+VAT 역산 |
| `accounting.vat_add` | 공급가액 + VAT 가산 |

## 공식 출처

- 한국채택국제회계기준(K-IFRS) IAS 16 유형자산: 정액법, 정률법, 생산량비례법
- 부가가치세법 시행령 제60조: 공급가액 역산 시 원 단위 이하 절사(DOWN rounding)
- 국세청 부가세 계산기 기준: gross / (1 + rate), 원 단위 절사

## 내부 자료형 및 캐스팅 정책

- 전 구간 `decimal.Decimal` 사용. float 입력 금지.
- 입력/출력 모두 Decimal 문자열(str) 직렬화.
- `core.decimal_ops.D(x)` 함수로 파싱. float 전달 시 `TypeError` 발생.
- 반올림은 `core.rounding.apply(value, decimals, RoundingPolicy)` 단일 경로.

## 반올림 정책 기본값

| 도구 | 기본값 | 근거 |
|-|-|-|
| `vat_extract` | DOWN | 부가세법 시행령: 원 단위 이하 절사 |
| `vat_add` | HALF_EVEN | 회계 일반 관행 |
| `depreciation_*` | HALF_EVEN | K-IFRS 일반 관행 |

## ADR-007 준수 (전역 가변 상태 금지)

모든 도구는 순수 함수로 구현. 전역 상태 없음. `core.batch`로 N=100 병렬 호출 시 동일 결과 보장.
