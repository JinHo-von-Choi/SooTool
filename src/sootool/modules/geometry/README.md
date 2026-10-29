# geometry

넓이, 부피, 벡터, 행렬, 지구 표면 거리 도구.

|도구|계산|엔진|
|-|-|-|
|`geometry.area_circle`|원의 넓이 π * r² 를 계산한다.|mpmath|
|`geometry.area_polygon`|다각형 넓이를 신발끈 공식(Shoelace)으로 계산한다.|mpmath|
|`geometry.area_rectangle`|직사각형 넓이 width * height 를 Decimal 로 정확히 계산한다.|Decimal|
|`geometry.area_triangle`|삼각형 넓이 (base * height) / 2 를 Decimal 로 정확히 계산한다.|Decimal|
|`geometry.haversine`|하버사인 공식으로 두 지점의 지구 표면 대원 거리(km)를 계산한다.|mpmath|
|`geometry.matrix_determinant`|정방행렬 M 의 행렬식을 계산한다.|float64(근사)|
|`geometry.matrix_inverse`|정방행렬의 역행렬을 numpy.linalg.inv(float64)로 계산한다.|float64(근사)|
|`geometry.matrix_multiply`|행렬 곱 A @ B 를 Decimal 로 계산한다.|float64(근사)|
|`geometry.matrix_solve`|연립일차방정식 Ax = b 의 해 x 를 numpy.linalg.solve(float64)로 구한다.|float64(근사)|
|`geometry.vector_cross`|3차원 벡터의 외적 a × b 를 Decimal 로 계산한다.|mpmath|
|`geometry.vector_dot`|두 벡터의 내적 Σ a_i * b_i 를 Decimal 로 계산한다.|mpmath|
|`geometry.vector_norm`|벡터의 L-p 노름을 계산한다.|mpmath|
|`geometry.volume_cuboid`|직육면체 부피 length * width * height 를 Decimal 로 계산한다.|mpmath|
|`geometry.volume_cylinder`|원기둥 부피 π * r² * h 를 계산한다.|mpmath|
|`geometry.volume_sphere`|구의 부피 (4/3) * π * r³ 를 계산한다.|mpmath|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

mixed 모듈이다. 위 "계산 방식" 절이 이미 도구별 경계를 설명하므로 여기서는 도구별로 실제 계산에 쓰이는 자료형을 정리한다. 위 표의 엔진 열은 모듈 단위의 거친 분류이고, 아래 표는 도구별 실제 경로다.

|도구|내부 자료형|
|-|-|
|`area_rectangle`, `area_triangle`, `area_polygon`, `volume_cuboid`|Decimal|
|`vector_dot`, `vector_cross`|Decimal|
|`matrix_multiply`|Decimal|
|`matrix_determinant`|Decimal (3×3 이하) / float64 (4×4 이상)|
|`matrix_inverse`, `matrix_solve`|float64 (numpy.linalg)|
|`area_circle`, `haversine`, `volume_cylinder`, `volume_sphere`, `vector_norm`|Decimal + mpmath|

### 캐스팅 정책

- 입력 숫자는 전부 십진 문자열이며 `core.decimal_ops.D()` 로 읽는다. float 입력은 받지 않는다.
- mpmath 경로(`area_circle`, `haversine`, `volume_cylinder`, `volume_sphere`, `vector_norm`): `mpmath.workdps(50)`(`_MPMATH_DPS`) 안에서 계산하고 `mpmath.nstr(value, 30, strip_zeros=False)` 로 30자리 문자열을 만든 뒤 `D()` 로 Decimal 에 읽는다. `core.cast.mpmath_to_decimal` 을 쓰지 않는 점이 다른 모듈과 다르다.
- Decimal 경로(`area_rectangle`, `area_triangle`, `area_polygon`, `volume_cuboid`, `vector_dot`): `localcontext(Context(prec=precision))` 로 입력 자릿수에 맞춘 독립 컨텍스트에서 계산하고 `context.traps[Inexact] = True` 로 정확히 떨어지지 않는 결과를 `DecimalException` 으로 거른다. `vector_cross` 는 컨텍스트를 열지 않고 Decimal 산술만 한다.
- 행렬 경로: `matrix_multiply` 와 `matrix_determinant`(3×3 이하)는 Decimal 로 직접 계산한다. `matrix_determinant` 의 4×4 이상은 `_decimal_matrix_to_float()` 로 `np.float64` 배열을 만들어 `np.linalg.det` 을 쓰고 `D(repr(float(...)))` 로 되돌린다. `matrix_inverse` 와 `matrix_solve` 도 numpy `linalg` 을 쓰고 결과는 `repr(float(v))` 로 문자열화한다.
- `core.cast` 의 `decimal_to_float64` 과 `float64_to_decimal_str` 는 쓰지 않는다. 이 모듈은 `core.rounding` 의 `RoundingPolicy` 도 쓰지 않는다.

### 정밀도 한계

- mpmath 경로는 50자리 컨텍스트에서 계산하지만 문자열로 옮길 때 30자리로 자른다. 마지막 자리는 근사값이다.
- Decimal 경로는 컨텍스트 정밀도를 입력 자릿수에 맞춰 잡으므로 결과의 소수점은 정확하다. 다만 결과가 Decimal 표현 범위를 넘거나 정확히 표현되지 않으면 `invalid_input` 오류로 거른다.
- `matrix_inverse` 와 `matrix_solve` 는 float64 결과라 정밀도가 유효숫자 15~17자리에서 멈춘다. 조건이 나쁜 행렬에서는 오차가 커진다.
- `matrix_determinant` 의 3×3 이하 경로는 Decimal 이지만 4×4 이상 경로로 넘어가면 float64 근사가 된다. 같은 도구 안에서 정밀도가 달라진다.

## 계산 방식

- 직사각형 넓이는 Decimal로 정확히 곱하고 Decimal 문자열로 돌려준다.
- 삼각형 넓이는 밑변과 수직 높이의 곱을 Decimal로 정확히 반으로 나누고 Decimal 문자열로 돌려준다.
- 직육면체 부피는 Decimal로 정확히 곱하고 Decimal 문자열로 돌려준다.
- 그 외 넓이·부피·벡터·하버사인은 Decimal 입력을 받아 mpmath(50자리)로 계산하고 Decimal 문자열로 돌려준다.
- 행렬 곱은 Decimal로 계산한다. 행렬식은 3×3 이하에서 Decimal 전개, 그보다 크면 numpy float64를 쓴다.
- 역행렬과 연립방정식 풀이는 numpy `linalg`(float64)를 쓴다. 결과는 근사값이다.
- 행렬 한 변의 상한은 200이다(`SOOTOOL_LIMIT_MATRIX_DIM`).

삼각형·직사각형 넓이와 직육면체 부피는 유한한 0 이상 입력을 자릿수에 맞춘 독립 Decimal 컨텍스트에서 정확히 계산한다. 호출자의 정밀도·반올림 설정에 영향을 받지 않으며, NaN·무한대와 Decimal 범위를 벗어나 정확히 표현할 수 없는 결과는 `invalid_input` 오류로 거부한다.

## 오류

- 음수 반지름·길이·높이, 꼭짓점 3개 미만 다각형, 특이행렬, 범위를 벗어난 위도(±90°)·경도(±180°): `domain_constraint`

## 출처

- 신발끈 공식(Shoelace formula), 하버사인 공식(지구 반지름 6,371 km)

## 예

```python
from sootool.sdk import geometry

geometry.area_circle(radius="5")["area"]       # "78.5398163397448309615660845820"
geometry.haversine(lat1="37.5665", lon1="126.9780",
                   lat2="35.1796", lon2="129.0756")["distance_km"]   # "325.111258849761689640587521141" (서울-부산)
```
