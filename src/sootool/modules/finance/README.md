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

`npv`, `pv`, `fv`, `roi`, `cagr`, `payback_period` 등은 `rounding`(기본 HALF_EVEN)과 `decimals`를 받는다. 원화 금액은 `decimals=0`, 채권·옵션 값은 6자리 이상을 권한다.

호출 예시는 [금융 쿡북](../../../../docs/cookbook/finance_scenarios.md)에 있다.
