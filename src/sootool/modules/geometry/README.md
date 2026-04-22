# geometry module

기하학 및 선형대수 연산 모듈. 넓이, 부피, 벡터, 행렬, 지리 거리 도구를 제공합니다.

## 공개 도구

| 도구 | 설명 | 반환 필드 |
|-|-|-|
| `geometry.area_circle` | 원의 넓이 π·r² | area, trace |
| `geometry.area_triangle` | 삼각형 넓이 base·h/2 | area, trace |
| `geometry.area_rectangle` | 직사각형 넓이 w·h | area, trace |
| `geometry.area_polygon` | 다각형 넓이 (Shoelace) | area, trace |
| `geometry.volume_sphere` | 구의 부피 (4/3)·π·r³ | volume, trace |
| `geometry.volume_cylinder` | 원기둥 부피 π·r²·h | volume, trace |
| `geometry.volume_cuboid` | 직육면체 부피 l·w·h | volume, trace |
| `geometry.vector_dot` | 벡터 내적 | result, trace |
| `geometry.vector_cross` | 3D 벡터 외적 | result, trace |
| `geometry.vector_norm` | 벡터 L-p 노름 | result, trace |
| `geometry.matrix_multiply` | 행렬 곱셈 A@B | result, trace |
| `geometry.matrix_determinant` | 행렬식 det(M) | result, trace |
| `geometry.matrix_inverse` | 역행렬 M⁻¹ | result, trace |
| `geometry.matrix_solve` | 선형계 풀기 Ax=b | x, trace |
| `geometry.haversine` | 하버사인 지리 거리 | distance_km, trace |

## ADR-008 준수 사항

- 2D 넓이/거리 경계값 처리: Decimal 문자열 입출력.
- 원/구/원기둥/노름/하버사인: 내부에서 mpmath (50 dps) 사용 후 Decimal 문자열 반환.
- 행렬 곱셈: Decimal 루프 (정밀도 보장).
- 행렬식(n≤3): Decimal 직접 전개. n>3: numpy float64.
- 역행렬/선형계: numpy linalg (float64) → 결과를 repr 문자열로 반환.

## 공식 출처

- Shoelace formula: https://en.wikipedia.org/wiki/Shoelace_formula
- Haversine formula: https://en.wikipedia.org/wiki/Haversine_formula
- Miller-Rabin 관련 행렬 연산: numpy.linalg (OpenBLAS 기반)

## 수용 기준

- 모든 입력은 Decimal 문자열. 변환 실패 시 `InvalidInputError`.
- 음수 반지름/길이/높이: `DomainConstraintError`.
- 다각형 꼭짓점 < 3개: `DomainConstraintError`.
- 역행렬/행렬식: 특이행렬 시 `DomainConstraintError`.
- 하버사인: 위도 범위 ±90°, 경도 범위 ±180° 벗어나면 `DomainConstraintError`.
- 병렬(race-free) 호출 시 동일 결과 보장.

## 예시

```python
from sootool.core.registry import REGISTRY
import sootool.modules.geometry  # noqa: F401

# 원의 넓이
REGISTRY.invoke("geometry.area_circle", radius="5")
# -> {"area": "78.5398163397448309...", "trace": {...}}

# 하버사인 (서울 → 부산)
REGISTRY.invoke("geometry.haversine",
    lat1="37.5665", lon1="126.9780",
    lat2="35.1796", lon2="129.0756")
# -> {"distance_km": "~325", "trace": {...}}

# 선형계 풀기
REGISTRY.invoke("geometry.matrix_solve",
    A=[["2", "1"], ["5", "3"]],
    b=["1", "2"])
# -> {"x": ["1.0", "-1.0"], "trace": {...}}
```
