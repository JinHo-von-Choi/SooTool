# 쿡북: 전기 회로 계산

교류 임피던스, RC 필터, 3상 전력, 데시벨, 저항 색 코드를 요청 문장, 도구 호출, 결과, 답변 예 순서로 정리한다. 결과 값은 SooTool 0.2.0에서 실제 실행한 값이다.

다른 쿡북: [한국 세금](tax_korea_2026.md) · [금융](finance_scenarios.md)

## 1. RLC 직렬 임피던스: engineering.ac_impedance

> "60 Hz 전원에 R=10 Ω, L=0.1 H, C=100 µF를 직렬로 연결하면 임피던스 크기와 위상각은?"

```json
{"tool": "engineering.ac_impedance",
 "args": {"frequency": "60", "resistance": "10", "inductance": "0.1", "capacitance": "0.0001", "topology": "series"}}
```

```json
{
  "magnitude": "14.9947445662283790155654688184",
  "phase_deg": "48.1717213118468626954562873704",
  "real": "10",
  "imag": "11.173287994428296233404426703945137024385901331662"
}
```

답변 예: |Z| = 14.99 Ω, 위상각 +48.17°다. ω = 2π·60 ≈ 376.99 rad/s에서 ωL ≈ 37.70 Ω, 1/(ωC) ≈ 26.53 Ω이라 순 리액턴스가 +11.17 Ω(유도성)이고, 전류가 전압보다 48.17° 늦다.

## 2. RLC 병렬 임피던스: 같은 도구, topology="parallel"

> "1 kHz에서 R=50 Ω, L=10 mH, C=0.1 µF를 병렬로 연결하면?"

```json
{"tool": "engineering.ac_impedance",
 "args": {"frequency": "1000", "resistance": "50", "inductance": "0.01", "capacitance": "0.0000001", "topology": "parallel"}}
```

```json
{"magnitude": "39.7245439193563430250777999444", "phase_deg": "37.3928057528897609353480518147"}
```

답변 예: |Z| = 39.72 Ω, 위상각 +37.39°다. 1 kHz는 공진 주파수(약 5.03 kHz)보다 낮아 병렬 회로에서는 인덕터 쪽 전류가 커지므로 유도성이다.

## 3. RC 저역통과 필터 차단 주파수: engineering.rc_filter_cutoff

> "1 kΩ 저항과 1 µF 커패시터로 만든 RC 저역통과 필터의 차단 주파수는?"

```json
{"tool": "engineering.rc_filter_cutoff",
 "args": {"resistance": "1000", "capacitance": "0.000001", "filter_type": "low_pass"}}
```

```json
{"cutoff_hz": "159.15494309189533576888376337248917785368459201003", "filter_type": "low_pass"}
```

답변 예: f_c = 1/(2π·R·C) ≈ 159.15 Hz다. 이 주파수에서 이득은 −3 dB, 위상은 −45°다. 이 도구는 1차 필터만 다룬다.

## 4. 3상 평형 전력: engineering.three_phase_power

> "Y결선, 선간전압 380 V, 선전류 20 A, 역률 0.85(지상)인 부하의 유효·무효·피상전력은?"

```json
{"tool": "engineering.three_phase_power",
 "args": {"line_voltage": "380", "line_current": "20", "power_factor": "0.85", "connection": "wye"}}
```

```json
{
  "apparent": "13163.58613752346743080859219547600",
  "real": "11189.0482168949473161873033661546000",
  "reactive": "6934.34928453997044545964003955"
}
```

답변 예: 피상전력 13,163.59 VA, 유효전력 11,189.05 W, 무효전력 6,934.35 var다. 역률을 1로 맞추려면 6,934 var만큼 진상 무효전력이 필요하며, 커패시터 용량은 `engineering.power_factor_correction`으로 구한다. 이 도구는 정현파 평형 부하를 가정한다.

## 5. 데시벨 변환: engineering.db_convert

> "전압비 10배는 몇 dB야? 1 mW는 몇 dBm이야?"

```json
{"tool": "core.batch",
 "args": {"items": [
   {"id": "v_ratio", "tool": "engineering.db_convert", "args": {"mode": "v_to_db",  "value": "10", "reference": "1"}},
   {"id": "dbm_1mw", "tool": "engineering.db_convert", "args": {"mode": "w_to_dbm", "value": "0.001"}}
 ]}}
```

|id|result|
|-|-|
|v_ratio|20.0000000000000000000000000000|
|dbm_1mw|0.0|

답변 예: 전압비 10배는 20 dB(전력비 100배와 같은 이득)이고, 1 mW는 0 dBm이다.

## 6. 저항 색 코드: engineering.resistor_color_code

> "4밴드 빨강-빨강-갈색-금색과 5밴드 갈색-검정-검정-빨강-갈색 저항의 값과 허용오차는?"

```json
{"tool": "core.batch",
 "args": {"items": [
   {"id": "band4", "tool": "engineering.resistor_color_code", "args": {"bands": ["red", "red", "brown", "gold"]}},
   {"id": "band5", "tool": "engineering.resistor_color_code", "args": {"bands": ["brown", "black", "black", "red", "brown"]}}
 ]}}
```

|id|resistance_ohm|tolerance_pct|
|-|-|-|
|band4|220|5|
|band5|10000|1|

답변 예: 4밴드는 220 Ω ±5%, 5밴드는 10 kΩ ±1%다.
