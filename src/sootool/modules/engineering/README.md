# engineering

전기·전자, 유체, 열전달, 재료역학, 기계요소, 제어, 신뢰성 공학 계산 도구. 이 네임스페이스는 도구를 더 늘리지 않으며 버그 수정만 한다.

|도구|계산|엔진|
|-|-|-|
|`engineering.ac_impedance`|R, L, C 조합의 AC 합성 임피던스 크기와 위상각을 구한다.|mpmath|
|`engineering.beam_deflection`|표준 하중 조건의 보 최대 처짐 δ_max 를 계산한다.|mpmath|
|`engineering.bearing_equivalent_load`|베어링 동등가하중 P = X·Fr + Y·Fa 를 계산한다.|mpmath|
|`engineering.bearing_life_l10`|구름 베어링 기본정격수명 L10 = (C/P)^p 를 백만 회전(10⁶ rev) 단위로 계산한다.|mpmath|
|`engineering.bending_stress`|휨응력 σ = M·c/I 를 계산한다.|mpmath|
|`engineering.bernoulli`|베르누이 방정식 P + ½ρv² + ρgz = 일정 을 풀어 상태 2의 미지수 하나를 구한다.|mpmath|
|`engineering.bode_magnitude_phase`|단일 극점 또는 영점 1차 전달함수의 Bode 크기(dB)와 위상(도)을 구한다.|mpmath|
|`engineering.capacitor_combine`|커패시터 여러 개의 합성 정전용량을 구한다.|mpmath|
|`engineering.convective_heat_transfer`|뉴턴 냉각 법칙에 따른 대류 열전달 Q = h·A·(T_s − T_∞) (W)를 계산한다.|mpmath|
|`engineering.darcy_weisbach`|다르시-바이스바흐 식으로 관 마찰 손실 수두와 압력강하를 계산한다.|mpmath|
|`engineering.db_convert`|dB, Np, dBm과 선형 값을 서로 변환한다.|mpmath|
|`engineering.elastic_modulus_relate`|E, G, ν, K 중 두 값으로 나머지 두 값을 구한다.|Decimal|
|`engineering.electrical_ohm`|옴의 법칙 V=IR에서 빠진 한 값을 구한다.|Decimal|
|`engineering.electrical_power`|직류 전력 방정식 P=VI=I²R=V²/R에서 나머지 값을 구한다.|Decimal|
|`engineering.euler_buckling`|오일러 좌굴 임계하중 P_cr = π²EI/(KL)² (N)를 계산한다.|mpmath|
|`engineering.exponential_reliability`|지수분포 고장 모델의 신뢰도 R(t) = exp(−λt), 불신뢰도 1−R, 평균 고장간격 MTBF = 1/λ 를 계산한다.|mpmath|
|`engineering.first_order_response`|1차 시스템 G(s)=K/(τs+1)의 스텝 응답 y(t)=K·u·(1−exp(−t/τ))를 구한다.|mpmath|
|`engineering.fluid_reynolds`|레이놀즈 수 Re = ρvL/μ 를 계산하고 층류(Re < 2300), 천이(2300 이상 4000 이하), 난류(4000 초과)로 분류한다.|mpmath|
|`engineering.fourier_heat_conduction`|1차원 정상상태 평판 열전도 Q = k·A·(T_hot − T_cold)/L (W)를 계산한다.|mpmath|
|`engineering.gear_ratio`|단순 기어쌍의 기어비 i = 피동 잇수 / 구동 잇수 를 계산하고 방향을 함께 반환한다.|mpmath|
|`engineering.gear_torque_transmission`|기어쌍을 통과한 출력 토크 τ_out = τ_in·(피동 잇수/구동 잇수)·η 를 계산하고 기어비도 반환한다.|mpmath|
|`engineering.hardness_convert`|강재 경도를 HV, HB, HRC 사이에서 근사 환산한다.|mpmath|
|`engineering.hazen_williams_flow`|하젠-윌리엄스 식(SI)으로 관 유량 Q = 0.278·C·D^2.63·S^0.54 (m³/s)를 계산한다.|mpmath|
|`engineering.inductor_combine`|인덕터 여러 개의 합성 인덕턴스를 구한다.|mpmath|
|`engineering.lc_resonant_frequency`|LC 공진 주파수 f0=1/(2π√(LC))를 구한다.|mpmath|
|`engineering.lmtd`|열교환기 대수평균온도차 LMTD = (ΔT₁ − ΔT₂)/ln(ΔT₁/ΔT₂)를 계산한다.|mpmath|
|`engineering.max_power_transfer`|최대 전력 전달 정리로 최적 부하와 최대 전력을 구한다.|Decimal|
|`engineering.mech_strain`|선형 변형률 ε = ΔL / L (무차원)을 계산한다.|Decimal|
|`engineering.mech_stress`|수직응력 σ = F / A 를 계산한다.|Decimal|
|`engineering.moment_of_inertia`|표준 형상의 질량 관성모멘트 I (kg·m²)를 계산한다.|Decimal|
|`engineering.moody_friction_factor`|콜브룩 방정식을 반복 풀이해 다르시 마찰계수 f를 구한다.|mpmath|
|`engineering.norton_equivalent`|테브난 등가(V_th, R_th)를 노턴 등가로 변환한다.|Decimal|
|`engineering.opamp_gain`|이상적 연산증폭기의 폐루프 전압 이득을 구한다.|mpmath|
|`engineering.parallel_reliability`|병렬(중복) 시스템 신뢰도 R_sys = 1 − Π(1 − R_i)를 계산한다.|mpmath|
|`engineering.pid_discrete_output`|속도형(velocity form) 이산 PID의 새 출력 u_k=u_{k-1}+Δu를 구한다.|mpmath|
|`engineering.power_factor_correction`|지상(유도성) 부하의 역률을 목표 역률로 올리는 병렬 커패시턴스를 구한다.|mpmath|
|`engineering.pump_hydraulic_power`|펌프 수력 동력 P = ρ·g·Q·H (W)를 계산하고, efficiency(0 초과 1 이하)를 주면 축동력 P/η 도 반환한다.|mpmath|
|`engineering.rc_filter_cutoff`|1차 RC 필터의 -3 dB 차단 주파수 fc=1/(2πRC)를 Hz로 구한다.|mpmath|
|`engineering.resistor_color_code`|저항기 4밴드 또는 5밴드 컬러코드를 해독해 저항값(Ω)과 허용오차(%)를 구한다.|mpmath|
|`engineering.resistor_parallel`|병렬 연결 저항의 합성 저항 1/R_total=Σ(1/Rᵢ)를 구한다.|Decimal|
|`engineering.resistor_series`|직렬 연결 저항의 합성 저항 R_total=ΣRᵢ를 구한다.|Decimal|
|`engineering.rlc_time_constant`|RC, RL, 직렬 RLC 회로의 시정수 또는 감쇠 특성을 구한다.|mpmath|
|`engineering.safety_factor`|안전율 SF = 허용응력 / 작용응력을 계산한다.|mpmath|
|`engineering.second_order_response`|2차 시스템 G(s)=ωn²/(s²+2ζωn·s+ωn²)의 감쇠 고유진동수 ωd, 최대 오버슈트, 정착시간을 구한다.|mpmath|
|`engineering.section_moment_inertia`|도심 중립축에 대한 단면 이차모멘트 I 를 계산한다.|mpmath|
|`engineering.series_reliability`|직렬 시스템 신뢰도 R_sys = ΠR_i 를 계산한다.|mpmath|
|`engineering.shear_stress`|횡전단응력 τ 를 모드별로 계산한다.|mpmath|
|`engineering.si_prefix_convert`|수치를 SI 접두사 사이에서 환산한다.|Decimal|
|`engineering.sn_fatigue_life`|바스퀸 식으로 파손까지의 사이클 수 N_f를 구한다.|mpmath|
|`engineering.stefan_boltzmann`|회색체 표면과 주위 사이의 순복사 열전달 Q = ε·σ·A·(T_s⁴ − T_surr⁴) (W)를 계산한다.|mpmath|
|`engineering.thermal_expansion_strain`|선팽창 변형률 ε = α·ΔT 를 계산하고 length(0 초과)를 주면 길이 변화 ΔL = ε·L₀ 도 반환한다.|mpmath|
|`engineering.thermal_resistance`|열저항 K/W 를 합성한다.|mpmath|
|`engineering.thevenin_equivalent`|개방 전압과 단락 전류로 테브난 등가 회로를 구한다.|Decimal|
|`engineering.three_phase_power`|균형 3상 회로의 피상, 유효, 무효 전력을 선간 값으로 구한다.|mpmath|
|`engineering.torque_rotational_power`|회전 일률 P = τ·ω (W)를 계산한다.|Decimal|
|`engineering.weibull_reliability`|2모수 와이블 분포의 신뢰도 R(t) = exp(−(t/η)^β)와 불신뢰도를 계산한다.|mpmath|

엔진 열은 도구가 정의된 모듈이 쓰는 가장 거친 수치 엔진이다. Decimal은 정확, mpmath는 지정 자릿수(기본 50자리), float64는 배정밀도 근사다. 인자와 기본값은 `sootool tools describe <도구>`로 확인한다.

## 사용 시 주의

- 입력 단위는 SI 기본 단위다(V, A, Ω, H, F, Hz, m, kg, Pa, K 등). µF는 `"0.000001"`처럼 환산해 넣는다. 접두어 환산은 `engineering.si_prefix_convert`를 쓴다.
- `electrical_ohm`은 V, I, R 중 정확히 두 값을, `electrical_power`는 P, V, I, R 중 정확히 두 값을 받는다.
- `fluid_reynolds`의 유동 구분은 관 유동 관례(층류 < 2300 ≤ 천이 ≤ 4000 < 난류)를 따른다.
- `three_phase_power`, `power_factor_correction`은 정현파 평형 부하를 가정한다.
- `hardness_convert`는 근사식이다. 정밀한 환산은 ASTM E140 표를 쓴다.

호출 예시는 [전기 공학 쿡북](../../../../docs/cookbook/engineering_electrical.md)에 있다.
