# geometry

넓이, 부피, 벡터, 행렬, 지구 표면 거리 도구.

|도구|계산|엔진|
|-|-|-|
|`geometry.area_circle`|원의 넓이 π * r² 를 계산한다.|mpmath|
|`geometry.area_polygon`|다각형 넓이를 신발끈 공식(Shoelace)으로 계산한다.|mpmath|
|`geometry.area_rectangle`|직사각형 넓이 width * height 를 Decimal 로 계산한다.|mpmath|
|`geometry.area_triangle`|삼각형 넓이 (base * height) / 2 를 Decimal 로 계산한다.|mpmath|
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

## 계산 방식

- 넓이·부피·벡터·하버사인은 Decimal 입력을 받아 mpmath(50자리)로 계산하고 Decimal 문자열로 돌려준다.
- 행렬 곱은 Decimal로 계산한다. 행렬식은 3×3 이하에서 Decimal 전개, 그보다 크면 numpy float64를 쓴다.
- 역행렬과 연립방정식 풀이는 numpy `linalg`(float64)를 쓴다. 결과는 근사값이다.
- 행렬 한 변의 상한은 200이다(`SOOTOOL_LIMIT_MATRIX_DIM`).

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
