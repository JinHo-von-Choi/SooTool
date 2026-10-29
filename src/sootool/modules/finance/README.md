# finance

화폐의 시간 가치, 투자 지표, 대출, 채권, 파생상품, 위험 지표 도구.

|도구|계산|엔진|
|-|-|-|
|`finance.black_scholes`|Black-Scholes 유럽형 옵션의 가격과 델타, 감마, 베가, 세타, 로를 계산한다.|mpmath|
|`finance.bond_duration`|채권의 맥컬리 듀레이션과 수정 듀레이션을 연 단위로 계산한다.|Decimal|
|`finance.bond_ytm`|채권 만기수익률(YTM)을 뉴턴법으로 구한다.|Decimal|
|`finance.cagr`|복합연평균성장률(CAGR)을 계산한다.|Decimal|
|`finance.forward_price`|무차익 선도가격을 계산한다.|mpmath|
|`finance.futures_price`|연속복리 보유비용 모형의 선물 이론가격을 계산한다.|mpmath|
|`finance.fv`|현재 금액의 미래가치를 계산한다.|Decimal|
|`finance.irr`|내부수익률(IRR), 즉 NPV 를 0 으로 만드는 기간 수익률을 구한다.|Decimal|
|`finance.loan_schedule`|대출 상환 스케줄을 계산한다.|Decimal|
|`finance.npv`|순현재가치를 계산한다.|Decimal|
|`finance.option_payoff`|옵션의 만기 payoff 를 계산한다.|mpmath|
|`finance.payback_period`|단순 투자회수기간을 계산한다.|Decimal|
|`finance.pv`|미래 현금흐름의 현재가치를 계산한다.|Decimal|
|`finance.roi`|투자수익률(ROI)을 계산한다.|Decimal|
|`finance.sharpe_ratio`|샤프지수 = (평균수익률 - 무위험수익률) / 표본표준편차(n-1)를 계산한다.|float64(근사)|
|`finance.sortino_ratio`|소르티노 비율 = (평균수익률 - 무위험수익률) / 하방편차를 계산한다.|float64(근사)|
|`finance.var_historical`|과거 수익률의 경험적 분위수로 VaR 와 CVaR(기대부족액)을 계산한다.|float64(근사)|
|`finance.var_parametric`|정규분포를 가정한 모수적 VaR 와 CVaR 를 계산한다.|float64(근사)|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

mixed 모듈이다. 시간가치·투자지표·대출·채권·위험지표는 Decimal 전 구간이고, 파생상품은 mpmath 를 거친 Decimal 이며 `var_parametric` 만 scipy float64 를 거친다. 위 표의 엔진 열은 모듈 단위의 거친 분류이고, 아래 표는 도구별 실제 경로다.

|도구|내부 자료형|
|-|-|
|`pv`, `fv`, `npv`, `irr`, `roi`, `cagr`, `payback_period`, `loan_schedule`, `bond_ytm`, `bond_duration`|Decimal|
|`var_historical`, `sharpe_ratio`, `sortino_ratio`|Decimal|
|`black_scholes`, `forward_price`, `futures_price`, `option_payoff`|Decimal + mpmath|
|`var_parametric`|Decimal + float64 (scipy.stats)|

### 캐스팅 정책

- 입력 숫자는 전부 십진 문자열이며 `core.decimal_ops.D()` 로 읽고, 사칙연산과 거듭제곱은 `core.decimal_ops` 의 `add` / `sub` / `mul` / `div` / `power` 를 쓴다.
- 반올림은 `core.rounding.apply(value, decimals, policy)`(= `round_apply`) 다. 정책은 모듈의 `_parse_policy(rounding)` 이 인자에서 해석하고 기본값은 `HALF_EVEN` 이다. 원화 금액은 `decimals=0`, 채권·옵션 값은 6자리 이상을 권한다(위 "반올림" 절).
- Decimal 컨텍스트는 도구마다 다르다. `tvm.py`(`pv`, `fv`)는 `localcontext(Context(prec=50))` 로 고정 50자리를 쓰고, `metrics.py`(`npv`, `irr`, `roi`, `cagr`, `payback_period`)는 입력 자릿수에서 파생한 가변 정밀도(최소 50자리)를 쓴다. `bond.py` 와 `loan.py` 는 컨텍스트를 열지 않고 기본 컨텍스트에서 계산한다.
- mpmath 경로: `option.py`(`black_scholes`)는 `mp.mp.dps = 50`, `derivatives.py`(`forward_price`, `futures_price`, `option_payoff`)는 `mpmath.mp.dps = 40`(`_DEFAULT_DPS`)로 계산하고 `core.cast.mpmath_to_decimal(digits=10~30)` 으로 Decimal 문자열로 되돌린다.
- `var_parametric` 만 scipy `stats.norm.ppf` / `pdf` 에서 float64 을 쓰고, 그 값을 `D(str(z))` 로 Decimal 에 되돌린다. 나머지 위험지표(`var_historical`, `sharpe_ratio`, `sortino_ratio`)는 Decimal 로만 계산한다.
- `risk.py` 의 `_q8` 은 `v.quantize(Decimal("0.00000001"))` 로 소수 8자리를 고정한다. `core.cast` 의 `decimal_to_float64` 과 `float64_to_decimal_str` 는 이 모듈에서 쓰지 않는다.

### 정밀도 한계

- Decimal 경로는 `decimal_ops` 컨텍스트(정밀도 50자리 이상)에서 돈다. 결과는 십진 문자열이므로 소수점은 정확하다.
- mpmath 경로는 50자리(옵션) 또는 40자리(선물·선도) 컨텍스트에서 계산해 유효숫자 10~30자리로 내보낸다.
- `var_parametric` 의 z 값과 정규밀도는 float64 계산이므로 유효숫자 15~17자리에서 멈춘다. 확률수준(`conf`)만 입력이고 나머지 분포 계산은 float64 다.
- `irr` 과 `bond_ytm` 은 뉴턴-랩슨 반복 풀이라 허용오차 1e-10 안에서만 수렴을 보장한다. 수렴 실패 시 `converged: false` 를 돌려준다(위 "수렴" 절).
- `irr` 의 이분법 구간은 [−0.99, 10] 이므로 그 밖의 해는 찾지 못한다.

## 공식과 출처

|구분|공식|출처|
|-|-|-|
|PV, FV|PV = FV / (1+r)^n, FV = PV·(1+r)^n|Brealey, Myers & Allen, *Principles of Corporate Finance*, 13th ed., Ch. 2-3|
|NPV, IRR|NPV = Σ CF_t / (1+r)^t, IRR은 NPV(r) = 0의 해|같은 책 Ch. 5-6|
|ROI, CAGR|ROI = 순이익 / 투자원가, CAGR = (기말/기초)^(1/n) − 1|-|
|투자회수기간|회수 직전 기간 수 + 회수 직전 미회수액 / 회수 기간 현금흐름. 끝까지 회수하지 못하면 `null`과 `recovered: false`|-|
|대출|원리금균등 M = P·r·(1+r)^n / ((1+r)^n − 1), 원금균등 P/n + 잔액 이자|-|
|채권|P = Σ C/(1+y/f)^t + F/(1+y/f)^n, 수정 듀레이션 = 맥컬리 / (1 + y/f)|Fabozzi, *Fixed Income Mathematics*, 4th ed., Ch. 3-4|
|블랙-숄즈|d1 = (ln(S/K) + (r − q + σ²/2)T) / (σ√T), d2 = d1 − σ√T|Black & Scholes (1973), Merton (1973)|

## 수렴

|도구|방법|허용오차|실패 시|
|-|-|-|-|
|`irr`|뉴턴-랩슨, 실패하면 [−0.99, 10] 구간 이분법|1e-10|`converged: false`, `irr: null`|
|`bond_ytm`|뉴턴-랩슨(표면이율에서 시작)|1e-10|`converged: false`|

현금흐름의 부호가 한 번도 바뀌지 않으면 `irr`은 반복 없이 `converged: false`를 돌려준다.

## 반올림

`pv`, `fv`는 호출자의 Decimal 설정과 독립적인 50자리 정밀도로 계산한다. 금액과 이율은 유한해야 하며, 기간은 1 이상 정수, 소수점 자릿수는 0 이상 정수다. 계산·반올림 범위를 넘으면 입력 오류를 반환한다.

`npv`, `pv`, `fv`, `roi`, `cagr`, `payback_period` 등은 `rounding`(기본 HALF_EVEN)과 `decimals`를 받는다. 원화 금액은 `decimals=0`, 채권·옵션 값은 6자리 이상을 권한다.

호출 예시는 [금융 쿡북](../../../../docs/cookbook/finance_scenarios.md)에 있다.
