# engineering module

Electrical engineering, fluid mechanics, and SI prefix conversion tools.

## Tools

### engineering.electrical_ohm

Ohm's law: V = I × R. Provide exactly 2 of {voltage, current, resistance}.

- `voltage` (str | None): Volts
- `current` (str | None): Amperes
- `resistance` (str | None): Ohms

### engineering.electrical_power

Power equations: P = VI = I²R = V²/R. Provide exactly 2 of {power, voltage, current, resistance}.

Supported equation pairs:
- V, I → P, R
- V, R → P, I
- I, R → P, V
- P, V → I, R
- P, I → V, R
- P, R → I=√(P/R), V=√(PR)

### engineering.resistor_series

Total resistance of resistors in series.

- `resistors` (list[str]): List of Decimal resistance values (all > 0)

Formula: R_total = R₁ + R₂ + … + Rₙ

### engineering.resistor_parallel

Total resistance of resistors in parallel.

- `resistors` (list[str]): List of Decimal resistance values (all > 0)

Formula: 1/R_total = 1/R₁ + 1/R₂ + … + 1/Rₙ

### engineering.fluid_reynolds

Reynolds number and flow regime classification.

- `density` (str): Fluid density ρ in kg/m³
- `velocity` (str): Flow velocity v in m/s
- `length` (str): Characteristic length L in m
- `viscosity` (str): Dynamic viscosity μ in Pa·s

Formula: Re = (ρ × v × L) / μ

Flow regimes (pipe flow convention):
- Re < 2300: laminar
- 2300 ≤ Re ≤ 4000: transitional
- Re > 4000: turbulent

### engineering.si_prefix_convert

Convert a value between SI prefix scales.

- `value` (str): Decimal string
- `from_prefix` (str): Source prefix name (e.g. "mega", "kilo", "milli")
- `to_prefix` (str): Target prefix name

Formula: result = value × 10^(from_exponent − to_exponent)

Supported prefixes (yocto to yotta):

| Prefix | Exponent |
|-|-|
| yocto | -24 |
| zepto | -21 |
| atto | -18 |
| femto | -15 |
| pico | -12 |
| nano | -9 |
| micro | -6 |
| milli | -3 |
| centi | -2 |
| deci | -1 |
| (base/"") | 0 |
| deca | 1 |
| hecto | 2 |
| kilo | 3 |
| mega | 6 |
| giga | 9 |
| tera | 12 |
| peta | 15 |
| exa | 18 |
| zetta | 21 |
| yotta | 24 |
