# tax_us

미국 세금 도구. 연방 소득세(일반 세율), 연방 자본이득세(장기·단기 + NIIT), FICA·SECA, 주 소득세(CA·NY·TX)를 다룬다. 세율표와 상한은 정책 파일에서 읽는다.

|도구|계산|엔진|
|-|-|-|
|`tax_us.federal_income`|연방 일반 소득세(7개 누진 구간, 4개 신고 유형)를 계산한다.|Decimal|
|`tax_us.capital_gains`|연방 자본이득세(장기 0/15/20%, 단기 일반 세율)를 계산하고 필요하면 NIIT 3.8% 를 더한다.|Decimal|
|`tax_us.fica`|FICA 급여세(근로자·고용주)와 자영업세 SECA(순이익의 92.35%)를 계산한다.|Decimal|
|`tax_us.state_tax`|주 소득세(CA, NY, TX)를 계산한다.|Decimal|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

Decimal 전 구간 모듈이다. float64, numpy, mpmath 를 쓰지 않으므로 경계 변환도 없다.

### 캐스팅 정책

- 입력 숫자는 전부 십진 문자열이며 `core.decimal_ops.D()` 로 Decimal 로 읽는다. float 입력은 받지 않는다.
- 구간표 세액은 `_brackets.py` 의 `slice_tax()` / `schedule_tax()` 가 Decimal 로 반올림 없이 계산한다. 각 구간의 세액·한계세율·구간별 과세 대상 금액이 모두 문자열로 담긴다.
- 결과 반올림은 `core.rounding.apply(value, decimals, policy)`(= `round_apply`) 로 한다. 정책은 `sootool.modules.tax.progressive._parse_rounding` 이 인자의 `rounding` 문자열에서 해석하고 기본값은 소수 둘째 자리 `HALF_UP` 다.
- `core.cast` 의 `decimal_to_float64`, `float64_to_decimal_str`, `mpmath_to_decimal` 은 쓰지 않는다.
- 주별 구간표에 `base`(구간 기준액)가 있으면 `schedule_tax()` 가 `base + rate x (과세표준 - 하한)` 을 쓰고, 없으면 누진 합산으로 내려간다. NY 처럼 공시 표가 기준액을 정수로 끊어 싣는 주에서도 표와 같은 값이 나온다.
- 세율·구간·상한은 `sootool.policy_mgmt.loader.load` 로 정책 YAML(`policies/tax_us/*.yaml`)에서 읽는다.

### 정밀도 한계

- 계산은 `decimal_ops` 컨텍스트(정밀도 50자리)에서 돈다. 결과는 십진 문자열이므로 소수점은 정확하다.
- 나눗셈이 반복 소수가 되는 값(유효세율, NIIT 산출)은 컨텍스트 정밀도 50자리에서 멈춘다.
- 세율표를 정책 파일에서 읽으므로 정책 연도가 바뀌면 결과가 달라진다. 응답의 `policy_version` 으로 확인한다.

## 사용 시 주의

- 금액 단위는 USD이고 입력은 십진 문자열로 받는다.
- `federal_income` 의 `apply_standard_deduction=true` 는 `taxable_income` 을 AGI 로 본다. 이미 공제를 뺀 값에 true 를 주면 공제가 두 번 빠진다.
- `capital_gains` 의 `ordinary_taxable_income` 을 생략하면 0으로 본다. 다른 소득이 있으면 반드시 넣어야 한다.
- `state_tax` 는 TX 는 세금이 0이고, NY 는 조정총소득 107,650 초과분을 환수 처리한다. CA 는 과세표준 1,000,000 초과분에 1% 가산세를 붙인다.
- `fica` 의 사회보장 기준액은 고용주 한 곳 기준이며, 복수 고용주 초과징수 환급과 선택적 계산법은 계산하지 않는다.
