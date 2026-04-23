# 쿡북 — 전기 공학 시나리오 (AC·RC·3상·dB·컬러코드)

실행 버전: v0.1.x, 2026-04-24
작성자: 최진호

관련 문서: [README](../../README.md) · [architecture](../architecture.md) · [user_guide](../user_guide.md)
· 다른 쿡북: [tax_korea_2026](./tax_korea_2026.md) · [finance_scenarios](./finance_scenarios.md)

## 시나리오 요약

1. AC 임피던스 RLC 직렬 (engineering.ac_impedance)
2. AC 임피던스 RLC 병렬 (동 도구, topology="parallel")
3. RC 1차 저역통과 필터 차단 주파수 (engineering.rc_filter_cutoff)
4. 3상 균형 전력 (engineering.three_phase_power)
5. dB / dBm 변환 2 set (engineering.db_convert)
6. 저항기 컬러코드 4-band / 5-band 해독 (engineering.resistor_color_code)

모든 숫자는 `REGISTRY.invoke` 실제 호출 결과(master@587b763, 2026-04-24 기준)이다.
각 단계는 다음 4단 형식으로 기록한다.

1. LLM 프롬프트 원문
2. SooTool JSON 호출
3. 응답 trace 발췌
4. 사용자 보고서 인용

---

## 1. RLC 직렬 임피던스 (60 Hz)

### 1.1 LLM 프롬프트 원문

> "60 Hz 전원에서 R=10 Ω, L=0.1 H, C=100 µF 를 직렬로 연결하면 임피던스 크기
> |Z|와 위상각은 얼마야?"

### 1.2 SooTool JSON 호출

```json
{
  "tool": "engineering.ac_impedance",
  "args": {
    "frequency":   "60",
    "resistance":  "10",
    "inductance":  "0.1",
    "capacitance": "0.0001",
    "topology":    "series"
  }
}
```

### 1.3 응답 trace 발췌

```json
{
  "magnitude": "14.9947445662283790155654688184",
  "phase_deg": "48.1717213118468626954562873704",
  "real":      "10",
  "imag":      "11.17...",
  "trace": {
    "tool": "engineering.ac_impedance",
    "formula": "Z = R + j(ωL - 1/(ωC)) (series); Y = 1/R + 1/(jωL) + jωC (parallel)",
    "steps": [
      {"label": "omega",     "value": "376.99..."},
      {"label": "z_real",    "value": "10"},
      {"label": "z_imag",    "value": "11.17..."},
      {"label": "magnitude", "value": "14.9947..."},
      {"label": "phase_deg", "value": "48.17..."}
    ]
  }
}
```

### 1.4 사용자 보고서 인용

> |Z| = 14.99 Ω, 위상 +48.17° (유도성 우세). ω = 2π·60 ≈ 376.99 rad/s,
> ωL ≈ 37.70 Ω, 1/(ωC) ≈ 26.53 Ω 로 순 리액턴스는 +11.17 Ω.
> 부하는 전류가 전압보다 48.17° 뒤처지는 유도성 특성을 보인다.

---

## 2. RLC 병렬 임피던스 (1 kHz)

### 2.1 LLM 프롬프트 원문

> "1 kHz 에서 R=50 Ω, L=10 mH, C=0.1 µF 를 병렬로 연결한 경우 임피던스는?"

### 2.2 SooTool JSON 호출

```json
{
  "tool": "engineering.ac_impedance",
  "args": {
    "frequency":   "1000",
    "resistance":  "50",
    "inductance":  "0.01",
    "capacitance": "0.0000001",
    "topology":    "parallel"
  }
}
```

### 2.3 응답 trace 발췌

```json
{
  "magnitude": "39.7245439193563430250777999444",
  "phase_deg": "37.3928057528897609353480518147"
}
```

### 2.4 사용자 보고서 인용

> 병렬 |Z| = 39.72 Ω, 위상 +37.39°. 공진점 부근(f₀ = 1/(2π√(LC)) ≈ 5.03 kHz)
> 과 차이가 있으므로 용량성·유도성 경쟁 상태이며 전류 벡터는 전압보다 37.39°
> 뒤진다.

---

## 3. RC 1차 저역통과 필터 (engineering.rc_filter_cutoff)

### 3.1 LLM 프롬프트 원문

> "1 kΩ 저항과 1 µF 콘덴서로 만든 RC 저역통과 필터의 차단 주파수 f_c 는?"

### 3.2 SooTool JSON 호출

```json
{
  "tool": "engineering.rc_filter_cutoff",
  "args": {
    "resistance":  "1000",
    "capacitance": "0.000001",
    "filter_type": "low_pass"
  }
}
```

### 3.3 응답 trace 발췌

```json
{
  "cutoff_hz":   "159.15494309189533576888376337248917785368459201003",
  "filter_type": "low_pass",
  "trace": {
    "tool":    "engineering.rc_filter_cutoff",
    "formula": "fc = 1 / (2π R C)",
    "steps":   [{"label": "cutoff", "value": "159.1549..."}]
  }
}
```

### 3.4 사용자 보고서 인용

> f_c = 1/(2π·R·C) = 1/(2π·1000·10⁻⁶) ≈ 159.155 Hz. 가청대역 기준으로 저음
> 이외를 감쇠하는 초저역 필터이며, −3 dB 지점에서 위상은 −45° 를 가진다.

---

## 4. 3상 균형 전력 (engineering.three_phase_power)

### 4.1 LLM 프롬프트 원문

> "Y결선, 선간전압 380 V, 선전류 20 A, 역률 0.85 (지상)인 부하의 유효전력 P,
> 무효전력 Q, 피상전력 S 를 구해 줘."

### 4.2 SooTool JSON 호출

```json
{
  "tool": "engineering.three_phase_power",
  "args": {
    "line_voltage": "380",
    "line_current": "20",
    "power_factor": "0.85",
    "connection":   "wye"
  }
}
```

### 4.3 응답 trace 발췌

```json
{
  "apparent": "13163.58613752346743080859219547600",
  "real":     "11189.0482168949473161873033661546000",
  "reactive": "6934.34928453997044545964003955",
  "trace": {
    "tool": "engineering.three_phase_power",
    "formula": "S = √3 V_LL I_L; P = S cosφ; Q = √(S² − P²)"
  }
}
```

### 4.4 사용자 보고서 인용

> S ≈ 13,163.59 VA, P ≈ 11,189.05 W, Q ≈ 6,934.35 VAR. 역률 개선을 위해
> 병렬 커패시터를 추가할 경우 Q_c ≈ 6,934 VAR 를 상쇄해야 하며
> `engineering.power_factor_correction` 도구로 용량 C 를 직접 산출할 수 있다.

---

## 5. dB / dBm 변환 (engineering.db_convert)

### 5.1 LLM 프롬프트 원문

> "전압비 10 배는 몇 dB야? 그리고 1 mW 를 dBm 단위로 알려줘."

### 5.2 SooTool JSON 호출 (core.batch 로 2 set)

```json
{
  "tool": "core.batch",
  "args": {
    "deterministic": true,
    "items": [
      {"id": "v_ratio", "tool": "engineering.db_convert",
       "args": {"mode": "v_to_db", "value": "10", "reference": "1"}},
      {"id": "dbm_1mw", "tool": "engineering.db_convert",
       "args": {"mode": "w_to_dbm", "value": "0.001"}}
    ]
  }
}
```

### 5.3 응답 trace 발췌

```json
{
  "result": "20.0000000000000000000000000000",
  "trace": {
    "tool": "engineering.db_convert",
    "formula": "dB = 20 log10(V/V_ref)",
    "inputs":  {"mode": "v_to_db", "value": "10", "reference": "1"},
    "steps":   [{"label": "result", "value": "20.0000..."}]
  }
}
```

```json
{
  "result": "0.0",
  "trace": {
    "tool": "engineering.db_convert",
    "formula": "dBm = 10 log10(P_W / 1 mW)",
    "inputs":  {"mode": "w_to_dbm", "value": "0.001", "reference": "1"}
  }
}
```

### 5.4 사용자 보고서 인용

> 전압비 10배 = 20 dB (전력비 100 배와 동일한 게인 레벨), 1 mW = 0 dBm
> (기준 기준점). 이는 RF 측정 / 오디오 아날로그 설계에서 레벨 다이어그램의
> 핵심 앵커로 쓰인다.

---

## 6. 저항기 컬러코드 해독 (engineering.resistor_color_code)

### 6.1 LLM 프롬프트 원문

> "4밴드 저항 (빨강-빨강-갈색-금색)과 5밴드 저항 (갈색-검정-검정-빨강-갈색)
> 의 저항값과 허용오차를 알려줘."

### 6.2 SooTool JSON 호출 (core.batch)

```json
{
  "tool": "core.batch",
  "args": {
    "deterministic": true,
    "items": [
      {"id": "band4", "tool": "engineering.resistor_color_code",
       "args": {"bands": ["red", "red", "brown", "gold"]}},
      {"id": "band5", "tool": "engineering.resistor_color_code",
       "args": {"bands": ["brown", "black", "black", "red", "brown"]}}
    ]
  }
}
```

### 6.3 응답 trace 발췌

```json
{
  "resistance_ohm": "220",
  "tolerance_pct":  "5",
  "trace": {
    "tool":    "engineering.resistor_color_code",
    "formula": "R = (digits × 10^multiplier_index) ± tolerance%",
    "steps":   [
      {"label": "digits",     "value": "22"},
      {"label": "multiplier", "value": "10"},
      {"label": "tolerance",  "value": "5"},
      {"label": "resistance", "value": "220"}
    ]
  }
}
```

```json
{
  "resistance_ohm": "10000",
  "tolerance_pct":  "1"
}
```

### 6.4 사용자 보고서 인용

> 4밴드 red-red-brown-gold 는 220 Ω ± 5%. 5밴드 brown-black-black-red-brown 은
> 10 kΩ ± 1%. 허용오차 1% 표준 저항이므로 정밀도가 요구되는 기준전압 분배·
> 피드백 네트워크에 사용 가능하다.

---

## 체인 예시

1~6 단계를 `core.pipeline` 하나에 묶으면 "AC 부하 분석 → 필터 설계 → 계측 레벨
환산 → BOM 저항 선정" 의 단일 계산 문서를 결정론적으로 생성할 수 있다. 각
단계는 입력이 독립적이므로 `core.batch` 병렬 처리도 가능하며, 단계별 `trace`
는 계산 근거를 그대로 보존한다.

## 한계와 확장

- 현 `rc_filter_cutoff` 는 1차 필터만 지원한다. 2차·다단 필터는 `ac_impedance`
  체인으로 |H(jω)| 을 수동 계산해야 한다.
- Decimal 기반 trigonometric 은 `_atan2_deg_mp` (mpmath) 로 내부 구현. 매우
  작은 L·C (< 1e−12) 에서는 정밀도 손실이 발생할 수 있으며, 이 경우 `mpmath`
  workdps 를 크게 설정해 호출하도록 내부에서 조정한다.
- 불평형 3상, 비정현파 전력은 범위 외. 현재 도구는 정현파 균형 부하 가정을
  사용한다.
