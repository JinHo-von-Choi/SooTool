# Stats Module

Author: 최진호
Date: 2026-04-22

## 개요

통계 계산 도구 모음. 기술통계, t-검정, 카이제곱 검정, 신뢰구간, 선형회귀를 제공한다.

## 내부 자료형 및 캐스팅 정책 (ADR-008)

ADR-008 준수: 통계 계산은 내부적으로 `float64` (numpy/scipy/statsmodels) 사용.
경계에서만 Decimal 문자열로 변환한다.

- 입력: `list[str]` (Decimal 문자열) → `np.array(dtype=np.float64)` 변환
- 출력: `float64` → `sootool.core.cast.float64_to_decimal_str()` 로 Decimal 문자열 직렬화
- 절대 `float` 직접 반환하거나 `json.dumps` 에 float 그대로 넣지 않음

출력 정밀도:
- 평균, 표준편차, 중앙값 등: 10 유효 자리
- t 통계량: 6 유효 자리
- p-value: 10 유효 자리
- R²: 10 유효 자리

## 도구 목록

| 도구 | 설명 |
|-|-|
| `stats.descriptive` | 기술통계 (n, mean, median, variance, stdev, min, max, q1, q3) |
| `stats.ttest_one_sample` | 일표본 t-검정 |
| `stats.ttest_two_sample` | 이표본 t-검정 (Welch 기본) |
| `stats.ttest_paired` | 짝지은 t-검정 |
| `stats.chi_square_independence` | 카이제곱 독립성 검정 |
| `stats.ci_mean` | 평균 신뢰구간 (t-분포) |
| `stats.regression_linear` | 선형회귀 (OLS) |

## 의존성

- `numpy`: 배열 연산, 기술통계
- `scipy.stats`: t-검정, 카이제곱, 신뢰구간
- `statsmodels`: OLS 회귀분석
