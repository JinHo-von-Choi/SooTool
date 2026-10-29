# medical

신체 계측, 신기능, 투약량, 심혈관 위험, QT 보정 등 임상 계산 도구. 계산 보조용이며 진단이나 처방을 대신하지 않는다.

|도구|계산|엔진|
|-|-|-|
|`medical.bmi`|체질량지수(BMI)를 계산하고 WHO 기준으로 분류한다.|mpmath|
|`medical.bsa`|체표면적(BSA)을 m² 단위로 계산한다.|mpmath|
|`medical.cha2ds2_vasc`|심방세동 환자의 뇌졸중 위험 점수 CHA2DS2-VASc를 계산한다.|Decimal|
|`medical.dose_weight_based`|체중 기반 약물 용량을 계산한다.|Decimal|
|`medical.egfr`|혈청 크레아티닌으로 추정 사구체여과율(eGFR)을 CKD-EPI 2021(인종 계수 없음) 식으로 계산하고 KDIGO 2012 CKD 병기(G1~G5)를 돌려준다.|Decimal|
|`medical.framingham_cvd_10y`|프레이밍햄 일반 10년 심혈관질환 발생 확률을 계산한다(D'Agostino 2008).|Decimal|
|`medical.has_bled`|항응고 치료 환자의 주요 출혈 위험 점수 HAS-BLED를 계산한다.|Decimal|
|`medical.pregnancy_weeks`|최종 월경일(LMP)로 임신 주수와 분만예정일(EDD)을 계산한다.|Decimal|
|`medical.qtc_bazett`|Bazett 공식으로 QT 간격을 심박수에 맞춰 보정한다.|mpmath|
|`medical.qtc_framingham`|Framingham 선형 공식으로 QT 간격을 보정한다.|mpmath|
|`medical.qtc_fridericia`|Fridericia 공식으로 QT 간격을 심박수에 맞춰 보정한다.|mpmath|
|`medical.qtc_hodges`|Hodges 공식으로 QT 간격을 심박수에 맞춰 보정한다.|mpmath|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 내부 자료형 및 캐스팅 정책

### 내부 자료형

mixed 모듈이다. 단순 산술 도구는 Decimal, 근사식 도구는 float64, 비정수 지수 도구는 mpmath 를 거친 Decimal 이다. 날짜 계산 도구는 숫자 변환이 없다.

|도구|내부 자료형|
|-|-|
|`bmi`, `dose_weight_based`|Decimal|
|`pregnancy_weeks`|날짜(`datetime.date`) 와 정수|
|`bsa`, `egfr`|float64 (float 계산 후 Decimal 로 복귀)|
|`qtc_bazett`, `qtc_framingham`, `qtc_fridericia`, `qtc_hodges`|Decimal + mpmath|
|`cha2ds2_vasc`, `has_bled`|정수 합산|
|`framingham_cvd_10y`|float64 (회귀식)|

### 캐스팅 정책

- 입력 숫자는 전부 십진 문자열이며 `core.decimal_ops.D()` 로 읽는다.
- `bmi` 와 `dose_weight_based` 는 Decimal 계산 후 `core.rounding.apply(value, decimals, policy)`(= `round_apply`) 로 반올림한다. `bmi` 는 소수 2자리 `HALF_EVEN`, `dose_weight_based` 는 소수 4자리 `HALF_EVEN` 이다.
- `bsa`(Dubois: `float(h) ** 0.725`, Mosteller: `float(mpmath.sqrt(...))`)와 `egfr`(`_ckd_epi_2021` 이 float 로 계산)는 float64 계산값을 `D(str(value), allow_float=True)` 로 Decimal 에 다시 넣는다. `allow_float=True` 는 이 의도적 float 진입을 표시하는 표식이다.
- `qtc_*` 네 도구는 `mpmath.workdps(40)`(`_MPDPS`) 안에서 계산하고 `core.cast.mpmath_to_decimal(digits=20)` 으로 Decimal 문자열로 되돌린다. 반올림 자릿수는 따로 정하지 않는다.
- `framingham_cvd_10y` 는 `core.cast.decimal_to_float64` 로 총콜레스테롤·HDL·혈압을 float64 로 바꿔 회귀식에 넣고 `core.cast.float64_to_decimal_str(digits=10)` 으로 위험률을 되돌린다. 점수 도구(`cha2ds2_vasc`, `has_bled`)는 정수 합산만 한다.
- `core.rounding` 의 `RoundingPolicy` 는 `bsa`(소수 4자리 `HALF_EVEN`), `egfr`(소수 1자리 `HALF_EVEN`), `bmi`(소수 2자리 `HALF_EVEN`), `dose_weight_based`(소수 4자리 `HALF_EVEN`)에만 쓰인다.

### 정밀도 한계

- Decimal 경로는 `decimal_ops` 컨텍스트(정밀도 50자리)에서 돈다.
- `bsa` 와 `egfr` 의 float64 계산은 유효숫자 15~17자리에서 멈춘다. `egfr` 의 1자리 반올림과 `bsa` 의 4자리 반올림은 그 위에서 이뤄진다.
- `qtc_*` 네 도구는 40자리 컨텍스트에서 계산해 유효숫자 20자리로 내보낸다.
- `framingham_cvd_10y` 는 float64 회귀식이므로 위험률이 유효숫자 10자리에서 끊긴다.
- `pregnancy_weeks` 은 정수 일수 계산이라 오차가 없다.

## 공식과 기준

### BMI
BMI = 체중(kg) / 키(m)². 소수 2자리(HALF_EVEN). 분류: underweight < 18.5 ≤ normal < 25 ≤ overweight < 30 ≤ obese_1 < 35 ≤ obese_2 < 40 ≤ obese_3. 출처: WHO, *Obesity and overweight* fact sheet.

### 체표면적(BSA)
- DuBois(`method=dubois`): 0.007184 × 키(cm)^0.725 × 체중(kg)^0.425
- Mosteller(`method=mosteller`): √(키(cm) × 체중(kg) / 3600)

출처: Du Bois & Du Bois, *Arch Intern Med* 1916;17:863-871. Mosteller, *N Engl J Med* 1987;317(17):1098.

### eGFR
CKD-EPI 2021(인종 계수 없음): 142 × min(Scr/κ, 1)^α × max(Scr/κ, 1)^−1.200 × 0.9938^나이 × (여성 1.012)

|성별|κ|α|
|-|-|-|
|여성|0.7|−0.241|
|남성|0.9|−0.302|

병기(KDIGO 2012, mL/min/1.73m²): G1 ≥ 90, G2 60-89, G3a 45-59, G3b 30-44, G4 15-29, G5 < 15. 출처: Inker et al., *N Engl J Med* 2021;385(19):1737-1749.

### 체중 기반 투약량
투약량 = min(체중 × kg당 용량, 최대 용량)

### 임신 주수
분만예정일 = 최종 월경일 + 280일(네겔레 법칙). 0~42주로 제한. 1삼분기 0~13주, 2삼분기 14~27주, 3삼분기 28주 이후. 출처: ACOG Committee Opinion No. 700 (2017).

### QTc
Bazett, Fridericia, Framingham, Hodges 네 공식을 각각의 도구로 제공한다. 입력은 QT 간격과 RR 간격이며 단위는 `unit`(기본 `ms`)으로 지정한다.
