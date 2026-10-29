# science

과학 도구. 화학(몰질량, 화학양론), 물리(방사성 붕괴), 열역학(이상 기체), 광학(스넬의 법칙, 얇은 렌즈, 브래그 회절, 세기), 전기화학(네른스트 방정식, 패러데이 법칙, 배터리 용량)을 다룬다.

|도구|계산|엔진|
|-|-|-|
|`science.molar_mass`|화학식의 몰질량(g/mol)과 원소별 원자 수를 구한다.|Decimal|
|`science.stoichiometry`|균형 맞춘 반응식에서 한계 반응물과 몰수·질량을 구한다.|Decimal|
|`science.ideal_gas`|이상 기체 법칙 PV = nRT 에서 빠진 변수 하나를 구한다.|Decimal|
|`science.half_life`|방사성 붕괴로 남은 양과 남은 비율을 구한다.|mpmath|
|`science.snell_law`|스넬의 법칙으로 굴절각을 구한다.|mpmath|
|`science.bragg`|브래그 회절 조건에서 파장·면간격·회절각 중 하나를 구한다.|mpmath|
|`science.thin_lens`|얇은 렌즈 방정식 1/f = 1/p + 1/q 에서 빠진 값과 배율을 구한다.|Decimal|
|`science.intensity`|빛이나 복사의 세기(W/m²)를 구한다.|Decimal|
|`science.nernst`|네른스트 방정식으로 비표준 조건의 전극 전위를 구한다.|mpmath|
|`science.faraday_electrolysis`|패러데이 법칙으로 석출 질량(g)을 구한다.|Decimal|
|`science.battery_capacity`|배터리 용량을 Ah와 Wh 사이에서 변환한다.|Decimal|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

mixed 모듈이다. Decimal 산술만으로 되는 도구와 초월함수가 필요한 도구가 나뉜다. float64 경로는 없다.

|도구|내부 자료형|
|-|-|
|`molar_mass`, `stoichiometry`, `ideal_gas`, `thin_lens`, `intensity`, `faraday_electrolysis`, `battery_capacity`|Decimal|
|`half_life`|Decimal + mpmath|
|`snell_law`, `bragg`|Decimal + mpmath|
|`nernst`|Decimal + mpmath|

### 캐스팅 정책

- mpmath 경로: `D()` → `mpmath.workdps(40 또는 50)` 계산 → `core.cast.mpmath_to_decimal(digits=...)` 로 Decimal 문자열로 돌아온다. float 을 거치는 단계가 없다.
- Decimal 전 구간 도구: `core.decimal_ops.D()` → Decimal 산술 → `str()` 으로 끝난다.
- `core.cast.decimal_to_float64` 과 `float64_to_decimal_str` 는 이 모듈에서 쓰지 않는다.
- 이 모듈은 `core.rounding` 의 `RoundingPolicy` 를 쓰지 않는다. `nernst` 만 결과 길이를 일정하게 맞추려고 `quantize(Decimal("1E-20"))` 를 한 번 건다.

### 정밀도 한계

- Decimal 전 구간 도구는 `decimal_ops` 컨텍스트(정밀도 50자리)에서 계산하며 반올림하지 않는다.
- mpmath 경로는 `workdps` 컨텍스트 안에서 계산한다. `half_life` 은 50자리 컨텍스트에서 계산해 유효숫자 30자리로 내보내고, `snell_law` 와 `bragg` 는 40자리에서 계산해 유효숫자 20자리로 내보낸다.
- mpmath 컨텍스트 밖의 값은 Decimal 50자리 정밀도이므로, 입력이 20자리보다 길면 그 뒤는 버려진다.

## 사용 시 주의

- 입력 단위는 SI 기본 단위다. `ideal_gas` 는 atm, L, 섭씨를 그대로 넣지 말고 Pa, m³, K 로 환산한다.
- `nernst` 에 넣는 `reaction_q` 는 반응 지수 Q 다. ln(Q) 를 넣으면 안 된다.
- `faraday_electrolysis` 의 시간은 초 단위다. 전류 효율은 100%로 가정한다.
- `molar_mass` 는 H~Pb 사이 일반 원소를 지원하고 그 밖의 원소와 이온 전하 표기는 오류다.
