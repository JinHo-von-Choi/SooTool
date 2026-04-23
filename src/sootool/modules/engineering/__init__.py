"""Engineering domain module.

Importing this package registers all engineering tools in REGISTRY:
  - engineering.electrical_ohm              (Ohm's law)
  - engineering.electrical_power            (power equations P=VI=I²R=V²/R)
  - engineering.resistor_series             (series resistance)
  - engineering.resistor_parallel           (parallel resistance)
  - engineering.ac_impedance                (AC R/L/C series/parallel impedance)
  - engineering.rlc_time_constant           (RC/RL/RLC time constant)
  - engineering.lc_resonant_frequency       (LC resonant frequency)
  - engineering.rc_filter_cutoff            (RC filter cutoff frequency)
  - engineering.capacitor_combine           (capacitor series/parallel)
  - engineering.inductor_combine            (inductor series/parallel)
  - engineering.three_phase_power           (balanced 3-phase power)
  - engineering.power_factor_correction     (PF correction capacitance)
  - engineering.db_convert                  (dB/Np/dBm conversion)
  - engineering.resistor_color_code         (4/5-band color code)
  - engineering.opamp_gain                  (inverting / non-inverting gain)
  - engineering.mech_stress                 (σ = F/A)
  - engineering.mech_strain                 (ε = ΔL/L)
  - engineering.elastic_modulus_relate      (E, G, ν, K relations)
  - engineering.torque_rotational_power     (P = τω)
  - engineering.moment_of_inertia           (standard-shape I)
  - engineering.fluid_reynolds              (Reynolds number + regime)
  - engineering.bernoulli                   (Bernoulli equation solver)
  - engineering.darcy_weisbach              (head loss)
  - engineering.moody_friction_factor       (Colebrook iterative)
  - engineering.hazen_williams_flow         (pipe flow rate)
  - engineering.pump_hydraulic_power        (P = ρgQH)
  - engineering.fourier_heat_conduction     (Q = kA ΔT / L)
  - engineering.thermal_resistance          (series/parallel R_th)
  - engineering.stefan_boltzmann            (radiation)
  - engineering.lmtd                        (log-mean ΔT)
  - engineering.convective_heat_transfer    (Q = hAΔT)
  - engineering.si_prefix_convert           (SI prefix scale conversion)
"""
from __future__ import annotations

from sootool.modules.engineering import (
    electrical,
    electrical_ac,
    fluid,
    mechanical,
    si_prefix,
    thermal,
)

__all__ = [
    "electrical",
    "electrical_ac",
    "fluid",
    "mechanical",
    "si_prefix",
    "thermal",
]
