# units module

Physical unit conversion, FX currency conversion, and temperature scale conversion.

## Tools

### units.convert

Convert a physical quantity between compatible units using pint.

- `magnitude` (str): Decimal string value
- `from_unit` (str): pint-recognized source unit (e.g. "meter", "kilogram", "liter")
- `to_unit` (str): pint-recognized target unit

Raises `InvalidInputError` for dimensionally incompatible units.

### units.fx_convert

Direct FX conversion: `result = amount * rate`, rounded to the target currency's minor units.

- `amount` (str): Source amount
- `from_ccy` (str): Source currency code (ISO 4217)
- `to_ccy` (str): Target currency code
- `rate` (str): Exchange rate from_ccy → to_ccy
- `rounding` (str): Rounding policy (default `"HALF_EVEN"`)

### units.fx_triangulate

Triangulated FX: `from_ccy → via_ccy → to_ccy` using two rates.

- `amount`, `from_ccy`, `via_ccy`, `to_ccy` (str)
- `rate1` (str): from_ccy → via_ccy
- `rate2` (str): via_ccy → to_ccy
- `rounding` (str): default `"HALF_EVEN"`

### units.temperature

Convert temperature between C, F, K, and R scales.

- `value` (str): Decimal string
- `from_scale` (str): `"C"` | `"F"` | `"K"` | `"R"`
- `to_scale` (str): same options

## Currency decimal rules (ISO 4217 minor units)

Final amounts are rounded to the number of decimal places defined by the
target currency's ISO 4217 minor unit count.

| Decimals | Currencies |
|-|-|
| 0 | JPY, KRW, CLP, ISK, UGX, VND, BIF, COP, DJF, GNF, KMF, MGA, PYG, RWF, VUV, XAF, XOF, XPF |
| 2 | USD, EUR, GBP, AUD, CNY, HKD, CAD, SGD, CHF, SEK, NOK, DKK, NZD, MXN, INR, BRL, RUB, ZAR, TRY, THB, IDR, MYR, PHP, EGP, PLN, CZK, HUF, RON, AED, SAR, QAR, PKR, NGN, UAH |
| 3 | BHD, KWD, OMR, TND, JOD, IQD, LYD |

Unknown currency codes fall back to 2 decimal places.

The full mapping lives in `currency.CURRENCY_DECIMALS`.
