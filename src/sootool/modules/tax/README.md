# Tax Module

Author: 최진호
Date: 2026-04-22

## 개요

세금 계산 도구 모음. 범용 누진세율 계산기, 한국 소득세, 간이 원천징수, 양도소득세를 제공한다.

## 내부 자료형 및 캐스팅 정책

ADR-008 준수: 세무 계산은 전 구간 `Decimal` 사용. `float` 사용 금지.
모든 입출력은 Decimal 문자열 형태이며, 내부에서도 `sootool.core.decimal_ops.D()` 로 변환한다.

## 도구 목록

| 도구 | 설명 |
|-|-|
| `tax.progressive` | 범용 누진세율 구간 계산기 |
| `tax.kr_income` | 한국 소득세 (소득세법 누진세율 YAML 참조) |
| `tax.kr_withholding_simple` | 근로소득 간이 원천징수세액 (간이세액표 근사) |
| `tax.capital_gains_kr` | 양도소득세 (장기보유특별공제 포함) |

## 정책 YAML

- `policies/tax/kr_income_2026.yaml`: 2026년 소득세율 구간
- `policies/tax/kr_withholding_2026.yaml`: 2026년 간이세액표 (근사 공식)
- `policies/tax/kr_capital_gains_2026.yaml`: 2026년 장기보유특별공제율

## 근사값 주의사항

`kr_withholding_2026.yaml` 및 `kr_capital_gains_2026.yaml`은 국세청 공식 2026년 발표 전
2025년 기준 근사값을 적용한다. 공식 발표 후 YAML 업데이트 필요.

간이세액표는 실제로 복잡한 룩업 테이블이나, 이 구현은 동일한 법령 산식을 공식으로 근사한다.

## 구간 경계 정책

누진세율 구간은 lower-exclusive, upper-inclusive 방식을 따른다:
- 과세표준 = upper → 해당 구간에 포함됨
- 과세표준 = lower → 해당 구간에 포함되지 않음 (상위 구간 적용)
