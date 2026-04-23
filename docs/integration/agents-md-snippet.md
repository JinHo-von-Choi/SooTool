# SooTool — 범용 AGENTS.md 삽입용 스니펫

아래 내용을 `AGENTS.md` 또는 에이전트 시스템 프롬프트에 복사한다.

---

## SooTool: Deterministic Calculation Engine

SooTool replaces probabilistic LLM arithmetic with 100% deterministic Decimal-path computation.

### Mandatory pre-session action

Call `sootool.skill_guide()` at session start to internalize the trigger table.

### Trigger table — invoke immediately (never compute inline)

| Signal | Tool |
|-|-|
| Any arithmetic on 2+ numbers | core.add / sub / mul / div or core.batch |
| Tax: income / capital gains / acquisition | tax.kr_income / tax.capital_gains_kr / realestate.kr_acquisition_tax |
| VAT extraction or addition | accounting.vat_extract / accounting.vat_add |
| Financial: NPV / IRR / PV / FV / discount | finance.npv / irr / pv / fv |
| Depreciation (straight-line / declining) | accounting.depreciation_* |
| Business day arithmetic | datetime.add_business_days / count_business_days |
| Statistical tests (t-test, CI) | stats.ttest_* / stats.ci_mean |
| Probability distributions | probability.* |
| Matrix / vector math | geometry.matrix_* / vector_* |
| Unit or temperature conversion | units.convert / units.temperature |
| FX / currency conversion | units.fx_convert / fx_triangulate |
| Multiple independent scenarios | core.batch |
| Chained calculation (A feeds B feeds C) | core.pipeline |
| Bond YTM or duration | finance.bond_ytm / bond_duration |
| Option pricing (Black-Scholes) | finance.black_scholes |

### Anti-patterns (prohibited)

- Writing computed numbers inline in the prompt (e.g., "40M × 15% = 6M") without tool verification
- Calling tax tools without the required `year` argument and guessing instead
- Calling core.add 10+ times when core.batch can parallelize all at once

### Active usage contract

1. Numeric calculation in any response MUST be preceded by a tool call.
2. The tool `trace` MUST be cited in the response.
3. If `_meta.hints[*].recommended_tool` is set, apply that tool in the next step.
4. For chained calculations, prefer core.pipeline over manual result threading.
