# pm

프로젝트 관리 도구. 주공정법(CPM), 획득가치관리(EVM), 획득일정(Earned Schedule), PERT 삼점 추정, 몬테카를로 일정 위험을 다룬다.

|도구|계산|엔진|
|-|-|-|
|`pm.critical_path`|작업 의존 관계로 주공정법(CPM) 일정을 계산한다. 각 작업의 ES, EF, LS, LF, 여유와 총 기간, 주공정 작업 목록을 돌려준다.|Decimal|
|`pm.earned_schedule`|획득일정(ES) 지표 SPI(t), TSPI(t), IEAC(t)를 계산한다.|Decimal|
|`pm.evm`|획득가치관리(EVM) 지표 SPI, CPI, SV, CV, EAC, ETC, VAC를 계산한다.|Decimal|
|`pm.monte_carlo_schedule`|PERT 베타 샘플링으로 프로젝트 총 소요 시간 분포를 시뮬레이션한다.|float64(근사)|
|`pm.pert`|PERT 삼점 추정으로 기대 기간, 분산, 표준편차를 계산한다.|mpmath|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

mixed 모듈이다. 일정·비용 지표 3종은 Decimal 전 구간이고, 표준편차 산출과 몬테카를로 샘플링만 다른 자료형을 쓴다.

|도구|내부 자료형|
|-|-|
|`critical_path`|Decimal|
|`earned_schedule`|Decimal|
|`evm`|Decimal|
|`pert`|Decimal + mpmath|
|`monte_carlo_schedule`|float64 (numpy)|

### 캐스팅 정책

- `critical_path`, `earned_schedule`, `evm` 은 `core.decimal_ops.D()` → Decimal 산술 → `str()` 으로 끝난다. float 을 거치지 않는다.
- `pert` 는 `D()` → Decimal 기댓값·분산 → `mpmath.workdps(50)` 제곱근 → `core.cast.mpmath_to_decimal(digits=30)` 으로 끝난다.
- `monte_carlo_schedule` 는 `D()` → `core.cast.decimal_to_float64` → `np.random.default_rng(seed)` 샘플링 → `core.cast.float64_to_decimal_str(digits=10)` 으로 끝난다.
- 위상 정렬(CPM)은 표준 라이브러리 `graphlib.TopologicalSorter` 로 하고 결과 순서는 그 위상 순서를 따른다.
- 이 모듈은 `core.rounding` 의 `RoundingPolicy` 를 쓰지 않는다. `critical_path`, `earned_schedule`, `evm` 은 반올림하지 않는다.

### 정밀도 한계

- `critical_path`, `earned_schedule`, `evm` 은 Decimal 50자리 정밀도에서 계산하며 결과를 문자열로 그대로 내보낸다. `evm` 의 나눗셈 결과는 반복 소수일 수 있다.
- `pert` 의 표준편차만 mpmath 50자리로 계산해 유효숫자 30자리까지 낸다. 기댓값과 분산은 Decimal 연산 결과다.
- `monte_carlo_schedule` 는 float64 샘플링이라 유효숫자 10자리 문자열이며 마지막 자리는 근사값이다. `seed` 가 같으면 같은 결과가 나온다(기본 0).

## 사용 시 주의

- `critical_path` 은 작업 간 지연(lag)과 시작 제약을 지원하지 않고 순환 의존은 오류다.
- `monte_carlo_schedule` 는 작업 기간을 단순 합산하므로 병렬 경로나 선후 관계는 반영하지 않는다.
