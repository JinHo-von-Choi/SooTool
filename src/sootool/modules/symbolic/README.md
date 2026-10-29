# symbolic

기호 해석 도구. sympy 로 기호 미분과 방정식 풀이를 하고, 결과를 Decimal 문자열로 되돌려준다. sympy 는 optional dependency 이므로 `sootool[symbolic]` extra 가 필요하다.

|도구|계산|엔진|
|-|-|-|
|`symbolic.diff`|sympy 로 n차 기호 도함수를 구하고, 치환한 지점의 수치를 Decimal 문자열로 함께 반환한다.|mpmath|
|`symbolic.solve`|sympy 로 방정식을 기호 풀이하고 실수해를 Decimal 문자열로 반환한다.|mpmath|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

sympy 기호 객체(sympy Expr) + mpmath 내부를 거쳐 Decimal 문자열 경계로 나가는 구조다. float64 경로는 없다.

|도구|내부 자료형|
|-|-|
|`diff`|sympy Expr → mpmath → Decimal 문자열|
|`solve`|sympy Expr → mpmath → Decimal 문자열|

### 캐스팅 정책

- 수식 입력은 `core.calc` 의 AST 화이트리스트(`_parse` + `_count_and_validate`)를 먼저 통과해야 한다. 통과 뒤에만 `sympy.sympify(expression, locals={}, rational=True)` 로 바뀐다. `locals={}` 로 이름 해석 경로를 막고 `rational=True` 로 소수 리터럴을 정확한 유리수로 읽는다.
- 변수 값은 `Decimal(raw).as_integer_ratio()` 로 분자/분모 정수를 뽑아 `sympy.Rational` 로 치환한다. 부동소수로 치환하면 `sympy.solve` 가 계수를 15자리 부동소수로 취급해 해의 자릿수가 줄어든다.
- 수치 직렬화는 `to_decimal_string()` 한 곳에서만 한다. `sympy.Float` 은 `mpmath.mpf(str(numeric))` 로 한 번 더 감싸 float 누수를 막고 `core.cast.mpmath_to_decimal` 로 넘긴다. `sympy.Rational` 은 분자/분모를 Decimal 로 나눠 직접 계산한다. 정수 결과는 `str(Decimal(int(...)))` 이고 실수가 아닌 값(기호·복소수)은 sympy 문자열로 그대로 반환한다.
- `core.cast.decimal_to_float64` 과 `float64_to_decimal_str` 는 쓰지 않는다. 이 모듈은 `core.rounding` 의 `RoundingPolicy` 도 쓰지 않는다.

### 정밀도 한계

- 수치 평가는 `mpmath.workdps(50)` 컨텍스트에서 `evalf(50)` 으로 50자리까지 계산하고 `mpmath_to_decimal(digits=50)` 으로 유효숫자 50자리 문자열을 만든다.
- sympy 의 기호 연산(미분·해법) 자체는 sympy 의 내부 정밀도 규칙을 따른다. 유리수 계수는 정확하지만 초월함수가 섞이면 sympy 가 정한 자리수로 근사한다.
- 유리수 해는 `Decimal` 나눗셈으로 바뀌므로 `decimal_ops` 컨텍스트(정밀도 50자리)에서 계산된다.

## 의존성

- sympy 가 없으면 도구 호출 시 `SymbolicDependencyError` 가 발생하고, "sympy 가 설치되지 않았습니다. symbolic.* 도구를 사용하려면 `pip install 'sootool[symbolic]'` 또는 `uv pip install -e .[symbolic]`" 안내가 붙는다.
- sympy 연산은 5초 제한(`_EVAL_TIMEOUT_S`) 안에서 돈다. 메인 스레드에서는 `SIGALRM`, 그 밖에서는 스레드 풀 타임아웃으로 강제 종료하며 초과하면 `DomainConstraintError` 다.

## 사용 시 주의

- 표현식 길이는 5000자까지다. 그를 넘으면 `DomainConstraintError` 다.
- `solve` 의 `equation` 은 `lhs = rhs` 또는 단일식(=0 가정) 형식이다.
- `diff` 의 `order` 는 1~20이다.
- 치환 후에도 기호가 남으면 수치값을 내지 않고 기호 문자열을 그대로 돌려준다.
