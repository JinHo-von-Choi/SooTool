# Realestate Module

한국 부동산 금융 계산 도구 모음. 2026년 기준 정책 적용.

## 정책 파일

| 파일 | 내용 |
|-|-|
| `policies/realestate/kr_acquisition_2026.yaml` | 취득세율 및 다주택 중과세 |
| `policies/realestate/kr_dsr_ltv_2026.yaml` | DSR/LTV/DTI 한도 |

## 도구 목록

### realestate.kr_dsr

DSR(총부채원리금상환비율) 계산.

**수식**: DSR = 연간 원리금 상환액 / 연간 소득  
**한도**: 40% (금융위원회 DSR 규제)

**출처**: 금융위원회 DSR 규제 (https://www.fsc.go.kr/)

---

### realestate.kr_ltv

LTV(주택담보대출비율) 계산 및 최대 대출 한도 산출.

**수식**: LTV = 대출액 / 주택가액

| 구분 | 1주택 | 다주택 |
|-|-|-|
| 규제지역 | 50% | 0% (금지) |
| 비규제지역 | 70% | 60% |

---

### realestate.kr_dti

DTI(총부채상환비율) 계산.

**수식**: DTI = 월 원리금 상환액 / 월 소득

| 구분 | 한도 |
|-|-|
| 규제지역 | 40% |
| 비규제지역 | 60% |

---

### realestate.kr_acquisition_tax

주택 취득세 계산.

**기본세율** (지방세법 제11조):
- 6억원 이하: 1%
- 6억원 초과 ~ 9억원: 2%
- 9억원 초과: 3%

**다주택 중과세율**:
- 2주택 규제지역: 8%
- 3주택 이상: 12%
- 2주택 비규제지역: 0% (중과 없음)

**부가세**:
- 농어촌특별세: 0.2% (전용면적 85m² 초과)
- 지방교육세: 0.1%

**출처**: 행정안전부 지방세법 제11조 (https://www.law.go.kr/)

---

### realestate.kr_transfer_tax

부동산 양도소득세 계산. `tax.capital_gains_kr`에 위임하며 부동산 메타데이터 추가.

**출처**: 소득세법 제95조 (장기보유특별공제 포함)

---

### realestate.rental_yield

임대수익률 계산.

**수식**:
- Gross: annual_rent / property_price × 100
- Net: (annual_rent - annual_expenses) / property_price × 100

**결과**: 백분율(%), 소수점 2자리 (HALF_EVEN 기본)
