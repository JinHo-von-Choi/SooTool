# stats

기술통계, 모수·비모수 검정, 신뢰구간, 회귀, 효과크기 도구.

|도구|계산|엔진|
|-|-|-|
|`stats.anova_oneway`|둘 이상 집단의 평균 차이를 일원분산분석(one-way ANOVA)으로 검정하고 Tukey HSD 쌍별 비교를 덧붙인다.|float64(근사)|
|`stats.bootstrap_ci`|표본 평균 또는 중앙값의 부트스트랩 신뢰구간을 백분위수법으로 구한다.|float64(근사)|
|`stats.chi_square_independence`|분할표의 두 범주형 변수가 독립인지 카이제곱 검정으로 판정한다.|float64(근사)|
|`stats.ci_mean`|표본 평균의 양측 신뢰구간을 t 분포로 계산한다.|float64(근사)|
|`stats.cohens_d`|두 독립 표본의 효과크기 Cohen's d와 소표본 보정값 Hedges's g를 계산한다.|float64(근사)|
|`stats.descriptive`|기술통계량(n, 평균, 중앙값, 분산, 표준편차, 최소, 최대, 사분위수)을 계산한다.|float64(근사)|
|`stats.eta_squared`|일원분산분석의 효과크기 η²와 ω²를 계산한다.|float64(근사)|
|`stats.kruskal_wallis`|여러 독립 집단의 위치 차이를 크루스칼-월리스 H 검정으로 판정한다.|float64(근사)|
|`stats.mann_whitney_u`|두 독립 표본의 위치 차이를 만-휘트니 U 검정으로 판정한다.|float64(근사)|
|`stats.regression_linear`|최소제곱(OLS) 선형회귀로 계수, 절편, R², 계수별 p값, 잔차를 구한다.|float64(근사)|
|`stats.ttest_one_sample`|표본 평균이 기준값과 다른지 일표본 t-검정으로 판정한다.|float64(근사)|
|`stats.ttest_paired`|대응표본의 평균 차이를 t-검정으로 판정한다.|float64(근사)|
|`stats.ttest_two_sample`|두 독립 표본의 평균 차이를 t-검정으로 판정한다.|float64(근사)|
|`stats.wilcoxon`|윌콕슨 부호순위 검정으로 대응표본의 차이를 판정한다.|float64(근사)|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 계산 방식

numpy와 scipy로 float64 계산을 하고, 결과를 Decimal 문자열로 바꿔 돌려준다(`core.cast.float64_to_decimal_str`). 입력은 숫자 문자열 목록이다. 결과의 마지막 유효숫자는 근사값이다.

|값|유효숫자|
|-|-|
|평균, 표준편차, 중앙값 등|10자리|
|t 통계량|6자리|
|p-value, R²|10자리|

## 사용 시 주의

- `ttest_two_sample`은 기본으로 웰치 t-검정(등분산 가정 없음)이다.
- `regression_linear`는 의사역행렬과 t 분포로 OLS를 계산한다. 결과는 statsmodels와 교차 시험으로 대조한다.
- `bootstrap_ci`의 재표본 수 상한은 100,000이다(`SOOTOOL_LIMIT_BOOTSTRAP_RESAMPLES`). `seed`(기본 42)가 같으면 결과가 같다.
