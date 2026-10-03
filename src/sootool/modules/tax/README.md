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
| `tax.kr_income` | 한국 종합소득세 기본세율(소득세법 제55조) |
| `tax.kr_comprehensive_income_tax` | 종합소득세 신고 흐름: 근로, 사업, 이자, 배당, 연금, 기타소득 합산, 금융소득 비교과세, 세액공제, 지방소득세 |
| `tax.kr_withholding_simple` | 근로소득 간이세액표(소득세법 시행령 별표 2 전체를 정책 데이터로 내장, 시행일별 자녀 세액공제) |
| `tax.capital_gains_kr` | 양도소득세(1세대1주택 비과세, 고가주택 안분, 장기보유특별공제 표 1과 표 2, 단기보유, 중과) |
| `tax.kr_gift`, `tax.kr_inheritance` | 증여세, 상속세(공제 한도, 세대생략 할증, 신고세액공제) |
| `tax.kr_corporate`, `tax.kr_simplified_vat` | 법인세, 간이과세 부가가치세 |
| `tax.kr_eitc` | 근로장려금(시행령 별표 11 산정표) |
| `tax.kr_securities_transaction`, `tax.kr_pension_income` | 증권거래세와 농어촌특별세, 연금소득 원천징수와 분리과세 |
| `tax.kr_vehicle_tax`, `tax.kr_registration_license_tax` | 자동차세, 등록면허세 |
| `tax.kr_local_income_tax`, `tax.kr_education_tax_add`, `tax.kr_rural_special_tax` | 지방소득세, 지방교육세, 농어촌특별세 |

전체 목록과 설명은 `docs/tool_catalog.md`(레지스트리에서 생성)를 본다.

## 정책 YAML

`src/sootool/policies/tax/` 아래 정책 파일은 조문 인용(`citations`), 시행일(`effective_date`, `effective_to`), 상태(`status`)를
가진다. 연중 개정되는 값은 `이름_연도@시행일.yaml` 버전 파일로 나뉘고, 호출의 `as_of` 와 `include_proposed` 로 고른다.
구조는 `policy_mgmt/schemas.py` 의 스키마로 검증되며 `tests/policy_mgmt` 가 모든 패키지 정책을 검사한다.

## 끝수와 단위

세액의 끝수는 도구마다 법령에 따른다(예: 지방세는 10원 미만 버림). 도구 설명에 적용한 규칙이 적혀 있다.
원문에 규정이 없는 끝수는 원 미만 버림을 쓰고 설명에 명시한다.

## 구간 경계 정책

누진세율 구간은 lower-exclusive, upper-inclusive 방식을 따른다:
- 과세표준 = upper → 해당 구간에 포함됨
- 과세표준 = lower → 해당 구간에 포함되지 않음 (상위 구간 적용)
