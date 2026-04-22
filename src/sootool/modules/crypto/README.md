# crypto module

암호학 기초 연산 모듈. GCD/LCM, 모듈러 산술, 해시, 소수 판별 도구를 제공합니다.

## 공개 도구

| 도구 | 설명 | 반환 필드 |
|-|-|-|
| `crypto.gcd` | 최대공약수(GCD) | result, trace |
| `crypto.lcm` | 최소공배수(LCM) | result, trace |
| `crypto.modpow` | 모듈러 거듭제곱 `base^exp mod m` | result, trace |
| `crypto.modinv` | 모듈러 역원 `a^-1 mod m` | result, trace |
| `crypto.hash` | SHA-256 / SHA-512 / BLAKE2b | hex, trace |
| `crypto.is_prime` | Miller-Rabin 소수 판별 | is_prime, trace |

## ADR-008 준수 사항

- 모듈러 산술은 Python 내장 `int` 타입 사용 (Decimal 불필요).
- 해시는 stdlib `hashlib` 사용.
- 소수 판별은 외부 의존성 없이 Miller-Rabin을 직접 구현.
  - n < 3.8 * 10^18 범위에서 결정론적 고정 증인 집합 사용 → 오판 없음.
  - 더 큰 n에서는 k (기본 20)개의 무작위 증인 사용.

## 공식 출처

- GCD/LCM: Python `math.gcd`, `math.lcm` (Python 3.9+)
- 모듈러 역원: Python `pow(a, -1, m)` (Python 3.8+)
- Miller-Rabin 결정론적 증인 집합: [Wikipedia — Miller-Rabin primality test](https://en.wikipedia.org/wiki/Miller%E2%80%93Rabin_primality_test#Testing_against_small_sets_of_bases)
- 해시: Python `hashlib` (FIPS 140-2 준수)

## 수용 기준

- 모든 입력은 정수 문자열. 변환 실패 시 `InvalidInputError`.
- `modinv`: gcd(a, m) != 1 이면 `DomainConstraintError`.
- `modpow`: exponent 음수, modulus <= 0 이면 `DomainConstraintError`.
- 병렬(race-free) 호출 시 동일 결과 보장.

## 예시

```python
from sootool.core.registry import REGISTRY
import sootool.modules.crypto  # noqa: F401

# GCD
REGISTRY.invoke("crypto.gcd", a="48", b="18")
# -> {"result": "6", "trace": {...}}

# 모듈러 역원
REGISTRY.invoke("crypto.modinv", a="3", m="11")
# -> {"result": "4", "trace": {...}}  # 3*4=12≡1 mod 11

# 해시
REGISTRY.invoke("crypto.hash", data="hello", algorithm="sha256")
# -> {"hex": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824", ...}

# 소수 판별
REGISTRY.invoke("crypto.is_prime", n="2305843009213693951")  # 2^61-1 (Mersenne prime)
# -> {"is_prime": True, ...}
```
