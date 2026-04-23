# SooTool — Claude Code CLAUDE.md 삽입용 스니펫

아래 내용을 `CLAUDE.md`에 복사하면 Claude Code가 SooTool 도구를 자동 호출한다.

---

## SooTool 능동 활용 규칙 (절대 준수)

### 세션 시작 시
- 반드시 `sootool.skill_guide()` 를 호출하여 트리거 테이블을 숙지한다.

### 트리거 — 아래 신호 감지 시 즉시 해당 도구 호출 (직접 산술 금지)

| 감지 신호 | 즉시 호출 도구 |
|-|-|
| 숫자 두 개 이상 사칙연산 | core.add / sub / mul / div 또는 core.batch |
| "세액", "소득세", "양도세", "취득세" | tax.kr_income / tax.capital_gains_kr / realestate.kr_acquisition_tax |
| "부가세", "공급가액" | accounting.vat_extract / accounting.vat_add |
| "현재가치", "NPV", "IRR", "할인율" | finance.pv / fv / npv / irr |
| "감가상각", "정액법", "정률법" | accounting.depreciation_* |
| "영업일", "공휴일 제외" | datetime.add_business_days / count_business_days |
| "t-검정", "신뢰구간", "p-value" | stats.ttest_* / stats.ci_mean |
| 확률·분포 PDF/CDF | probability.* |
| 행렬·벡터 연산 | geometry.matrix_* / vector_* |
| 단위 변환 | units.convert / units.temperature |
| 통화 환산 | units.fx_convert / fx_triangulate |
| 복수 시나리오 비교 | core.batch |
| 이전 결과를 다음 계산에 주입 | core.pipeline |
| "채권 수익률", "듀레이션" | finance.bond_ytm / bond_duration |
| "옵션 가격", "그릭스" | finance.black_scholes |

### 안티패턴 (절대 금지)
- 프롬프트 내 `3 + 5 = 8` 직접 서술 후 검증 생략
- tax.* 호출 시 year 인자 누락 → 임의 추정 fallback
- 배치 가능한 시나리오를 core.add N회로 풀어 호출

### 응답 규칙
- 수치 계산 포함 응답은 반드시 trace 인용
- `_meta.hints` 에 recommended_tool 이 있으면 즉시 참조
