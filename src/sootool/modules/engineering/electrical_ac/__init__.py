"""AC circuit tools (impedance, resonance, filters, networks, three-phase power, dB, color code, op-amp).

Importing this package registers every electrical_ac tool in REGISTRY.
"""
from __future__ import annotations

from sootool.modules.engineering.electrical_ac import (  # noqa: F401
    combine,
    impedance,
    power,
    signals,
)
from sootool.modules.engineering.electrical_ac._common import (  # noqa: F401
    _MP_DPS,
    _ONE,
    _OUT_DIG,
    _TWO,
    _ZERO,
    _atan2_deg_mp,
    _pi_dec,
    _sqrt_mp,
)
from sootool.modules.engineering.electrical_ac.combine import (  # noqa: F401
    capacitor_combine,
    inductor_combine,
)
from sootool.modules.engineering.electrical_ac.impedance import (  # noqa: F401
    ac_impedance,
    lc_resonant_frequency,
    rc_filter_cutoff,
    rlc_time_constant,
)
from sootool.modules.engineering.electrical_ac.power import (  # noqa: F401
    power_factor_correction,
    three_phase_power,
)
from sootool.modules.engineering.electrical_ac.signals import (  # noqa: F401
    db_convert,
    opamp_gain,
    resistor_color_code,
)
