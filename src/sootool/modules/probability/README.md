# probability

확률 도구. 베이즈 정리, 이산 기댓값, 조합론(팩토리얼·이항계수·순열), 정규·베타·감마·지수·로그정규·이항·포아송·카이제곱·F 분포의 pdf·cdf·ppf를 다룬다.

|도구|계산|엔진|
|-|-|-|
|`probability.bayes`|베이즈 정리로 사후확률 P(A\|B)를 구한다.|Decimal|
|`probability.expected_value`|이산 확률변수의 기댓값 E[X] = Σ value_i · prob_i 를 구한다.|Decimal|
|`probability.factorial`|n!을 정확한 정수 문자열로 구한다.|mpmath|
|`probability.nCr`|이항계수 C(n, r) 를 정확한 정수 문자열로 구한다.|Decimal|
|`probability.nPr`|순열 P(n, r) 을 정확한 정수 문자열로 구한다.|Decimal|
|`probability.normal_pdf`|정규분포의 확률밀도를 구한다.|float64(근사)|
|`probability.normal_cdf`|정규분포의 누적확률을 구한다.|float64(근사)|
|`probability.normal_ppf`|정규분포의 분위수를 구한다.|float64(근사)|
|`probability.beta_pdf`|베타분포의 확률밀도를 구한다.|float64(근사)|
|`probability.beta_cdf`|베타분포의 누적확률을 구한다.|float64(근사)|
|`probability.beta_ppf`|베타분포의 분위수를 구한다.|float64(근사)|
|`probability.gamma_pdf`|감마분포의 확률밀도를 구한다.|float64(근사)|
|`probability.gamma_cdf`|감마분포의 누적확률을 구한다.|float64(근사)|
|`probability.gamma_ppf`|감마분포의 분위수를 구한다.|float64(근사)|
|`probability.exponential_pdf`|지수분포의 확률밀도를 구한다.|float64(근사)|
|`probability.exponential_cdf`|지수분포의 누적확률을 구한다.|float64(근사)|
|`probability.exponential_ppf`|지수분포의 분위수를 구한다.|float64(근사)|
|`probability.lognormal_pdf`|로그정규분포의 확률밀도를 구한다.|float64(근사)|
|`probability.lognormal_cdf`|로그정규분포의 누적확률을 구한다.|float64(근사)|
|`probability.lognormal_ppf`|로그정규분포의 분위수를 구한다.|float64(근사)|
|`probability.binomial_pmf`|이항분포의 확률질량을 구한다.|float64(근사)|
|`probability.binomial_cdf`|이항분포의 누적확률을 구한다.|float64(근사)|
|`probability.poisson_pmf`|포아송분포의 확률질량을 구한다.|float64(근사)|
|`probability.poisson_cdf`|포아송분포의 누적확률을 구한다.|float64(근사)|
|`probability.chi_square_pdf`|카이제곱분포의 확률밀도를 구한다.|float64(근사)|
|`probability.chi_square_cdf`|카이제곱분포의 누적확률을 구한다.|float64(근사)|
|`probability.chi_square_ppf`|카이제곱분포의 분위수를 구한다.|float64(근사)|
|`probability.f_pdf`|F 분포의 확률밀도를 구한다.|float64(근사)|
|`probability.f_cdf`|F 분포의 누적확률을 구한다.|float64(근사)|
|`probability.f_ppf`|F 분포의 분위수를 구한다.|float64(근사)|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

mixed 모듈이다. 분포 함수 24종은 scipy `stats` 내부 float64, 베이즈와 기댓값은 Decimal 전 구간, 조합론은 정수 연산이다.

|도구|내부 자료형|
|-|-|
|분포 24종(`*_pdf`, `*_cdf`, `*_ppf`)|float64 (scipy.stats)|
|`bayes`|Decimal|
|`expected_value`|Decimal|
|`nCr`, `nPr`|정수 (Decimal로 직렬화)|
|`factorial`|정수 (mpmath)|

### 캐스팅 정책

- 분포 경계: `core.decimal_ops.D()` → `core.cast.decimal_to_float64` → scipy float64 → `core.cast.float64_to_decimal_str(digits=10)`. 공통 헬퍼는 `distributions/_common.py` 의 `_parse_float` / `_parse_prob` / `_parse_quantile` 과 `_dist_result()` 이며 출력 자릿수는 `_SIG_DIGITS = 10` 이다.
- `bayes` 는 `D()` → Decimal 곱셈·나눗셈 → `str()` 으로 끝나며 float 을 거치지 않는다.
- `expected_value` 는 `D()` → `localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN))` 합산 → `str()` 으로 끝난다.
- `nCr`, `nPr` 은 `math.comb` / `math.perm` 로 계산하고, `factorial` 은 n < 1000 이면 `math.factorial`, n ≥ 1000 이면 `mpmath.workdps` 안에서 `mpmath.factorial` 을 쓴다. 셋 다 파이썬 `int` → `str(Decimal(value))` 로 직렬화한다.
- 이 모듈은 `core.rounding` 의 `RoundingPolicy` 를 쓰지 않는다.

### 정밀도 한계

- 분포 함수는 float64 계산이라 유효숫자 10자리로 맞춘다. 마지막 유효숫자는 근사값이다.
- `bayes` 와 `expected_value` 는 Decimal 50자리로 계산한다.
- `factorial` 은 n ≥ 1000 에서 자릿수를 Stirling 상계로 추정해 `mpmath.workdps` 자릿수를 정한다. 결과 자릿수가 매우 커서 float 로 변환하면 정밀도를 잃는다.

## 사용 시 주의

- 감마·지수분포의 `scale` 은 rate 의 역수다. rate 를 그대로 넣으면 틀린다.
- 로그정규분포의 `mu`, `sigma` 는 ln X 의 평균과 표준편차다. X 자체의 통계량이 아니다.
- 정규분포의 `sigma` 는 표준편차다. 분산을 넣으면 틀린다.
- 밀도값은 확률이 아니다. 구간 확률은 cdf 의 차로 구한다.
