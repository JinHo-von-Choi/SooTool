# Finance Module

작성자: 최진호
작성일: 2026-04-22

## 도구 목록

| 도구명 | 설명 | 파일 |
|-|-|-|
| finance.pv | 현재가치(PV) | tvm.py |
| finance.fv | 미래가치(FV) | tvm.py |
| finance.npv | 순현재가치(NPV) | metrics.py |
| finance.irr | 내부수익률(IRR) | metrics.py |
| finance.loan_schedule | 대출 상환 스케줄 | loan.py |
| finance.bond_ytm | 채권 만기수익률(YTM) | bond.py |
| finance.bond_duration | Macaulay/Modified Duration | bond.py |
| finance.black_scholes | Black-Scholes 옵션 가격 + Greeks | option.py |

## 공식 출처

### TVM (화폐의 시간 가치)
- Brealey, Myers & Allen, "Principles of Corporate Finance", 13th ed., Ch. 2-3.
- PV = FV / (1+r)^n
- FV = PV * (1+r)^n

### NPV / IRR
- Brealey, Myers & Allen, "Principles of Corporate Finance", 13th ed., Ch. 5-6.
- NPV = sum(CF_t / (1+r)^t, t=0..n)
- IRR: NPV(r) = 0 — Newton-Raphson + bisection fallback

### 대출 상환
- 금융감독원 표준 대출 상환 공식 (표준 금융상품 약관)
- EQUAL_PAYMENT: M = P * r_m * (1+r_m)^n / ((1+r_m)^n - 1)
- EQUAL_PRINCIPAL: principal_per_month = P / n; interest = balance * r_m

### 채권
- Fabozzi, "Fixed Income Mathematics", 4th ed., Ch. 3-4.
- YTM: Newton-Raphson으로 P = sum(C/(1+y/f)^t) + F/(1+y/f)^n 수치해법
- Macaulay Duration = sum(t * PV(CF_t)) / P  [in years]
- Modified Duration = Macaulay / (1 + ytm/freq)

### Black-Scholes
- Black, F. & Scholes, M. (1973). "The Pricing of Options and Corporate Liabilities."
  Journal of Political Economy, 81(3), 637-654. DOI:10.1086/260062
- Merton, R.C. (1973). "Theory of Rational Option Pricing."
  Bell Journal of Economics, 4(1), 141-183.
- d1 = (ln(S/K) + (r - q + sigma^2/2)*T) / (sigma*sqrt(T))
- d2 = d1 - sigma*sqrt(T)
- call = S*exp(-qT)*N(d1) - K*exp(-rT)*N(d2)
- put  = K*exp(-rT)*N(-d2) - S*exp(-qT)*N(-d1)

## 자료형 정책 (ADR-008)

| 도구 | 내부 연산 | 반환 |
|-|-|-|
| TVM (pv, fv) | pure Decimal | str |
| NPV, IRR | pure Decimal | str |
| 대출 스케줄 | pure Decimal | str |
| 채권 (YTM, Duration) | pure Decimal | str |
| Black-Scholes | mpmath (50 dps) | str via mpmath_to_decimal |

## 반올림 정책

- 기본값: HALF_EVEN (IEEE 754 banker's rounding)
- 원화(KRW): decimals=0
- 채권/옵션: 소수점 6자리 이상 유지 권장

## 알고리즘 수렴 정책

| 도구 | 알고리즘 | tol (기본) | 폴백 |
|-|-|-|-|
| IRR | Newton-Raphson | 1e-10 | bisection [-0.99, 10] |
| Bond YTM | Newton-Raphson | 1e-10 | N/A (coupon rate 초기값) |

수렴 실패 시 converged=False 반환 (예외 미발생).
IRR의 경우 부호 전환이 없으면 즉시 converged=False 반환.
