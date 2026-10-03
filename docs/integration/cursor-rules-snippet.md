# SooTool, Cursor .cursorrules 삽입용 스니펫

아래 내용을 `.cursorrules` 파일에 복사한다.

---

## SooTool MCP Active Usage Rules

At session start: call `sootool.skill_guide()` to load the trigger table.

### Trigger table, call the tool immediately on these signals (no inline arithmetic)

| Signal | Tool |
|-|-|
| Two or more numbers with arithmetic | core.add / sub / mul / div or core.batch |
| "income tax", "capital gains", "acquisition tax" | tax.kr_income / tax.capital_gains_kr / realestate.kr_acquisition_tax |
| "VAT", "supply amount" | accounting.vat_extract / accounting.vat_add |
| "NPV", "IRR", "discount rate", "present value" | finance.pv / fv / npv / irr |
| "depreciation", "straight-line", "declining balance" | accounting.depreciation_* |
| "business days", "excluding holidays" | datetime.add_business_days / count_business_days |
| "t-test", "confidence interval", "p-value" | stats.ttest_* / stats.ci_mean |
| Probability distribution PDF/CDF | probability.* |
| Matrix / vector operations | geometry.matrix_* / vector_* |
| Unit conversion | units.convert / units.temperature |
| Currency conversion | units.fx_convert / fx_triangulate |
| Multiple scenario comparison | core.batch |
| Feed previous result to next calculation | core.pipeline |
| "bond yield", "duration" | finance.bond_ytm / bond_duration |
| "option price", "Greeks", "Black-Scholes" | finance.black_scholes |
| "EITC", "earned income tax credit" | tax.kr_eitc |
| "comprehensive income tax" | tax.kr_comprehensive_income_tax |
| "securities transaction tax", "vehicle tax" | tax.kr_securities_transaction / kr_pension_income / kr_vehicle_tax / kr_registration_license_tax |
| "overtime pay", "minimum wage" | payroll.kr_overtime_pay / kr_weekly_holiday_pay / kr_minimum_wage_check |
| "national pension benefit" | payroll.kr_national_pension_benefit / kr_health_income_premium |
| "gross from net" | payroll.kr_gross_from_net / core.solve_for |
| "subscription score" | realestate.kr_subscription_score |
| "FICA" | tax_us.fica |

### Anti-patterns (strictly prohibited)
- Computing arithmetic inline in the prompt without tool verification
- Calling tax.* without the `year` argument and falling back to estimates
- Calling core.add N times when core.batch handles all at once

### Response rules
- Every numeric response must cite the tool trace
- If `_meta.hints` contains a `recommended_tool`, apply it immediately
