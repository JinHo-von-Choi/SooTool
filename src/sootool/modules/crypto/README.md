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
