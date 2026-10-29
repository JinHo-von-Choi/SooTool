# math

수치 해석 도구. 수치 미분, 수치 적분, 보간, 다항식 평가와 근 찾기, 이산 푸리에 변환을 다룬다. 수식 인자는 `core.calc` 문법을 쓴다.

|도구|계산|엔진|
|-|-|-|
|`math.diff_central`|중심 차분으로 1차 도함수를 수치 근사한다.|float64(근사)|
|`math.diff_five_point`|5점 공식으로 1차 도함수를 수치 근사한다. 중심 차분보다 오차가 작다(O(h⁴)).|float64(근사)|
|`math.fft`|실수 샘플의 이산 푸리에 변환(DFT)을 계산한다.|float64(근사)|
|`math.ifft`|푸리에 변환 bin 리스트에서 시간 영역 샘플을 복원한다(1/N 정규화 포함).|float64(근사)|
|`math.integrate_gauss_legendre`|가우스-르장드르 구적법으로 정적분한다.|float64(근사)|
|`math.integrate_simpson`|합성 심프슨 1/3 법으로 정적분한다.|float64(근사)|
|`math.interpolate_cubic_spline`|3차 스플라인 보간으로 값을 구한다.|float64(근사)|
|`math.interpolate_linear`|1차원 선형 보간으로 값을 구한다.|float64(근사)|
|`math.polynomial_horner`|호너 방법으로 다항식을 평가한다.|Decimal|
|`math.polynomial_roots`|다항식의 모든 근(복소근 포함)을 구한다.|float64(근사)|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

mixed 모듈이다. `polynomial_horner` 만 Decimal 전 구간이고 나머지는 float64 내부 계산에 Decimal 문자열 경계를 둔다. `integrate_gauss_legendre` 는 구적 자체를 mpmath 로 하지만 결과가 float64 를 지나므로 최종 정밀도는 float64 다.

|도구|내부 자료형|
|-|-|
|`diff_central`, `diff_five_point`|float64|
|`fft`, `ifft`|float64 (numpy.fft)|
|`integrate_simpson`|float64|
|`integrate_gauss_legendre`|float64 (구적은 mpmath)|
|`interpolate_linear`, `interpolate_cubic_spline`|float64 (numpy/scipy)|
|`polynomial_horner`|Decimal|
|`polynomial_roots`|float64 (numpy.roots)|

### 캐스팅 정책

- 입력: `core.decimal_ops.D()` 로 읽은 Decimal 을 `core.cast.decimal_to_float64` 로 float64 에 넘긴다.
- 출력: `core.cast.float64_to_decimal_str(value, digits=12)` 로 Decimal 문자열을 만든다(`_SIG = 12`).
- `polynomial_horner` 만 `D()` → Decimal 호너 법 → `str()` 으로 끝나며 float 을 거치지 않는다.
- 수식 평가는 `core.calc` 안전 AST 평가기(`precision=15`)를 거치고, 그 결과를 `float()` 으로 받아 float64 계산에 넣는다.
- `core.rounding` 의 `RoundingPolicy` 는 쓰지 않는다. 결과 자릿수는 `float64_to_decimal_str(digits=12)` 로 고정한다.

### 정밀도 한계

- float64 는 유효숫자 15~17자리만 표현하므로 결과는 12자리로 맞춘다. 마지막 유효숫자는 근사값이다.
- `polynomial_horner` 는 float 을 거치지 않아 입력 계수의 자릿수를 그대로 유지한다.
- `integrate_gauss_legendre` 는 mpmath 40자리로 적분해도 최종 값이 float64 를 지나며 12자리로 줄어든다.

## 사용 시 주의

- `integrate_simpson` 은 하한이 상한보다 크면 오류이므로 부호를 직접 뒤집어야 하고, 특이점이 있는 구간은 정확하지 않다.
- `interpolate_linear` 와 `interpolate_cubic_spline` 은 표본 구간 밖의 질의를 외삽하지 않고 오류로 낸다.
- `fft` 의 `k` 는 주파수가 아니라 인덱스다. Hz 는 `k * 샘플링주파수 / N` 으로 따로 계산한다.
- `ifft` 는 bin 을 N개 전체를 순서대로 넣어야 한다. 일부만 넣으면 다른 신호가 복원된다.
