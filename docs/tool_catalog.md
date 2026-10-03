# 도구 카탈로그

scripts/gen_tool_catalog.py 가 레지스트리에서 생성한다. 직접 고치지 않는다. 정확도 등급은 계산 엔진에서 정해진다:
exact(Decimal), high_precision(mpmath, 지정 자릿수), approximate(float64 근사), depends_on_children(호출한 도구에 따름),
not_numeric(수치 계산 아님). 정책 열이 예이면 `year` 와 시점(`as_of`)에 따라 정책 문서를 읽는다.

총 281개 도구, 20개 네임스페이스.


## accounting (11)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|balance|1.0.0|exact||예|분개 목록의 차변 합계와 대변 합계가 같은지 검증한다. entries 는 {account, debit, credit} 항목의 목록이며 금액은 Decimal 문자…|
|cashflow_operating|1.0.0|exact||예|간접법 영업활동현금흐름(CFO)을 계산한다. 당기순이익에 감가상각비, 무형자산상각비, 기타 비현금 항목을 더하고 매출채권 증가와 재고자산 증가는 빼며 매입채무 …|
|depreciation_declining_balance|1.0.0|exact||예|정률법 감가상각 스케줄을 계산한다. 연도별 감가비 = 기초 장부가 x 감가율(rate, 0 초과 1 미만 Decimal 문자열)이며 장부가는 잔존가치 아래로 내…|
|depreciation_straight_line|1.0.0|exact||예|정액법 감가상각 스케줄을 계산한다. 연 감가비 = (취득원가 - 잔존가치) / 내용연수(life_years, 1 이상 정수), 금액은 Decimal 문자열. d…|
|depreciation_units_of_production|1.0.0|exact||예|생산량비례법 감가상각 스케줄을 계산한다. 기간 감가비 = (취득원가 - 잔존가치) / 총생산량 x 기간 생산량. total_units 는 1 이상 정수, per…|
|dupont_3|1.0.0|exact||예|DuPont 3단계 분해로 ROE = 순이익률 x 총자산회전율 x 자기자본승수(재무레버리지)를 계산한다. 금액은 Decimal 문자열이며 매출, 총자산, 자기자…|
|dupont_5|1.0.0|exact||예|DuPont 5단계 분해로 ROE = 세부담비율(순이익/세전이익) x 이자부담비율(세전이익/EBIT) x 영업이익률 x 총자산회전율 x 재무레버리지를 계산한다.…|
|income_statement|1.0.0|exact||예|다단계 손익계산서: 매출에서 매출총이익, 영업이익, 세전이익, 당기순이익까지 단계별 이익과 이익률을 계산한다. 금액은 Decimal 문자열이며 매출과 매출원가는…|
|ratios|1.0.0|exact||예|재무상태표와 손익 항목으로 유동비율, 당좌비율, 부채/자기자본, 부채/총자산, 자기자본비율, ROE, ROA, 순이익률 8개를 한 번에 계산한다. 금액은 Dec…|
|vat_add|1.0.0|exact||예|공급가액에 부가세를 더해 공급대가를 계산한다. 부가세 = 공급가액 x rate(기본 0.1)를 정수 자리로 rounding 처리하며 기본은 HALF_EVEN 으…|
|vat_extract|1.0.0|exact||예|공급대가(부가세 포함 금액)에서 공급가액과 부가세를 역산한다. 공급가액 = gross / (1 + rate)를 정수 자리로 rounding(기본 DOWN, 절사…|

## core (11)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|add|1.0.0|exact||예|Decimal 정밀 덧셈. operands(쉼표, 단위, 공백 없는 숫자 문자열 목록)의 합을 result 문자열로 반환한다. 유효숫자 50자리 안에서 계산하고…|
|batch|1.0.0|depends_on_children||예|서로 독립인 도구 호출 N개를 병렬 실행한다. items 는 id, tool, args 를 가진 객체 목록(최대 500개, id 중복 불가)이고 읽기 전용 도구…|
|calc|1.0.0|high_precision||예|AST 기반 안전 수식 평가기. expression 은 사칙, %, //, **, 괄호, 함수(sqrt, abs, floor, ceil, round, log, …|
|compare|1.0.0|depends_on_children||예|시나리오 비교: 읽기 전용 도구 tool 을 base_arguments 로 실행한 기준안과, 각 시나리오의 arguments 로 덮어쓴 실행을 비교한다. fie…|
|div|1.0.0|exact||예|Decimal 정밀 나눗셈 a / b. a 와 b 는 쉼표, 단위, 공백 없는 숫자 문자열이며 b 가 0 이면 오류를 반환한다. 몫은 유효숫자 50자리로 계산되…|
|explain|1.0.0|depends_on_children||예|설명 모드: 읽기 전용 도구 tool 을 arguments 로 실행하고, 수식, 입력, 계산 단계, 결과, 적용 정책(상태, 시행 기간)과 근거 조문을 평문(l…|
|mul|1.0.0|exact||예|Decimal 정밀 곱셈. operands(쉼표, 단위, 공백 없는 숫자 문자열 목록)의 곱을 result 문자열로 반환한다. 유효숫자 50자리를 넘는 곱은 그…|
|pipeline|1.0.0|depends_on_children||예|의존 관계(DAG)를 가진 도구 호출을 순서대로 실행하고 앞 단계 결과를 뒤 단계 입력으로 전달한다. steps 는 id, tool, args 목록(최대 50단…|
|pipeline_resume|1.0.0|depends_on_children||예|이전 core.pipeline 실행을 pipeline_id 로 지정하고 from_step 단계부터 다시 실행한다. from_step 앞쪽의 성공 단계는 결과를 …|
|solve_for|1.0.0|depends_on_children||예|역산: 읽기 전용 도구 tool 의 결과 필드 target_field 가 target 이 되도록 숫자 문자열 입력 variable 을 [lower, upper]…|
|sub|1.0.0|exact||예|Decimal 정밀 뺄셈 a - b. a 와 b 는 쉼표, 단위, 공백 없는 숫자 문자열이며 결과는 result 문자열이다. 유효숫자 50자리 안에서 계산하고 …|

## crypto (10)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|carmichael_lambda|1.0.0|exact||예|카마이클 함수 λ(n) = lcm(λ(p^k)) 를 구한다. n 은 1 이상 10^14 이하의 정수 문자열이며 시행 나눗셈으로 소인수분해하므로 한도를 넘으면 오…|
|crt|1.0.0|exact||예|중국인의 나머지 정리로 연립합동식 x ≡ r_i (mod m_i) 의 해 x 를 구한다. residues, moduli 는 길이가 같은 정수 문자열 리스트이고 …|
|egcd|1.0.0|exact||예|확장 유클리드 알고리즘으로 gcd(a, b) = a*x + b*y 를 만족하는 gcd 와 Bezout 계수 x, y 를 구한다. a, b 는 정수 문자열(자릿수…|
|euler_totient|1.0.0|exact||예|오일러 토션트 φ(n) = n * Π(1 - 1/p) 를 구한다. n 은 1 이상 10^14 이하의 정수 문자열이며 시행 나눗셈으로 소인수분해하므로 한도를 넘으…|
|gcd|1.0.0|exact||예|두 정수의 최대공약수(GCD)를 구한다. a, b 는 정수 문자열(부호는 무시, 자릿수 한도 2048)이고 결과 result 는 정수 문자열이다. 둘 다 0 이…|
|hash|1.0.0|exact||예|문자열을 UTF-8 로 인코딩해 해시를 소문자 16진수 hex 로 반환한다. algorithm 은 sha256(기본) \| sha512 \| blake2b(64…|
|is_prime|1.0.0|exact||예|Miller-Rabin 으로 소수 여부 is_prime(bool)을 판정한다. n 은 정수 문자열(자릿수 한도 2048)이며 2 미만과 음수는 False. 약 …|
|lcm|1.0.0|exact||예|두 정수의 최소공배수(LCM)를 구한다. a, b 는 정수 문자열(부호는 무시, 자릿수 한도 2048)이고 큰 정수도 정확히 계산해 result 를 정수 문자열…|
|modinv|1.0.0|exact||예|모듈러 역원 a^-1 mod m 을 구한다. a, m 은 정수 문자열(자릿수 한도 2048)이고 m 은 2 이상이어야 한다. result 는 0 이상 m 미만이…|
|modpow|1.0.0|exact||예|모듈러 거듭제곱 base^exponent mod modulus 를 구한다. 세 인자는 정수 문자열(자릿수 한도 2048)이며 modulus 는 1 이상, exp…|

## datetime (14)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|add_business_days|1.0.0|exact||예|start_date 에 영업일 기준으로 days 를 더한(음수면 뺀) 날짜 end_date 를 YYYY-MM-DD 로 반환한다. 토·일, holidays 패키지…|
|age|1.0.0|exact||예|만 나이(한국 법정 연령)를 years, months, days 정수로 계산한다. 날짜는 YYYY-MM-DD 이고 생일 당일에 한 살이 오른다. referenc…|
|count_business_days|1.0.0|exact||예|start 와 end 사이의 영업일 수 count 를 정수로 센다. 날짜는 YYYY-MM-DD 이고 양 끝 날짜를 포함하며 토·일과 holidays 패키지의 c…|
|day_count|1.0.0|exact||예|이자 계산용 일수 days(정수)와 연 환산 비율 year_fraction(Decimal 문자열)을 구한다. convention 은 30/360(말일 31일 보…|
|diff|1.0.0|exact||예|두 날짜의 차이를 unit(days \| weeks \| months \| years) 단위의 정수 문자열 value 로 돌려준다. 날짜는 YYYY-MM-DD …|
|fiscal_quarter|1.0.0|exact||예|기준일 as_of(YYYY-MM-DD)가 속한 회계분기 번호 quarter(1~4)와 시작·종료일을 구한다. country(KR \| US \| JP \| UK…|
|fiscal_year|1.0.0|exact||예|기준일 as_of(YYYY-MM-DD)가 속한 회계연도의 라벨 fiscal_year 와 시작·종료일을 구한다. country 는 KR \| US(1/1~12/3…|
|lunar_holiday|1.0.0|exact||예|음력 명절을 양력 solar_date 로 환산한다. name 은 seollal(설날), jeongwol_daeboreum(정월대보름), buddhas_birth…|
|lunar_to_solar|1.0.0|exact||예|음력 날짜를 양력 solar_date(YYYY-MM-DD)로 바꾼다. lunar_year 는 2020~2030, lunar_month 는 1~12, lunar_…|
|payroll_period|1.0.0|exact||예|as_of(YYYY-MM-DD)가 속한 월 단위 급여 정산 기간의 period_start, period_end 를 구한다. start_day(1~28, 기본 1…|
|solar_terms|1.0.0|exact||예|양력 year 의 24절기 이름과 양력 날짜 24개를 입춘부터의 순서로 반환한다. 연도별 계산이 아닌 고정 일자표이므로 모든 연도에 같은 월일이 나오고 실제 절…|
|solar_to_lunar|1.0.0|exact||예|양력 날짜를 음력 년·월·일(lunar_year, lunar_month, lunar_day)과 윤달 여부 is_leap 으로 바꾼다. 입력은 YYYY-MM-DD…|
|tax_period_kr|1.0.0|exact||예|as_of(YYYY-MM-DD)가 속한 한국 소득세 과세기간(소득세법 제5조, 1/1~12/31)의 연도 tax_year 와 경계일을 반환한다. 사업 개시·폐업…|
|tz_convert|1.0.0|exact||예|IANA 타임존 사이에서 시각을 변환해 UTC 오프셋이 붙은 ISO 8601 문자열 iso_datetime 으로 돌려준다. 입력은 초 단위(YYYY-MM-DDT…|

## engineering (56)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|ac_impedance|1.0.0|high_precision||예|R, L, C 조합의 AC 합성 임피던스 크기와 위상각을 구한다. frequency(Hz, 0 초과), resistance(Ω), inductance(H), c…|
|beam_deflection|1.0.0|high_precision||예|표준 하중 조건의 보 최대 처짐 δ_max 를 계산한다. case: cantilever_point_end(PL³/3EI), cantilever_uniform(w…|
|bearing_equivalent_load|1.0.0|high_precision||예|베어링 동등가하중 P = X·Fr + Y·Fa 를 계산한다. 반경하중, 축하중, 계수 X 와 Y 는 모두 0 이상이고 두 하중이 동시에 0 이면 오류다. X, …|
|bearing_life_l10|1.0.0|high_precision||예|구름 베어링 기본정격수명 L10 = (C/P)^p 를 백만 회전(10⁶ rev) 단위로 계산한다. bearing_type 'ball' 은 p=3(정확 계산), …|
|bending_stress|1.0.0|high_precision||예|휨응력 σ = M·c/I 를 계산한다. moment 는 굽힘모멘트(N·m, 부호 유지), distance_neutral 은 중립축에서 응력을 구할 섬유까지 거리…|
|bernoulli|1.0.0|high_precision||예|베르누이 방정식 P + ½ρv² + ρgz = 일정 을 풀어 상태 2의 미지수 하나를 구한다. pressure_2, velocity_2, elevation_2 …|
|bode_magnitude_phase|1.0.0|high_precision||예|단일 극점 또는 영점 1차 전달함수의 Bode 크기(dB)와 위상(도)을 구한다. mode='pole'이면 G(jω)=1/(1+jω/ωc), 'zero'이면 G…|
|capacitor_combine|1.0.0|high_precision||예|커패시터 여러 개의 합성 정전용량을 구한다. topology='series'면 1/C=Σ(1/Cᵢ), 'parallel'이면 C=ΣCᵢ. capacitors 는…|
|convective_heat_transfer|1.0.0|high_precision||예|뉴턴 냉각 법칙에 따른 대류 열전달 Q = h·A·(T_s − T_∞) (W)를 계산한다. heat_transfer_coefficient W/(m²·K), ar…|
|darcy_weisbach|1.0.0|high_precision||예|다르시-바이스바흐 식으로 관 마찰 손실 수두 h_f = f·(L/D)·v²/(2g) (m)와 압력강하 ρ·g·h_f (Pa)를 계산한다. friction_fac…|
|db_convert|1.0.0|high_precision||예|dB, Np, dBm과 선형 값을 서로 변환한다. mode: v_to_db(20·log10(value/reference)), p_to_db(10·log10(va…|
|elastic_modulus_relate|1.0.0|exact||예|등방성 선형 탄성체에서 영률 E, 전단탄성계수 G, 푸아송비 ν, 체적탄성계수 K 중 정확히 2개를 받아 나머지 2개를 계산한다(E = 2G(1+ν) = 3K(…|
|electrical_ohm|1.0.0|exact||예|옴의 법칙 V=IR에서 빠진 한 값을 구한다. voltage(V), current(A), resistance(Ω) 중 정확히 2개를 Decimal 문자열로 넣으…|
|electrical_power|1.0.0|exact||예|직류 전력 방정식 P=VI=I²R=V²/R에서 나머지 값을 구한다. power(W), voltage(V), current(A), resistance(Ω) 중 정…|
|euler_buckling|1.0.0|high_precision||예|오일러 좌굴 임계하중 P_cr = π²EI/(KL)² (N)를 계산한다. end_condition 으로 K 를 자동 설정(fixed_free 2, pinned_…|
|exponential_reliability|1.0.0|high_precision||예|지수분포 고장 모델의 신뢰도 R(t) = exp(−λt), 불신뢰도 1−R, 평균 고장간격 MTBF = 1/λ 를 계산한다. failure_rate λ 는 단위…|
|first_order_response|1.0.0|high_precision||예|1차 시스템 G(s)=K/(τs+1)의 스텝 응답 y(t)=K·u·(1−exp(−t/τ))를 구한다. gain K, time_constant τ(초, 0 초과)…|
|fluid_reynolds|1.0.0|high_precision||예|레이놀즈 수 Re = ρvL/μ 를 계산하고 층류(Re < 2300), 천이(2300 이상 4000 이하), 난류(4000 초과)로 분류한다. 밀도 kg/m³,…|
|fourier_heat_conduction|1.0.0|high_precision||예|1차원 정상상태 평판 열전도 Q = k·A·(T_hot − T_cold)/L (W)를 계산한다. thermal_conductivity W/(m·K), area …|
|gear_ratio|1.0.0|high_precision||예|단순 기어쌍의 기어비 i = 피동 잇수 / 구동 잇수 를 계산하고 방향을 함께 반환한다. i > 1 이면 reduction(감속), i < 1 이면 overdr…|
|gear_torque_transmission|1.0.0|high_precision||예|기어쌍을 통과한 출력 토크 τ_out = τ_in·(피동 잇수/구동 잇수)·η 를 계산하고 기어비도 반환한다. 출력 토크는 input_torque 와 같은 단위…|
|hardness_convert|1.0.0|high_precision||예|강재의 경도를 HV, HB, HRC 사이에서 근사식(HV ≈ 0.95·HB, HRC ≈ 88.887 − 0.058·HV)으로 환산한다. value 는 0 초과이…|
|hazen_williams_flow|1.0.0|high_precision||예|하젠-윌리엄스 식(SI)으로 관 유량 Q = 0.278·C·D^2.63·S^0.54 (m³/s)를 계산한다. S = head_loss/length 는 동수경사,…|
|inductor_combine|1.0.0|high_precision||예|인덕터 여러 개의 합성 인덕턴스를 구한다. topology='series'면 L=ΣLᵢ, 'parallel'이면 1/L=Σ(1/Lᵢ). inductors 는 0…|
|lc_resonant_frequency|1.0.0|high_precision||예|LC 공진 주파수 f0=1/(2π√(LC))를 구한다. inductance(H)와 capacitance(F)는 0 초과 Decimal 문자열이고 결과는 Hz(각…|
|lmtd|1.0.0|high_precision||예|열교환기 대수평균온도차 LMTD = (ΔT₁ − ΔT₂)/ln(ΔT₁/ΔT₂)를 계산한다. 양 끝단의 온도차 두 값(K 또는 °C 차, 모두 0 초과)을 받고 …|
|max_power_transfer|1.0.0|exact||예|최대 전력 전달 정리로 최적 부하와 최대 전력을 구한다. R_L=R_th일 때 P_max=V_th²/(4R_th). v_th(V)와 r_th(Ω, 0 초과)는 …|
|mech_strain|1.0.0|exact||예|선형 변형률 ε = ΔL / L (무차원)을 계산한다. delta_length 와 original_length 는 같은 길이 단위여야 하며(mm 와 m 을 섞으…|
|mech_stress|1.0.0|exact||예|수직응력 σ = F / A 를 계산한다. force 는 힘(N), area 는 단면적(m², 0 초과)이며 결과는 Pa(N/m²). 단위 변환은 하지 않고 입력…|
|moment_of_inertia|1.0.0|exact||예|표준 형상의 질량 관성모멘트 I (kg·m²)를 계산한다. solid_disk(½mr²), thin_ring(mr²), solid_sphere(2/5 mr²)는…|
|moody_friction_factor|1.0.0|high_precision||예|콜브룩 방정식 1/√f = -2·log10(ε/(3.7D) + 2.51/(Re·√f)) 를 스위미-제인 초기값에서 시작해 최대 100회, 허용오차 1e-10 으…|
|norton_equivalent|1.0.0|exact||예|테브난 등가(V_th, R_th)를 노턴 등가로 변환한다. I_N=V_th/R_th, R_N=R_th. v_th(V)와 r_th(Ω, 0 초과)는 Decimal…|
|opamp_gain|1.0.0|high_precision||예|이상적 연산증폭기의 폐루프 전압 이득을 구한다. configuration='inverting'이면 -Rf/Rin, 'non_inverting'이면 1+Rf/Ri…|
|parallel_reliability|1.0.0|high_precision||예|병렬(중복) 시스템 신뢰도 R_sys = 1 − Π(1 − R_i)를 계산한다. component_reliabilities 는 구성요소 신뢰도의 숫자 문자열 목…|
|pid_discrete_output|1.0.0|high_precision||예|속도형(velocity form) 이산 PID의 새 출력 u_k=u_{k-1}+Δu를 구한다. Δu=Kp·Δe+Ki·e·Ts+Kd·(Δe−Δe_prev)/Ts.…|
|power_factor_correction|1.0.0|high_precision||예|지상(유도성) 부하의 역률을 목표 역률로 올리는 병렬 커패시턴스를 구한다. Q_c=P·(tanφ₁−tanφ₂), C=Q_c/(2π·f·V²). real_powe…|
|pump_hydraulic_power|1.0.0|high_precision||예|펌프 수력 동력 P = ρ·g·Q·H (W)를 계산하고, efficiency(0 초과 1 이하)를 주면 축동력 P/η 도 반환한다. density kg/m³, …|
|rc_filter_cutoff|1.0.0|high_precision||예|1차 RC 필터의 -3 dB 차단 주파수 fc=1/(2πRC)를 Hz로 구한다. resistance(Ω)와 capacitance(F)는 0 초과 Decimal …|
|resistor_color_code|1.0.0|high_precision||예|저항기 4밴드 또는 5밴드 컬러코드를 해독해 저항값(Ω)과 허용오차(%)를 구한다. 4밴드는 [자릿수1, 자릿수2, 승수, 허용오차], 5밴드는 [자릿수1, 자…|
|resistor_parallel|1.0.0|exact||예|병렬 연결 저항의 합성 저항 1/R_total=Σ(1/Rᵢ)를 구한다. resistors 는 0 초과 저항값(Ω)의 Decimal 문자열 목록이며 최소 1개. …|
|resistor_series|1.0.0|exact||예|직렬 연결 저항의 합성 저항 R_total=ΣRᵢ를 구한다. resistors 는 0 초과 저항값(Ω)의 Decimal 문자열 목록이며 최소 1개. 계산은 유효…|
|rlc_time_constant|1.0.0|high_precision||예|RC, RL, 직렬 RLC 회로의 시정수 또는 감쇠 특성을 구한다. mode='rc'면 τ=RC, 'rl'이면 τ=L/R, 'rlc'면 α=R/(2L), ω₀=…|
|safety_factor|1.0.0|high_precision||예|안전율 SF = 허용응력 / \|작용응력\| 을 계산하고 SF 1 이상이면 'safe', 미만이면 'unsafe' 를 반환한다. 두 응력은 같은 단위(Pa 또는…|
|second_order_response|1.0.0|high_precision||예|2차 시스템 G(s)=ωn²/(s²+2ζωn·s+ωn²)의 감쇠 고유진동수 ωd, 최대 오버슈트, 정착시간을 구한다. damping_ratio ζ(0 이상)와 …|
|section_moment_inertia|1.0.0|high_precision||예|도심 중립축에 대한 단면 이차모멘트 I 를 계산한다. rectangle(width, height: bh³/12), circle(diameter: πd⁴/64),…|
|series_reliability|1.0.0|high_precision||예|직렬 시스템 신뢰도 R_sys = ΠR_i 를 계산한다. component_reliabilities 는 구성요소 신뢰도의 숫자 문자열 목록(1개 이상, 각 0 …|
|shear_stress|1.0.0|high_precision||예|횡전단응력 τ 를 모드별로 계산한다. average 는 V/A, rectangular_max 는 1.5V/A(직사각형 단면 중립축의 최대값, area 필요), …|
|si_prefix_convert|1.0.0|exact||예|수치를 SI 접두사 사이에서 환산한다. 결과 = value × 10^(from 지수 − to 지수)를 Decimal 로 정확히 계산한다. 접두사는 이름으로 넣고…|
|sn_fatigue_life|1.0.0|high_precision||예|바스퀸 식 S_a = S_f'·(2N_f)^b 를 N_f = 0.5·(S_a/S_f')^(1/b) 로 풀어 파손까지의 사이클 수를 구한다(반전 횟수 2N_f 가…|
|stefan_boltzmann|1.0.0|high_precision||예|회색체 표면과 주위 사이의 순복사 열전달 Q = ε·σ·A·(T_s⁴ − T_surr⁴) (W)를 계산한다. σ = 5.670374419e-8 W/(m²·K⁴)…|
|thermal_expansion_strain|1.0.0|high_precision||예|선팽창 변형률 ε = α·ΔT 를 계산하고 length(0 초과)를 주면 길이 변화 ΔL = ε·L₀ 도 반환한다. alpha 는 선팽창계수(1/K), delt…|
|thermal_resistance|1.0.0|high_precision||예|열저항 K/W 를 합성한다. topology 'series' 는 R_total = ΣRᵢ, 'parallel' 은 1/R_total = Σ(1/Rᵢ). resi…|
|thevenin_equivalent|1.0.0|exact||예|개방 전압과 단락 전류로 테브난 등가 회로를 구한다. V_th=V_oc, R_th=V_oc/I_sc. open_circuit_voltage(V)와 short_c…|
|three_phase_power|1.0.0|high_precision||예|균형 3상 회로의 피상, 유효, 무효 전력을 선간 값으로 구한다. S=√3·V_LL·I_L, P=S·cosφ, Q=√(S²−P²). line_voltage(V)…|
|torque_rotational_power|1.0.0|exact||예|회전 일률 P = τ·ω (W)를 계산한다. torque 는 N·m, angular_velocity 는 rad/s 이다. rpm 을 그대로 넣으면 틀리므로 ω …|
|weibull_reliability|1.0.0|high_precision||예|2모수 와이블 분포의 신뢰도 R(t) = exp(−(t/η)^β)와 불신뢰도를 계산한다. shape β 와 scale η 는 0 초과, time 은 η 와 같은…|

## finance (15)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|black_scholes|1.0.0|high_precision||예|Black-Scholes 유럽형 옵션의 가격과 델타, 감마, 베가, 세타, 로를 계산한다. option_type 은 call 또는 put, rate, sigma…|
|bond_duration|1.0.0|exact||예|채권의 맥컬리 듀레이션과 수정 듀레이션을 연 단위로 계산한다. face 는 양수, coupon_rate 와 ytm 은 연율 소수 Decimal 문자열, year…|
|bond_ytm|1.0.0|exact||예|채권 만기수익률(YTM)을 뉴턴법으로 구한다. price 와 face 는 양수 Decimal 문자열, coupon_rate 는 연 표면이율 소수 (예 0.05)…|
|forward_price|1.0.0|high_precision||예|무차익 선도가격을 계산한다. F = S x exp((r - y) x T), 연속복리 기준이며 income_yield(배당률이나 쿠폰수익률, 기본 0)를 차감한다…|
|futures_price|1.0.0|high_precision||예|연속복리 보유비용 모형의 선물 이론가격을 계산한다. F = S x exp((r - q) x T). spot 은 양수, risk_free_rate 와 divide…|
|fv|1.0.0|exact||예|현재 금액의 미래가치를 계산한다. FV = PV x (1+r)^n, 기간마다 복리. present_value 와 rate(기간당 이율, 0 이상, 예 0.05)…|
|irr|1.0.0|exact||예|내부수익률(IRR), 즉 NPV 를 0 으로 만드는 기간 수익률을 구한다. cashflows 는 2개 이상이며 index 0 이 t=0, 양수와 음수가 모두 있…|
|loan_schedule|1.0.0|exact||예|대출 상환 스케줄을 계산한다. method 는 EQUAL_PAYMENT(원리금균등, 기본) 또는 EQUAL_PRINCIPAL(원금균등). annual_rate …|
|npv|1.0.0|exact||예|순현재가치를 계산한다. NPV = sum(CF_t / (1+r)^t). cashflows 의 index 0 은 t=0 시점이라 할인하지 않으며 초기 투자는 음수…|
|option_payoff|1.0.0|high_precision||예|옵션의 만기 payoff 를 계산한다. option_type 은 vanilla, digital(현금 지급), asian(산술평균), barrier(up_in, …|
|pv|1.0.0|exact||예|미래 현금흐름의 현재가치를 계산한다. PV = FV / (1+r)^n. future_value 와 rate(기간당 이율, 0 이상, 예 0.05)는 Decima…|
|sharpe_ratio|1.0.0|approximate||예|샤프지수 = (평균수익률 - 무위험수익률) / 표본표준편차(n-1)를 계산한다. returns 는 기간 수익률 문자열 목록(2개 이상), risk_free_ra…|
|sortino_ratio|1.0.0|approximate||예|소르티노 비율 = (평균수익률 - 무위험수익률) / 하방편차를 계산한다. 하방편차 = sqrt(mean(min(r - rf, 0)^2)), 평균은 전체 표본 수…|
|var_historical|1.0.0|approximate||예|과거 수익률의 경험적 분위수로 VaR 와 CVaR(기대부족액)을 계산한다. returns 는 기간 수익률 문자열 목록(2개 이상), confidence 는 0 …|
|var_parametric|1.0.0|approximate||예|정규분포를 가정한 모수적 VaR 와 CVaR 를 계산한다. 표본 평균과 표본표준편차(n-1)로 VaR = -(mu + z x sigma). returns 는 기…|

## geometry (15)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|area_circle|1.0.0|high_precision||예|원의 넓이 π * r² 를 계산한다. radius 는 0 이상 Decimal 문자열이며 단위는 자유(결과는 그 단위의 제곱). π 는 mpmath 50자리로 계…|
|area_polygon|1.0.0|high_precision||예|다각형 넓이를 신발끈 공식(Shoelace)으로 계산한다. vertices 는 [[x, y], ...] 형태 Decimal 문자열 좌표이고 꼭짓점 3개 이상을 …|
|area_rectangle|1.0.0|high_precision||예|직사각형 넓이 width * height 를 Decimal 로 계산한다. 두 값은 0 이상 Decimal 문자열이며 단위는 같아야 하고 float 를 거치지 않…|
|area_triangle|1.0.0|high_precision||예|삼각형 넓이 (base * height) / 2 를 Decimal 로 계산한다. base 는 밑변, height 는 그 밑변에 수직인 높이이며 둘 다 0 이상 …|
|haversine|1.0.0|high_precision||예|하버사인 공식으로 두 지점의 지구 표면 대원 거리(km)를 계산한다. 위도(-90~90)와 경도(-180~180)는 도 단위 Decimal 문자열이고 지구 반지…|
|matrix_determinant|1.0.0|approximate||예|정방행렬 M 의 행렬식을 계산한다. M 은 n×n Decimal 문자열 2차원 리스트(n 은 200 이하). n 이 3 이하면 Decimal 로 정확히 전개하고…|
|matrix_inverse|1.0.0|approximate||예|정방행렬의 역행렬을 numpy.linalg.inv(float64)로 계산한다. M 은 n×n Decimal 문자열 2차원 리스트(n 은 200 이하). 결과 원…|
|matrix_multiply|1.0.0|approximate||예|행렬 곱 A @ B 를 Decimal 로 계산한다. A 는 m×k, B 는 k×n 의 Decimal 문자열 2차원 리스트이며 A 의 열 수와 B 의 행 수가 같…|
|matrix_solve|1.0.0|approximate||예|연립일차방정식 Ax = b 의 해 x 를 numpy.linalg.solve(float64)로 구한다. A 는 n×n Decimal 문자열 2차원 리스트, b 는…|
|vector_cross|1.0.0|high_precision||예|3차원 벡터의 외적 a × b 를 Decimal 로 계산한다. a, b 는 정확히 3개 원소의 Decimal 문자열 리스트이고 결과도 3개 원소 리스트다. 외적…|
|vector_dot|1.0.0|high_precision||예|두 벡터의 내적 Σ a_i * b_i 를 Decimal 로 계산한다. a, b 는 같은 길이의 비어 있지 않은 Decimal 문자열 리스트이며 반올림 없는 정확…|
|vector_norm|1.0.0|high_precision||예|벡터의 L-p 노름 (Σ \|v_i\|^p)^(1/p) 을 계산한다. v 는 비어 있지 않은 Decimal 문자열 리스트, p 는 1 이상의 정수(기본 2, 유…|
|volume_cuboid|1.0.0|high_precision||예|직육면체 부피 length * width * height 를 Decimal 로 계산한다. 세 값은 0 이상 Decimal 문자열이며 같은 길이 단위여야 하고 f…|
|volume_cylinder|1.0.0|high_precision||예|원기둥 부피 π * r² * h 를 계산한다. radius(밑면 반지름)와 height 는 0 이상 Decimal 문자열이며 같은 길이 단위여야 한다. π 는 …|
|volume_sphere|1.0.0|high_precision||예|구의 부피 (4/3) * π * r³ 를 계산한다. radius 는 0 이상 Decimal 문자열이며 결과 단위는 길이 단위의 세제곱이다. π 는 mpmath …|

## math (10)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|diff_central|1.0.0|exact||예|중심 차분 f'(x) ≈ (f(x+h) - f(x-h)) / (2h) 로 x 에서의 1차 도함수를 수치 근사한다. expression 은 core.calc 문법…|
|diff_five_point|1.0.0|exact||예|5점 공식 f'(x) ≈ (-f(x+2h) + 8 f(x+h) - 8 f(x-h) + f(x-2h)) / (12 h) 로 x 에서의 1차 도함수를 수치 근사한다…|
|fft|1.0.0|approximate||예|실수 샘플의 이산 푸리에 변환(DFT)을 numpy.fft 로 계산한다. samples 는 2개 이상 65536개 이하의 Decimal 문자열 리스트. 각 bi…|
|ifft|1.0.0|approximate||예|fft 결과의 bin 리스트({magnitude, phase_rad})에서 시간 영역 샘플을 복원한다(1/N 정규화 포함). 최대 65536개. real_out…|
|integrate_gauss_legendre|1.0.0|high_precision||예|가우스-르장드르 구적법(mpmath.quadgl)으로 정적분 ∫_a^b f(x) dx 의 근삿값을 구한다. expression 은 core.calc 문법, a …|
|integrate_simpson|1.0.0|high_precision||예|합성 심프슨 1/3 법으로 정적분 ∫_a^b f(x) dx 의 근삿값을 구한다. expression 은 core.calc 문법, a 와 b 는 a < b 인 D…|
|interpolate_cubic_spline|1.0.0|approximate||예|3차 스플라인 보간(scipy CubicSpline)으로 x_query 에서의 값을 구한다. xs 는 엄격히 증가하는 4개 이상의 Decimal 문자열 리스트,…|
|interpolate_linear|1.0.0|approximate||예|표본점 (xs, ys) 를 직선으로 이어 x_query 에서의 값을 구하는 1차원 선형 보간이다. xs 는 엄격히 증가하는 2개 이상의 Decimal 문자열 리…|
|polynomial_horner|1.0.0|approximate||예|호너 방법으로 다항식 P(x) 를 Decimal 로 평가한다. coefficients 는 높은 차수부터 내림차순(예 [1, 0, -4] 는 x² - 4), x …|
|polynomial_roots|1.0.0|approximate||예|다항식의 모든 근(복소근 포함)을 numpy.roots 로 구한다. coefficients 는 높은 차수부터 내림차순 Decimal 문자열 리스트(예 [1, 0…|

## medical (12)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|bmi|1.0.0|high_precision||예|체질량지수(BMI)를 계산하고 WHO 기준으로 분류한다. BMI = weight_kg / height_m^2, 입력은 미터와 킬로그램의 Decimal 문자열, …|
|bsa|1.0.0|high_precision||예|체표면적(BSA)을 m² 단위로 계산한다. 입력은 신장 cm, 체중 kg의 Decimal 문자열, 결과는 소수 4자리 HALF_EVEN 반올림. method=d…|
|cha2ds2_vasc|1.0.0|exact||예|심방세동 환자의 뇌졸중 위험 점수 CHA2DS2-VASc를 계산한다. C=울혈성심부전, H=고혈압, A2=75세 이상(2점), D=당뇨, S2=뇌졸중/TIA(2…|
|dose_weight_based|1.0.0|exact||예|체중 기반 약물 용량을 계산한다. dose = weight_kg * dose_per_kg, max_dose를 주면 초과 시 max_dose로 제한하고 cappe…|
|egfr|1.0.0|exact||예|혈청 크레아티닌으로 추정 사구체여과율(eGFR)을 CKD-EPI 2021(인종 계수 없음) 식으로 계산하고 KDIGO 2012 CKD 병기(G1~G5)를 돌려준…|
|framingham_cvd_10y|1.0.0|exact||예|Framingham 일반 10년 심혈관질환 발생 확률을 계산한다(D'Agostino 2008 일반 CVD 모델). sex=male\|female, age 30~…|
|has_bled|1.0.0|exact||예|항응고 치료 환자의 주요 출혈 위험 점수 HAS-BLED를 계산한다. H=고혈압, A=신장 또는 간 기능 이상(각 1점), S=뇌졸중, B=출혈력, L=불안정 …|
|pregnancy_weeks|1.0.0|exact||예|최종 월경일(LMP)로 임신 주수와 분만예정일(EDD)을 계산한다. 입력은 YYYY-MM-DD 문자열이며 reference_date를 생략하면 서버의 오늘 날짜…|
|qtc_bazett|1.0.0|high_precision||예|Bazett 공식으로 QT 간격을 심박수에 맞춰 보정한다. QTc = QT / sqrt(RR). qt와 rr은 Decimal 문자열이며 unit='ms'(기본)…|
|qtc_framingham|1.0.0|high_precision||예|Framingham 선형 공식으로 QT 간격을 보정한다. QTc = QT + 0.154 * (1 - RR_초). qt와 rr은 Decimal 문자열이며 unit…|
|qtc_fridericia|1.0.0|high_precision||예|Fridericia 공식으로 QT 간격을 심박수에 맞춰 보정한다. QTc = QT / RR^(1/3). qt와 rr은 Decimal 문자열이며 unit='ms'…|
|qtc_hodges|1.0.0|high_precision||예|Hodges 공식으로 QT 간격을 심박수에 맞춰 보정한다. QTc_ms = QT_ms + 1.75 * (HR - 60), HR = 60 / RR_초. qt와 r…|

## payroll (15)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|hourly_to_monthly_net|1.1.0|exact|예|예|시급(원, 문자열)을 월 환산시간(기본 209시간, 주 40시간과 주휴 포함)에 곱해 월급으로 바꾸고 원 미만을 버린 뒤 payroll.kr_salary 로 4…|
|kr_bonus_tax|2.0.0|exact|예|예|상여금 원천징수세액을 근로소득 간이세액표로 구한다. method=averaging(기본, 소득세법 제136조제1항제1호)은 상여를 지급대상기간 월수(1~12, …|
|kr_donation_deduction|1.1.0|exact|예|예|기부금 세액공제(소득세법 제59조의4제4항, 조세특례제한법 제76조)를 구한다. 근로소득금액(원 문자열) 기준 한도 안에서 특례·일반기부금 합계 1천만원 이하 …|
|kr_education_deduction|1.0.0|exact|예|예|교육비 세액공제(소득세법 제59조의4제3항)를 구한다. expenses 는 self, preschool, elementary, middle_high, unive…|
|kr_gross_from_net|2.0.0|exact|예|예|역산: 세후 월급(net_monthly, 원 문자열)에서 세전 월급을 구한다. payroll.kr_salary 의 실수령액이 목표 이상이 되는 가장 작은 정수 …|
|kr_health_income_premium|1.0.0|exact|예|예|건강보험 직장가입자의 보수 외 소득월액보험료(국민건강보험법 제71조: 연 2천만원 초과분의 1/12, 근로·연금소득 50% 평가, 이자·배당 1천만원 이하 제외…|
|kr_housing_loan_deduction|1.0.0|exact|예|예|장기주택저당차입금 이자상환액 소득공제(소득세법 제52조제5항·제6항)의 공제 대상액을 구한다. 이자상환액(원 문자열), 상환기간(년), 고정금리와 비거치식 여부…|
|kr_medical_deduction|1.1.0|exact|예|예|의료비 세액공제(소득세법 제59조의4제2항)를 구한다. 총급여(원 문자열)의 3% 미달분을 일반, 특수, 미숙아, 난임 순으로 차감한 뒤 일반 의료비 15%(연…|
|kr_minimum_wage_check|1.0.0|exact|예|예|한국 최저임금 충족 여부를 검토한다(최저임금법 제5조·제6조, 시행령 제5조, 연도별 고시). wage_amount 는 wage_unit 단위의 매월 정기 지급…|
|kr_national_pension_benefit|1.0.0|exact|예|예|국민연금 노령연금 예상액을 국민연금법 제51조 기본연금액 산식(A값, 구간별 비례상수 2.4~1.29, 20년 초과 연 5% 가산), 제63조 가입기간별 지급률…|
|kr_overtime_pay|1.0.0|exact|예|예|한국 연장·야간·휴일근로수당을 계산한다(근로기준법 제56조, 시행령 제6조). ordinary_wage 는 통상임금(원)이고 wage_unit 으로 시급·일급·…|
|kr_salary|2.0.0|exact|예|예|세전 월급(원, 문자열)에서 한국 실수령액을 구한다. 비과세 식대 한도를 뺀 과세급여로 4대보험 근로자 부담분(국민연금 상·하한, 건강보험, 장기요양, 고용보험…|
|kr_severance_pay|1.0.0|exact|예|예|퇴직소득세(소득세법 제48조·제55조)를 구한다. 퇴직급여총액, 근속연수(년, 소수 가능), 비과세액(원 문자열)에서 근속연수공제, 환산급여(12배 후 근속연수…|
|kr_weekly_holiday_pay|1.0.0|exact|예|예|한국 주휴수당을 계산한다(근로기준법 제55조제1항·제18조제3항, 시행령 제30조·별표 2). weekly_contract_hours 는 4주 평균 1주 소정근…|
|kr_year_end_tax_settlement|2.0.0|exact|예|예|연말정산 환급 또는 추가납부액을 간이 모델로 구한다. 연간 총급여에서 근로소득공제, 인당 기본공제, 추가 소득공제를 뺀 과세표준에 소득세 누진세율을 적용하고 근…|

## pm (5)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|critical_path|1.0.0|exact||예|작업 의존 관계로 주공정법(CPM) 일정을 계산해 각 작업의 ES, EF, LS, LF, 여유(slack)와 총 기간, 여유가 0인 주공정 작업 목록을 돌려준다…|
|earned_schedule|1.0.0|exact||예|획득일정(Earned Schedule) 지표를 계산한다. ES는 획득가치(EV)에 해당하는 계획 시점으로 pv_timeline을 선형 보간해 역산하고, SPI(…|
|evm|1.0.0|exact||예|획득가치관리(EVM) 지표를 계산한다. SPI=EV/PV, CPI=EV/AC, SV=EV-PV, CV=EV-AC, EAC=BAC/CPI, ETC=EAC-AC, …|
|monte_carlo_schedule|1.0.0|approximate||예|작업별 낙관, 최빈, 비관 추정으로 프로젝트 총 소요 시간의 분포를 몬테카를로로 시뮬레이션해 P10, P50, P90, 평균, 표본 표준편차를 돌려준다. tas…|
|pert|1.0.0|high_precision||예|단일 작업의 PERT 삼점 추정으로 기대 기간, 분산, 표준편차를 계산한다. E=(O+4M+P)/6, V=((P-O)/6)², 표준편차는 sqrt(V). 낙관,…|

## probability (30)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|bayes|1.0.0|exact||예|베이즈 정리로 사후확률 P(A\|B) = P(A)P(B\|A)/P(B)를 구한다. prior, likelihood, marginal 은 [0, 1] 구간 십진 …|
|beta_cdf|1.0.0|approximate||예|베타분포의 누적확률 P(X ≤ x) = I_x(α, β)를 구한다. x 는 [0, 1] 구간, alpha 와 beta 는 양수 십진 문자열이며 scipy flo…|
|beta_pdf|1.0.0|approximate||예|베타분포의 확률밀도 f(x; α, β)를 구한다. x 는 [0, 1] 구간, alpha 와 beta 는 양수 십진 문자열이며 scipy float64 계산 후 …|
|beta_ppf|1.0.0|approximate||예|베타분포의 분위수를 구한다. q 는 0 초과 1 미만, alpha 와 beta 는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반…|
|binomial_cdf|1.0.0|approximate||예|이항분포의 누적확률 P(X ≤ k; n, p)를 구한다. k 와 n 은 0 이상 정수(k ≤ n), p 는 [0, 1] 구간 십진 문자열이며 scipy floa…|
|binomial_pmf|1.0.0|approximate||예|이항분포의 확률질량 P(X=k; n, p)를 구한다. k 와 n 은 0 이상 정수(k ≤ n), p 는 [0, 1] 구간 십진 문자열이며 scipy float6…|
|chi_square_cdf|1.0.0|approximate||예|카이제곱분포의 누적확률 P(X ≤ x)를 구한다. x 는 0 이상, df(자유도)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 …|
|chi_square_pdf|1.0.0|approximate||예|카이제곱분포의 확률밀도를 구한다. x 는 0 이상, df(자유도)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 문자열을…|
|chi_square_ppf|1.0.0|approximate||예|카이제곱분포의 분위수를 구한다. q 는 0 초과 1 미만, df(자유도)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리로 반올림한 …|
|expected_value|1.0.0|exact||예|이산 확률변수의 기댓값 E[X] = Σ value_i * prob_i 를 구한다. values 와 probabilities 는 같은 길이의 십진 문자열 리스트이…|
|exponential_cdf|1.0.0|approximate||예|지수분포의 누적확률 P(X ≤ x) = 1 - e^(-λx)를 구한다. x 는 0 이상, rate(λ)는 양수 십진 문자열이며 scipy float64 계산 후…|
|exponential_pdf|1.0.0|approximate||예|지수분포의 확률밀도 f(x; λ) = λe^(-λx)를 구한다. x 는 0 이상, rate(λ)는 양수 십진 문자열이며 scipy float64 계산 후 유효숫…|
|exponential_ppf|1.0.0|approximate||예|지수분포의 분위수 x = -ln(1-q)/λ 를 구한다. q 는 0 초과 1 미만, rate(λ)는 양수 십진 문자열이며 scipy float64 계산 후 유효…|
|f_cdf|1.0.0|approximate||예|F 분포의 누적확률 P(X ≤ x)를 구한다. x 는 0 이상, dfn 은 분자 자유도, dfd 는 분모 자유도(둘 다 양수 십진 문자열)이며 scipy flo…|
|f_pdf|1.0.0|approximate||예|F 분포의 확률밀도를 구한다. x 는 0 이상, dfn 은 분자 자유도, dfd 는 분모 자유도(둘 다 양수 십진 문자열)이며 scipy float64 계산 후…|
|f_ppf|1.0.0|approximate||예|F 분포의 분위수를 구한다. q 는 0 초과 1 미만, dfn 은 분자 자유도, dfd 는 분모 자유도(둘 다 양수 십진 문자열)이며 scipy float64 …|
|factorial|1.0.0|high_precision||예|n!을 정확한 정수 문자열로 반환한다. n 은 0 이상 정수이며 상한은 20000(환경변수 SOOTOOL_LIMIT_COMBINATORICS_N 으로 조정), …|
|gamma_cdf|1.0.0|approximate||예|감마분포의 누적확률 P(X ≤ x)를 구한다. x 는 0 이상, shape(k)는 양수, scale(θ, 기본 1)은 양수 십진 문자열이며 scipy float…|
|gamma_pdf|1.0.0|approximate||예|감마분포의 확률밀도 f(x; k, θ)를 구한다. x 는 0 이상, shape(k)는 양수, scale(θ, 기본 1)은 양수 십진 문자열이며 scipy flo…|
|gamma_ppf|1.0.0|approximate||예|감마분포의 분위수를 구한다. q 는 0 초과 1 미만, shape(k)는 양수, scale(θ, 기본 1)은 양수 십진 문자열이며 scipy float64 계산…|
|lognormal_cdf|1.0.0|approximate||예|로그정규분포의 누적확률 P(X ≤ x) = Φ((ln x - μ)/σ)를 구한다. x 는 양수, mu 와 sigma 는 ln X 의 평균과 표준편차(sigma …|
|lognormal_pdf|1.0.0|approximate||예|로그정규분포의 확률밀도를 구한다. x 는 양수, mu 와 sigma 는 ln X 의 평균과 표준편차(sigma 는 양수, 기본 0 과 1)이며 scipy flo…|
|lognormal_ppf|1.0.0|approximate||예|로그정규분포의 분위수 exp(μ + σΦ⁻¹(q))를 구한다. q 는 0 초과 1 미만, mu 와 sigma 는 ln X 의 평균과 표준편차(sigma 는 양수…|
|nCr|1.0.0|high_precision||예|이항계수 C(n, r) = n!/(r!(n-r)!)을 정확한 정수 문자열로 반환한다. n, r 은 0 이상 정수(r ≤ n, n 상한 20000)이며 반올림은 …|
|nPr|1.0.0|high_precision||예|순열 P(n, r) = n!/(n-r)!을 정확한 정수 문자열로 반환한다. n, r 은 0 이상 정수(r ≤ n, n 상한 20000)이며 반올림은 없다. 순서…|
|normal_cdf|1.0.0|approximate||예|정규분포의 누적확률 P(X ≤ x)를 구한다. x, mu(평균, 기본 0), sigma(표준편차, 양수, 기본 1)는 십진 문자열이며 scipy float64 …|
|normal_pdf|1.0.0|approximate||예|정규분포의 확률밀도 f(x; μ, σ)를 구한다. x, mu(평균, 기본 0), sigma(표준편차, 양수, 기본 1)는 십진 문자열이며 scipy float6…|
|normal_ppf|1.0.0|approximate||예|정규분포의 분위수 x = μ + σΦ⁻¹(q)를 구한다. q 는 0 초과 1 미만 확률, mu(기본 0), sigma(표준편차, 양수, 기본 1)이며 scipy…|
|poisson_cdf|1.0.0|approximate||예|포아송분포의 누적확률 P(X ≤ k; λ)를 구한다. k 는 0 이상 정수, lam(λ)은 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10…|
|poisson_pmf|1.0.0|approximate||예|포아송분포의 확률질량 P(X=k; λ)를 구한다. k 는 0 이상 정수, lam(λ)은 양수 십진 문자열이며 scipy float64 계산 후 유효숫자 10자리…|

## realestate (10)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|kr_acquisition_tax|1.1.0|exact|예|예|한국 주택 유상취득 취득세와 농어촌특별세·지방교육세를 계산한다. 표준세율은 6억 이하 1%, 6억 초과 9억 이하 산식 세율, 9억 초과 3%이고, 조정 2주택…|
|kr_comprehensive|1.1.0|exact|예|예|주택분 종합부동산세와 농어촌특별세(종부세의 20%)를 계산한다. 공시가격 합계(원)에서 기본공제 후 공정시장가액비율을 곱한 과세표준에 2주택 이하·3주택 이상 …|
|kr_dsr|1.1.0|exact|예|예|DSR(총부채원리금상환비율 = 연간 원리금 상환액 / 연간 소득, 원 단위 문자열)을 계산하고 한도 이내인지 판정한다. 소수 4자리 HALF_EVEN 반올림, …|
|kr_dti|1.1.0|exact|예|예|DTI(총부채상환비율 = 월 원리금 상환액 / 월 소득, 원 단위 문자열)를 계산하고 한도 이내인지 판정한다. 소수 4자리 HALF_EVEN 반올림, 규제지역 …|
|kr_local_property|1.1.0|exact|예|예|광역자치단체(seoul, gyeonggi, busan, incheon, daegu, daejeon, gwangju, ulsan, sejong)별 주택 취득세 또…|
|kr_ltv|1.1.0|exact|예|예|LTV(대출액 / 주택가액, 원 단위 문자열, 소수 4자리 HALF_EVEN)를 계산하고 한도 이내 여부와 최대 대출액을 구한다. 한도 비율은 규제지역·수도권,…|
|kr_property_tax|1.1.0|exact|예|예|한국 주택 재산세(지방세법 §110~§111의2)와 지방교육세·도시지역분을 계산한다. 공시가격(원)에 공정시장가액비율(일반 60%, 1세대 1주택은 시가표준액 …|
|kr_subscription_score|1.0.0|exact|예|예|주택공급에 관한 규칙 별표 1의 청약 가점제 점수(무주택기간 32, 부양가족 35, 청약저축 가입기간 17, 합계 84점)를 계산한다. 기간은 입주자모집공고일 …|
|kr_transfer_tax|1.0.0|exact|예|예|한국 부동산 양도소득세를 tax.capital_gains_kr 에 위임해 계산하고 domain, module 표식을 붙인다. 금액은 원 단위 문자열, 세액은 d…|
|rental_yield|1.0.0|exact||예|임대수익률을 백분율(%) 문자열로 계산한다. gross 는 연간 임대수입 / 매입가격, net 은 (연간 임대수입 - 연간 비용) / 매입가격이며 금액은 원 단…|

## science (11)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|battery_capacity|1.0.0|high_precision||예|배터리 용량을 Ah와 Wh 사이에서 변환한다. Wh = Ah * V, Ah = Wh / V. mode='ah_to_wh'(기본) 또는 'wh_to_ah', va…|
|bragg|1.0.0|high_precision||예|브래그 회절 조건 n*lambda = 2 d sin(theta)에서 파장, 면간격, 회절각 중 하나를 구한다. order는 양의 정수이고 wavelength, …|
|faraday_electrolysis|1.0.0|high_precision||예|패러데이 법칙으로 전기분해 시 석출되는 질량(g)을 계산한다. m = (I * t * M) / (n * F). current_a는 암페어, time_s는 초, …|
|half_life|1.0.0|high_precision||예|방사성 붕괴로 남은 양을 계산한다. N(t) = N0 x 0.5^(t/T). initial_amount는 양수, half_life는 양수, elapsed_tim…|
|ideal_gas|1.0.0|exact||예|이상 기체 법칙 PV = nRT에서 빠진 변수 하나를 계산한다. 압력 Pa, 부피 m³, 물질량 mol, 온도 K 중 정확히 3개를 Decimal 문자열로 주고…|
|intensity|1.0.0|high_precision||예|빛이나 복사의 세기(단위 면적당 전력)를 계산한다. I = P / A. power_w는 0 이상 와트, area_m2는 양수 제곱미터의 Decimal 문자열이며…|
|molar_mass|1.0.0|exact||예|화학식으로 몰질량(g/mol)을 계산하고 원소별 원자 수(composition)를 돌려준다. 원소 기호는 대소문자를 구분하며 괄호 Ca(OH)2, 수화물 CuS…|
|nernst|1.0.0|high_precision||예|Nernst 방정식으로 비표준 조건의 전극 전위를 V 단위로 계산한다. E = E0 - (RT / nF) * ln(Q). e0(V)와 reaction_q(양수)…|
|snell_law|1.0.0|high_precision||예|스넬의 법칙으로 굴절각을 계산한다. n1 sin(theta1) = n2 sin(theta2), theta2 = asin(n1/n2 * sin(theta1)). …|
|stoichiometry|1.0.0|exact||예|균형 맞춘 반응식 계수로 한계 반응물을 찾고 각 물질의 몰수(mol)와 질량(g)을 계산한다. reactants는 {formula, mass(g) 또는 mole…|
|thin_lens|1.0.0|high_precision||예|얇은 렌즈 방정식 1/f = 1/p + 1/q에서 빠진 값 하나(초점거리, 물체거리, 상거리)를 구하고 배율 m = -q/p도 돌려준다. 세 인자 중 정확히 2…|

## sootool (12)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|policy_activate|1.0.0|not_numeric||아니오|[관리자] 검증을 통과한 초안을 덮어쓰기 저장소에 반영하고 캐시를 비우며 감사 기록을 남긴다. 검증 오류가 있는 초안은 validation_failed 로 거부…|
|policy_diff|1.0.0|not_numeric||예|정책 두 버전의 구간별 세율과 주요 값 변경을 비교한다. year_from 과 year_to 로 연도 간 비교하거나 draft_id 로 초안과 현재 시행본을 비…|
|policy_export|1.0.0|not_numeric|예|예|정책 하나를 이식 가능한 묶음(원본 YAML과 메타데이터)으로 내보낸다. domain, name, year 로 지정하고 as_of, include_propose…|
|policy_get|1.0.0|not_numeric|예|예|정책 파일 하나의 내용(data)과 출처(package 또는 override), 버전 정보를 반환한다. domain, name, year 로 지정하고 as_of…|
|policy_history|1.0.0|not_numeric||예|정책 하나(domain, name)의 변경 감사 기록을 기록된 순서대로 반환한다. 항목마다 action(activate, rollback, import), 시각…|
|policy_import|1.0.0|not_numeric||아니오|[관리자] sootool.policy_export 가 만든 묶음을 검증한 뒤 덮어쓰기 저장소에 반영한다. require_signature 와 public_key…|
|policy_list|1.0.0|not_numeric||예|패키지와 덮어쓰기 저장소의 모든 정책 파일 목록을 반환한다. 항목마다 영역, 이름, 연도, 출처(package 또는 override), 시행일, 종료일, 상태,…|
|policy_propose|1.0.0|not_numeric||아니오|[관리자] 정책 초안을 만든다. 6단계 검증 보고서와 전년도 대비 변경점을 반환하며 아직 시행되지 않는다. 관리자 모드(SOOTOOL_ADMIN_MODE=1)가…|
|policy_rollback|1.0.0|not_numeric||아니오|[관리자] 덮어쓰기 저장소의 정책 버전 파일을 지워 패키지 기본값으로 되돌린다. 같은 연도에 덮어쓴 버전이 여럿이면 effective_date(YYYY-MM-D…|
|policy_validate|1.0.0|not_numeric||예|정책 YAML 문자열을 검증해 보고서(status, findings, sha256)를 반환한다. name 을 주면 도메인 스키마까지 검사하고 파일은 저장하지 않…|
|skill_guide|1.0.0|not_numeric||예|에이전트용 능동 활용 가이드를 반환한다. section 은 triggers(호출 신호표), examples, anti_patterns, playbooks, al…|
|verify_receipt|1.0.0|depends_on_children||예|계산 영수증(_meta.integrity)을 재실행으로 검증한다. tool 과 arguments 로 같은 계산을 다시 실행해 입력 해시, 결과 해시, 도구 버전…|

## stats (14)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|anova_oneway|1.0.0|approximate||예|둘 이상 집단의 평균 차이를 일원분산분석(one-way ANOVA)으로 검정하고 Tukey HSD 쌍별 비교를 덧붙인다. groups는 집단별 Decimal 문…|
|bootstrap_ci|1.0.0|approximate||예|표본 평균 또는 중앙값의 부트스트랩 신뢰구간을 백분위수법으로 구한다. values는 Decimal 문자열 2개 이상, statistic은 mean 또는 medi…|
|chi_square_independence|1.0.0|approximate||예|분할표의 두 범주형 변수가 독립인지 카이제곱 검정으로 판정해 chi2, df, p_value, 기대빈도 표를 돌려준다. observed는 관측 빈도의 2x2 이…|
|ci_mean|1.0.0|approximate||예|표본 평균의 양측 신뢰구간을 t-분포로 계산해 mean, lower, upper를 돌려준다. values는 Decimal 문자열 2개 이상, confidence…|
|cohens_d|1.0.0|approximate||예|두 독립 표본의 효과크기 Cohen's d와 소표본 보정값 Hedges's g를 계산한다. d = (a 평균 - b 평균) / 풀드 표준편차이며 a 평균이 크면…|
|descriptive|1.0.0|approximate||예|숫자 목록의 기술통계량(n, mean, median, variance, stdev, min, max, q1, q3)을 계산한다. values는 Decimal 문…|
|eta_squared|1.0.0|approximate||예|일원분산분석의 효과크기 eta^2(편향 있음)와 omega^2(편향 보정)를 계산하고 F, p값, 자유도도 함께 돌려준다. groups는 집단별 Decimal …|
|kruskal_wallis|1.0.0|approximate||예|독립 여러 집단의 분포 위치 차이를 순위 기반 Kruskal-Wallis H 검정으로 판정해 h_stat, p_value, df(집단 수-1)를 돌려준다. gr…|
|mann_whitney_u|1.0.0|approximate||예|독립 두 표본의 분포 위치 차이를 순위 기반 Mann-Whitney U 검정으로 판정해 u_stat, p_value, n_a, n_b를 돌려준다. a, b는 D…|
|regression_linear|1.0.0|approximate||예|최소제곱(OLS) 선형회귀로 계수, 절편, R², 계수별 p값, 잔차를 구한다. X는 표본 수 x 특징 수의 Decimal 문자열 행렬, y는 표본 수 길이의 …|
|ttest_one_sample|1.0.0|approximate||예|표본 평균이 기준값 popmean과 다른지 일표본 t-검정으로 판정해 t, df(n-1), p_value, ci_95를 돌려준다. values는 Decimal …|
|ttest_paired|1.0.0|approximate||예|같은 대상의 전후 측정 등 대응표본의 평균 차이를 t-검정으로 판정해 t, df(n-1), p_value, ci_95(a 평균 - b 평균의 95% 구간)를 돌…|
|ttest_two_sample|1.0.0|approximate||예|독립 두 표본의 평균 차이를 t-검정으로 판정해 t, df, p_value, ci_95(a 평균 - b 평균의 95% 구간)를 돌려준다. a, b는 Decima…|
|wilcoxon|1.0.0|approximate||예|Wilcoxon 부호순위 검정으로 대응표본의 차이 또는 단일 표본의 0 기준 위치 이동을 판정해 w_stat, p_value, n을 돌려준다. b를 주면 a와 …|

## symbolic (2)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|diff|1.0.0|high_precision||예|sympy 로 n차 기호 도함수를 구하고, variables 로 값을 치환하면 그 지점의 수치를 Decimal 문자열(50자리)로 함께 반환한다. var 는 미…|
|solve|1.0.0|high_precision||예|sympy 로 방정식을 기호 풀이한다. equation 은 'lhs = rhs' 또는 단일식(=0 가정), var 는 풀 변수이며 variables 값은 풀기 …|

## tax (16)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|capital_gains_kr|2.0.0|exact|예|예|한국 양도소득세를 계산한다(소득세법 제89조·제95조·제103조·제104조). 금액은 원 단위 Decimal 문자열, 보유·거주 기간은 만 년 정수다. 1세대1…|
|kr_corporate|1.0.0|exact|예|예|한국 법인세를 계산한다(법인세법 제55조, 조세특례제한법 제132조). taxable_income 은 과세표준(원, Decimal 문자열)이고 누진 구간 산출세…|
|kr_education_tax_add|1.0.0|exact||예|한국 지방교육세를 본세 x 부가세율로 계산한다(지방세법 제151조). base_tax 는 재산세·취득세·등록면허세 등 본세액(원, 0 이상 Decimal 문자열…|
|kr_eitc|1.0.0|exact|예|예|한국 근로장려금(조특법 §100의3·§100의5·§100의7) 산정. year 는 소득 귀속연도, 금액은 원 단위 숫자 문자열. 가구유형(single/one_e…|
|kr_gift|1.0.0|exact|예|예|한국 증여세를 계산한다(상속세및증여세법 제53조·제53조의2·제56조·제57조·제69조). 금액은 원 단위 Decimal 문자열이다. 관계별 증여재산공제에서 1…|
|kr_income|1.0.0|exact|예|예|한국 종합소득세·근로소득세 산출세액을 소득세법 제55조 기본세율(6~45% 누진, 정책 YAML)로 계산한다. taxable_income 은 공제를 모두 뺀 과…|
|kr_inheritance|1.0.0|exact|예|예|한국 상속세를 계산한다(상속세및증여세법 제18조~제21조·제24조·제26조·제69조). 금액은 원 단위 Decimal 문자열이다. 기초·인적공제와 일괄공제 5억…|
|kr_local_income_tax|1.0.0|exact||예|한국 개인 지방소득세를 소득세 본세의 10% 고정 비율로 계산한다(지방세법 제92조). income_tax 는 이미 산출된 소득세액(원, 0 이상 Decimal…|
|kr_pension_income|1.0.0|exact|예|예|한국 사적연금(연금계좌) 인출 원천징수, 분리과세 판정, 연금소득공제를 계산한다(소득세법 제129조, 제14조, 제47조의2). 금액은 원 문자열이며 priva…|
|kr_registration_license_tax|1.0.0|exact|예|예|부동산 등기의 등록면허세와 지방교육세(20%)를 계산한다(지방세법 제28조제1항제1호, 제151조). 저당권, 전세권, 지상권, 지역권, 임차권, 경매신청, 가…|
|kr_rural_special_tax|1.0.0|exact||예|한국 농어촌특별세를 계산한다(농어촌특별세법 제5조). mode=base 는 본세액 x 10%, mode=reduced 는 감면세액 x 20%이고 amount 는…|
|kr_securities_transaction|1.0.0|exact|예|예|한국 주식 양도 시 증권거래세와 농어촌특별세를 계산한다(증권거래세법 제8조, 시행령 제5조 탄력세율, 농특세법 제5조). transfer_amount 는 양도가…|
|kr_simplified_vat|1.0.0|exact|예|예|한국 간이과세자 부가가치세를 계산한다(부가가치세법 제46조·제61조·제63조·제69조). 금액은 원 단위 Decimal 문자열이다. 공급대가 x 업종별 부가가치…|
|kr_vehicle_tax|1.0.0|exact|예|예|한국 승용자동차 자동차세 연세액과 지방교육세(비영업용 30%)를 계산한다(지방세법 제127조, 제128조, 제151조). 배기량은 cc 정수, 차령기산일은 YY…|
|kr_withholding_simple|2.0.0|exact|예|예|근로소득 월 원천징수세액을 소득세법 시행령 별표 2 간이세액표로 구한다. monthly_salary 는 비과세·학자금을 뺀 월급여액(원, Decimal 문자열)…|
|progressive|1.0.0|exact||예|임의의 누진세율 구간표로 세액을 계산한다. taxable_income 은 0 이상의 Decimal 문자열, brackets 는 오름차순 {upper, rate}…|

## tax_us (4)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|capital_gains|1.0.0|exact|예|예|미국 연방 자본이득세를 계산한다. 장기(long)는 0%/15%/20% 구간을 신고 유형별로 적용하며 ordinary_taxable_income 위에 양도소득을…|
|federal_income|1.0.0|exact|예|예|미국 연방 소득세(일반 세율)를 계산한다. IRS 2025·2026 tax year, 7개 누진 구간, 4개 신고 유형이며 qualifying_surviving…|
|fica|1.0.0|exact|예|예|미국 FICA 급여세(IRC 3101, 3111) 근로자·고용주 부담분과 자영업세 SECA(IRC 1401, 순이익의 92.35%)를 과세연도 정책으로 계산한다…|
|state_tax|1.0.0|exact|예|예|미국 주 소득세를 계산한다(CA, NY, TX). 신고 유형별 누진 구간과 주별 표준공제를 반영하고 TX 는 소득세가 없어 0이다. NY 는 조정총소득(stat…|

## units (8)

|도구|버전|정확도|정책|읽기 전용|설명|
|-|-|-|-|-|-|
|convert|1.0.0|exact||예|pint 로 물리 단위를 변환한다. magnitude 는 Decimal 문자열, from_unit 과 to_unit 은 pint 단위 이름(meter, foot…|
|data_size_convert|1.0.0|exact||예|데이터 크기 단위를 바이트 기준으로 변환한다. mode 'si'(b, B, kB, MB, GB, TB, PB, 1000 배, b 는 비트, 기본)와 'iec'(…|
|energy_convert|1.0.0|exact||예|에너지 단위를 J 기준 Decimal 계수로 변환한다. 지원 단위는 J, kJ, cal, kcal, eV, BTU, Wh, kWh 이며 대소문자를 구분하고 ma…|
|fx_convert|1.0.0|exact||예|amount * rate 를 to_ccy 의 소수 자릿수로 반올림해 amount(문자열)와 currency 를 반환한다. 자릿수는 JPY, KRW 등 0, US…|
|fx_triangulate|1.0.0|exact||예|중간 통화를 거치는 삼각 환산 amount * rate1 * rate2 를 to_ccy 의 소수 자릿수로 한 번만 반올림해 amount(문자열)와 currenc…|
|pressure_convert|1.0.0|exact||예|압력 단위를 Pa 기준 Decimal 계수로 변환한다. 지원 단위는 Pa, kPa, MPa, atm, bar, mbar, psi, mmHg, torr 이며 대소…|
|temperature|1.0.0|exact||예|섭씨(C), 화씨(F), 켈빈(K), 랭킨(R) 사이에서 온도를 변환한다. value 는 Decimal 문자열, from_scale 과 to_scale 은 대소…|
|time_small_convert|1.0.0|exact||예|짧은 시간 단위 s, ms, us, ns, ps, min, hour, day 사이를 pint 로 변환한다. magnitude 는 Decimal 문자열이고 단위는…|
