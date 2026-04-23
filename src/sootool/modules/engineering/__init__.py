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
  - engineering.beam_deflection             (cantilever/simply-supported δ_max)
  - engineering.bending_stress              (σ = M c / I)
  - engineering.shear_stress                (τ = V Q / (I b))
  - engineering.euler_buckling              (P_cr = π² E I / (K L)²)
  - engineering.section_moment_inertia      (rectangle/circle/I-beam I)
  - engineering.first_order_response        (1차 시스템 스텝 응답)
  - engineering.second_order_response       (2차 시스템 ωd/Mp/ts)
  - engineering.bode_magnitude_phase        (Bode 크기·위상)
  - engineering.pid_discrete_output         (이산 PID 속도형)
  - engineering.safety_factor               (SF = σ_allow / σ_applied)
  - engineering.thermal_expansion_strain    (ε = α ΔT)
  - engineering.sn_fatigue_life             (Basquin N_f)
  - engineering.hardness_convert            (HV↔HB↔HRC)
  - engineering.gear_ratio                  (i = N_driven / N_driver)
  - engineering.gear_torque_transmission    (τ_out = τ_in · i · η)
  - engineering.bearing_life_l10            (L10 = (C/P)^p)
  - engineering.bearing_equivalent_load     (P = X·Fr + Y·Fa)
  - engineering.thevenin_equivalent         (V_th, R_th)
  - engineering.norton_equivalent           (I_N, R_N)
  - engineering.max_power_transfer          (R_L = R_th, P_max)
  - engineering.exponential_reliability     (R(t) = exp(−λt); MTBF)
  - engineering.series_reliability          (R_sys = Π R_i)
  - engineering.parallel_reliability        (R_sys = 1 − Π(1 − R_i))
  - engineering.weibull_reliability         (R(t) = exp(−(t/η)^β))
"""
from __future__ import annotations

from sootool.modules.engineering import (
    control,
    electrical,
    electrical_ac,
    equivalent_circuit,
    fluid,
    gear_bearing,
    materials,
    mechanical,
    reliability,
    si_prefix,
    structural,
    thermal,
)

__all__ = [
    "control",
    "electrical",
    "electrical_ac",
    "equivalent_circuit",
    "fluid",
    "gear_bearing",
    "materials",
    "mechanical",
    "reliability",
    "si_prefix",
    "structural",
    "thermal",
]
