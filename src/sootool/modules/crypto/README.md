# crypto

정수론과 해시 도구. 최대공약수, 모듈러 연산, 중국인의 나머지 정리, 소수 판별, 오일러 피와 카마이클 함수, 해시를 제공한다.

|도구|계산|엔진|
|-|-|-|
|`crypto.carmichael_lambda`|카마이클 함수 λ(n) = lcm(λ(p^k)) 를 구한다.|Decimal|
|`crypto.crt`|중국인의 나머지 정리로 연립합동식 x ≡ r_i (mod m_i) 의 해 x 를 구한다.|Decimal|
|`crypto.egcd`|확장 유클리드 알고리즘으로 gcd(a, b) = a*x + b*y 를 만족하는 gcd 와 Bezout 계수 x, y 를 구한다.|Decimal|
|`crypto.euler_totient`|오일러 토션트 φ(n) = n * Π(1 - 1/p) 를 구한다.|Decimal|
|`crypto.gcd`|두 정수의 최대공약수(GCD)를 구한다.|Decimal|
|`crypto.hash`|문자열을 UTF-8로 인코딩해 해시(16진수)를 구한다.|Decimal|
|`crypto.is_prime`|밀러-라빈 판정법으로 소수 여부를 판정한다.|Decimal|
|`crypto.lcm`|두 정수의 최소공배수(LCM)를 구한다.|Decimal|
|`crypto.modinv`|모듈러 역원 a^-1 mod m 을 구한다.|Decimal|
|`crypto.modpow`|모듈러 거듭제곱 base^exponent mod modulus 를 구한다.|Decimal|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

파이썬 `int`(임의 정밀도 정수) 전 구간 모듈이다. Decimal, float64, mpmath 를 쓰지 않는다. 위 표의 엔진 열이 Decimal 인 것은 이 모듈이 수치 변환 경계를 갖지 않음을 뜻한다.

### 캐스팅 정책

- 입력은 정수 문자열이며 `_ints.py` 의 `parse_int()` 가 읽는다. 자릿수가 `SOOTOOL_LIMIT_CRYPTO_DIGITS` 를 넘으면 `InputLimitError` 다.
- 계산은 표준 라이브러리 정수 연산(`math.gcd`, `math.lcm`, `pow(x, -1, m)` 등) 또는 자체 확장 유클리드 알고리즘으로 한다. `core.decimal_ops.D()` 도 `core.cast` 도 쓰지 않는다.
- 결과는 `str(int)` 로 문자열 직렬화한다. 정수이므로 소수점은 없고 출력 자릿수 상한도 없다. 입력 자릿수 상한만 적용된다.
- 해시는 표준 라이브러리 `hashlib` 이며 숫자 자료형 변환이 없다.
- 이 모듈은 `core.rounding` 의 `RoundingPolicy` 를 쓰지 않는다.

### 정밀도 한계

- 파이썬 `int` 는 임의 정밀도라 정수 연산에 오차가 없다. `modpow` 의 `pow(base, exponent, modulus)` 와 `modinv` 의 `pow(a, -1, m)` 은 파이썬 내장 모듈러 거듭제곱이라 지수 크기만큼 중간값이 커지지 않는다.
- 다만 입력 정수의 자릿수가 2,048자리를 넘으면 `InputLimitError` 로 막힌다.
- `is_prime` 은 n < 3.3 × 10²⁴ 에서 결정적으로 판정하고 그보다 큰 수는 확률적 판정(라운드 수 상한 `SOOTOOL_LIMIT_PRIME_ROUNDS`)이므로 아주 큰 수에서는 확정적 판정을 보장하지 않는다.

## 계산 방식

- 정수 연산은 파이썬 `int`(임의 정밀도)로 한다. 입력과 출력은 정수 문자열이다.
- 소수 판별은 밀러-라빈이다. n < 3.3 × 10²⁴ 범위는 고정 증인 집합으로 결정적으로 판정하고, 그보다 큰 수는 확률적으로 판정한다(라운드 수 상한 `SOOTOOL_LIMIT_PRIME_ROUNDS`).
- 해시는 표준 라이브러리 `hashlib`(SHA-256, SHA-512, BLAKE2b)을 쓴다.
- 정수 자릿수 상한은 2,048자리다(`SOOTOOL_LIMIT_CRYPTO_DIGITS`).

## 오류

- 정수가 아닌 입력: `invalid_input`
- `modinv`에서 gcd(a, m) ≠ 1, `modpow`에서 음수 지수나 0 이하 법: `domain_constraint`

## 예

```python
from sootool.sdk import crypto

crypto.gcd(a="48", b="18")["result"]                          # "6"
crypto.modinv(a="3", m="11")["result"]                        # "4"  (3 × 4 = 12 ≡ 1 mod 11)
crypto.is_prime(n="2305843009213693951")["is_prime"]          # True (2^61 - 1)
```
