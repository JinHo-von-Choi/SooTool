# realestate

한국 부동산 세금(취득세, 재산세, 종합부동산세, 양도소득세)과 대출 규제(LTV, DTI, DSR), 청약 가점, 임대수익률 도구. 법정 값은 연도별 정책 파일에 있고 각 파일의 `citations`에 근거 조문이 있다.

|도구|계산|엔진|정책|
|-|-|-|-|
|`realestate.kr_acquisition_tax`|한국 주택 유상취득 취득세와 농어촌특별세·지방교육세를 계산한다.|Decimal|예|
|`realestate.kr_comprehensive`|주택분 종합부동산세와 농어촌특별세(종부세의 20%)를 계산한다.|Decimal|예|
|`realestate.kr_dsr`|DSR(연간 원리금 상환액 / 연간 소득)을 계산하고 한도 이내인지 판정한다.|Decimal|예|
|`realestate.kr_dti`|DTI(월 원리금 상환액 / 월 소득)를 계산하고 한도 이내인지 판정한다.|Decimal|예|
|`realestate.kr_local_property`|광역자치단체별 조례 가감 계수로 주택 취득세 또는 재산세를 계산한다.|Decimal|예|
|`realestate.kr_ltv`|LTV(대출액 / 주택가액)를 계산하고 한도 이내 여부와 최대 대출액을 구한다.|Decimal|예|
|`realestate.kr_property_tax`|한국 주택 재산세(지방세법 §110~§111의2)와 지방교육세·도시지역분을 계산한다.|Decimal|예|
|`realestate.kr_subscription_score`|청약 가점(무주택기간 32, 부양가족 35, 청약통장 가입기간 17, 합계 84점)을 계산한다.|Decimal|예|
|`realestate.kr_transfer_tax`|부동산 양도소득세를 `tax.capital_gains_kr`에 위임해 계산한다.|Decimal|예|
|`realestate.rental_yield`|임대수익률을 백분율(%) 문자열로 계산한다.|Decimal||

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 정책 파일

|파일|내용|
|-|-|
|`policies/realestate/kr_acquisition_2026.yaml`|주택 취득세 표준세율, 중과세율, 농어촌특별세, 지방교육세|
|`policies/realestate/kr_property_tax_2026.yaml`|재산세 공정시장가액비율, 표준세율, 1세대 1주택 특례세율, 과세표준상한율|
|`policies/realestate/kr_comprehensive_2026.yaml`|주택분 종합부동산세(2026년 귀속)|
|`policies/realestate/kr_comprehensive_2027.yaml`|종합부동산세 정부 개정안(`status: proposed`, `include_proposed=true`일 때만 사용)|
|`policies/realestate/kr_local_property_2026.yaml`|광역별 취득세·재산세 계수와 도시지역분 여부|
|`policies/realestate/kr_dsr_ltv_2026.yaml`|DSR·LTV·DTI 한도, 주택가격별 주담대 한도, 스트레스 금리 하한|
|`policies/realestate/kr_subscription_2026.yaml`|청약 가점 산정 기준|

## 도구별 규칙 요약

### kr_dsr
DSR = 연간 원리금 상환액 / 연간 소득. 한도는 은행권 40%, 2금융권 50%(`is_nonbank`). `mortgage_region`을 주면 스트레스 금리 하한(수도권·규제지역 3%, 그 외 0.75%)을 돌려준다. 스트레스 DSR은 대출금리에 이 값을 더해 산정한 상환액으로 판정한다.

### kr_ltv
|구분|무주택(1주택 취득)|2주택 이상|
|-|-|-|
|규제지역|40%|0%(금지)|
|수도권 비규제지역|70%|0%(금지)|
|수도권 외 비규제지역|70%|60%|

생애최초는 수도권·규제지역 70%, 그 외 80%, 한도 6억 원. 수도권·규제지역 주택가격별 한도는 시가 15억 이하 6억, 25억 이하 4억, 25억 초과 2억이다. 최대 대출액 = min(시가 × LTV, 금액 한도).

### kr_dti
규제지역 40%, 규제지역 외 수도권(아파트 담보) 60%, 수도권 외 비규제지역은 한도 없음.

### kr_acquisition_tax
- 표준세율(지방세법 제11조제1항제8호): 6억 원 이하 1%, 6억 초과 9억 이하 (취득가액 × 2/3억 원 − 3) × 1/100(소수 넷째 자리 반올림), 9억 초과 3%
- 중과세율(지방세법 제13조의2): 조정대상지역 2주택·비조정 3주택 8%, 조정대상지역 3주택 이상·비조정 4주택 이상·법인 12%. 일시적 2주택 등 중과 제외는 `is_heavy_excluded`
- 농어촌특별세(전용 85m² 초과): 표준세율 0.2%, 중과 8%는 0.6%, 12%는 1.0%
- 지방교육세: 표준세율의 10%(0.1~0.3%), 중과 0.4%

### kr_property_tax
과세표준 = 공시가격 × 공정시장가액비율(일반 60%, 2026년 1세대 1주택 43/44/45%). 직전 연도 시가표준액을 주면 과세표준상한(5%)을 적용한다. 시가표준액 9억 이하 1세대 1주택은 특례세율(0.05~0.35%). 지방교육세 20%, 도시지역분 0.14%.

### kr_comprehensive
기본공제(1세대 1주택 12억, 그 외 9억, 법인 0), 공정시장가액비율 60%, 2주택 이하·3주택 이상 누진세율 또는 법인 2.7%·5.0%, 재산세 상당액 공제, 1세대 1주택자 연령·보유 공제(합계 80% 한도), 세부담상한 150%(`prior_year_total_tax`), 농어촌특별세 20%.

### kr_local_property
조례 가감세율(지방세법 제14조, 제111조제3항)을 광역 계수로 반영한다. 재산세 가감과 도시지역분은 자치구·시·군 조례 사항이므로 광역 계수는 대표값이다.

### rental_yield
총수익률 = 연 임대료 / 매매가 × 100, 순수익률 = (연 임대료 − 연 비용) / 매매가 × 100. 소수 2자리(기본 HALF_EVEN).
