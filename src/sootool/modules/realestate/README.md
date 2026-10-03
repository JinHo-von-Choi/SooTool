# Realestate Module

한국 부동산 세금·대출 규제 계산 도구 모음. 연도별 정책 파일을 쓰며 각 정책 파일의 `citations` 에 근거 조문과 출처가 있다.

## 정책 파일

| 파일 | 내용 |
|-|-|
| `policies/realestate/kr_acquisition_2026.yaml` | 주택 취득세 표준세율, 중과세율, 농어촌특별세, 지방교육세 |
| `policies/realestate/kr_property_tax_2026.yaml` | 주택 재산세 공정시장가액비율, 표준세율, 1세대 1주택 특례세율, 과세표준상한율 |
| `policies/realestate/kr_comprehensive_2026.yaml` | 주택분 종합부동산세(2026년 귀속) |
| `policies/realestate/kr_comprehensive_2027.yaml` | 주택분 종합부동산세 정부 개정안(status: proposed, `include_proposed` 필요) |
| `policies/realestate/kr_local_property_2026.yaml` | 광역별 취득세·재산세 계수와 도시지역분 여부 |
| `policies/realestate/kr_dsr_ltv_2026.yaml` | DSR/LTV/DTI 한도, 주택가격별 주담대 한도, 스트레스 금리 하한 |

## 도구 목록

### realestate.kr_dsr

DSR(총부채원리금상환비율) 계산.

- 수식: DSR = 연간 원리금 상환액 / 연간 소득
- 한도: 은행권 40%, 2금융권 50% (`is_nonbank`)
- `mortgage_region` 을 주면 스트레스 금리 하한을 반환한다(수도권·규제지역 3%, 그 외 0.75%). 스트레스 DSR 로 판정하려면 대출금리에 이 값을 더해 산정한 상환액을 넣는다.

---

### realestate.kr_ltv

LTV(주택담보대출비율) 계산과 주택구입 주담대 한도 산출.

| 구분 | 무주택(1주택 취득) | 2주택 이상 |
|-|-|-|
| 규제지역 | 40% | 0% (금지) |
| 수도권 비규제지역 | 70% | 0% (금지) |
| 수도권 외 비규제지역 | 70% | 60% |

- 생애최초: 수도권·규제지역 70%, 그 외 80%, 6억 한도
- 수도권·규제지역 주택가격별 한도: 시가 15억 이하 6억, 25억 이하 4억, 25억 초과 2억
- `max_loan = min(시가 × LTV, 금액 한도)`

---

### realestate.kr_dti

DTI(총부채상환비율) 계산.

| 구분 | 한도 |
|-|-|
| 규제지역 | 40% |
| 규제지역 외 수도권(아파트 담보) | 60% |
| 수도권 외 비규제지역 | 없음 |

---

### realestate.kr_acquisition_tax

주택 유상취득 취득세 계산.

표준세율(지방세법 제11조제1항제8호):
- 6억원 이하: 1%
- 6억원 초과 9억원 이하: (취득가액 × 2/3억원 - 3) × 1/100, 소수점 이하 넷째자리까지 반올림
- 9억원 초과: 3%

중과세율(지방세법 제13조의2, 표준세율을 대체):
- 조정대상지역 2주택, 비조정 3주택: 8%
- 조정대상지역 3주택 이상, 비조정 4주택 이상, 법인: 12%
- 일시적 2주택 등 중과 제외 주택은 `is_heavy_excluded`

부가세:
- 농어촌특별세(전용 85m² 초과): 표준세율 0.2%, 중과 8%는 0.6%, 12%는 1.0%
- 지방교육세: 표준세율의 10%(0.1%~0.3%), 중과 0.4%

---

### realestate.kr_property_tax

주택 재산세. 과세표준 = 공시가격 × 공정시장가액비율(일반 60%, 2026년 1세대 1주택 43/44/45%), 직전 연도 시가표준액을 주면 과세표준상한(5%) 적용. 시가표준액 9억 이하 1세대 1주택은 특례세율(0.05~0.35%). 지방교육세 20%, 도시지역분 0.14%.

---

### realestate.kr_comprehensive

주택분 종합부동산세. 기본공제(1세대 1주택 12억, 그 외 9억, 법인 0), 공정시장가액비율 60%, 2주택 이하/3주택 이상 누진세율 또는 법인 2.7%/5.0%, 재산세 상당액 공제, 1세대 1주택자 연령·보유 공제(합계 80% 한도), 세부담상한 150%(`prior_year_total_tax`), 농어촌특별세 20%.

---

### realestate.kr_local_property

광역별 취득세·재산세. 조례 가감세율(지방세법 제14조, 제111조제3항)을 광역 계수로 반영한다. 재산세 가감과 도시지역분 고시는 자치구·시·군 조례 사항이라 광역 계수는 대표값이다.

---

### realestate.kr_transfer_tax

부동산 양도소득세 계산. `tax.capital_gains_kr` 에 위임하며 부동산 메타데이터 추가.

---

### realestate.rental_yield

임대수익률 계산.

- Gross: annual_rent / property_price × 100
- Net: (annual_rent - annual_expenses) / property_price × 100
- 결과: 백분율(%), 소수점 2자리 (HALF_EVEN 기본)
