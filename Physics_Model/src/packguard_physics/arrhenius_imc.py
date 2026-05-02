"""Arrhenius IMC (intermetallic compound) growth model for wire bonds.

Equation: x(t) = sqrt(D0 * exp(-Ea / (k*T)) * t)

Constants:
  Au-Al: D0 = 4.0e-4 cm²/s, Ea = 1.0 eV  (Philofsky 1970; Footner & Richards 1982)
  Cu-Al: D0 = 1.0e-4 cm²/s, Ea = 0.9 eV  (Noolu et al. 2004)
  Au-Au: D0 = 1.0e-5 cm²/s, Ea = 1.2 eV  (Harman 1997)

Critical thickness: 5 µm → brittle joint / cratering risk.

References:
  Philofsky E. "Intermetallic formation in gold-aluminum systems."
  Solid-State Electronics, vol. 13, 1970, pp. 1391-1399.

  Footner PK, Richards BP. "Long-term growth of gold-aluminium intermetallics
  in IC devices." J. Mat. Sci., 17, 1982, pp. 2141-2153.

  Noolu NJ et al. "Intermetallic compound formation in Ag and Au ball bonds
  on Al metallization." Mat. Res. Soc. Proc. vol. 795, 2004.

  Harman G. "Wire Bonding in Microelectronics." McGraw-Hill, 2nd ed., 1997.
"""
from __future__ import annotations
import math
from scipy.stats import norm
from packguard_physics.types import ReliabilityResult

_K_EV = 8.617333e-5
_CRITICAL_THICKNESS_UM = 5.0   # µm — Philofsky 1970

# (D0 in cm²/s, Ea in eV)
_METALLURGY_PARAMS: dict[str, tuple[float, float]] = {
    "Au-Al": (4.0e-4, 1.0),
    "Cu-Al": (1.0e-4, 0.9),
    "Au-Au": (1.0e-5, 1.2),
}

_CM_TO_UM = 1e4  # 1 cm = 1e4 µm


def predict_imc_thickness(
    temperature_history_celsius: list[float],
    time_at_temperature_hours: list[float],
    wire_pad_metallurgy: str = "Au-Al",
) -> ReliabilityResult:
    """Predict IMC thickness growth and brittle-joint risk using Arrhenius diffusion.

    Equation: x_i = sqrt(D0 * exp(-Ea/(k*T_i)) * t_i) [in µm]
    Total effective thickness: x_total = sqrt(sum(D_eff_i * t_i)) * unit_conv

    P(fail) based on normal CDF centered at x_total with sigma = 20% of critical thickness.

    Args:
        temperature_history_celsius: List of temperature stages (°C).
        time_at_temperature_hours:   List of dwell times at each stage (hours).
        wire_pad_metallurgy: One of "Au-Al", "Cu-Al", "Au-Au".

    Returns:
        ReliabilityResult with units="micrometers" (predicted IMC thickness).

    Example:
        >>> r = predict_imc_thickness([150, 200], [100, 50], "Au-Al")
        >>> r.predicted_lifetime > 0
        True
    """
    if len(temperature_history_celsius) != len(time_at_temperature_hours):
        raise ValueError("temperature_history and time_at_temperature must have equal length")
    if not temperature_history_celsius:
        raise ValueError("At least one temperature stage required")
    if wire_pad_metallurgy not in _METALLURGY_PARAMS:
        raise ValueError(f"Unknown metallurgy '{wire_pad_metallurgy}'. Choose from {list(_METALLURGY_PARAMS)}")

    D0, Ea = _METALLURGY_PARAMS[wire_pad_metallurgy]

    # Parabolic growth law: x² = D_eff * t → sum contributions
    sum_Dt = 0.0
    for T_c, t_h in zip(temperature_history_celsius, time_at_temperature_hours):
        T_K = T_c + 273.15
        t_s = t_h * 3600.0
        D_eff = D0 * math.exp(-Ea / (_K_EV * T_K))
        sum_Dt += D_eff * t_s

    thickness_cm = math.sqrt(sum_Dt)
    thickness_um = thickness_cm * _CM_TO_UM

    # Sigma = 20% of critical thickness (process variability)
    sigma_um = 0.20 * _CRITICAL_THICKNESS_UM
    p_fail = float(norm.cdf(thickness_um, loc=_CRITICAL_THICKNESS_UM, scale=sigma_um))
    p_fail = max(0.0, min(1.0, p_fail))

    # 90% CI
    pf_low  = max(0.0, min(1.0, float(norm.cdf(thickness_um - 1.645 * sigma_um,
                                                  loc=_CRITICAL_THICKNESS_UM, scale=sigma_um))))
    pf_high = max(0.0, min(1.0, float(norm.cdf(thickness_um + 1.645 * sigma_um,
                                                  loc=_CRITICAL_THICKNESS_UM, scale=sigma_um))))

    return ReliabilityResult(
        probability_of_failure=p_fail,
        confidence_interval=(pf_low, pf_high),
        predicted_lifetime=thickness_um,
        units="micrometers",
        model_used="arrhenius_imc",
        assumptions=[
            f"Metallurgy: {wire_pad_metallurgy}, D0={D0} cm²/s, Ea={Ea} eV",
            f"Critical brittle thickness = {_CRITICAL_THICKNESS_UM} µm (Philofsky 1970)",
            "Parabolic growth law assumed (diffusion-controlled regime)",
            "P(fail) modeled as normal CDF; sigma = 20% of critical thickness",
        ],
        inputs={
            "temperature_history_celsius": temperature_history_celsius,
            "time_at_temperature_hours": time_at_temperature_hours,
            "wire_pad_metallurgy": wire_pad_metallurgy,
            "predicted_imc_thickness_um": thickness_um,
        },
        citations=[
            "Philofsky E, 'Intermetallic formation in gold-aluminum systems,' "
            "Solid-State Electronics, 13, 1970, pp. 1391-1399.",
            "Footner PK, Richards BP, 'Long-term growth of gold-aluminium intermetallics,' "
            "J. Mat. Sci. 17, 1982, pp. 2141-2153.",
            "Harman G, 'Wire Bonding in Microelectronics,' McGraw-Hill, 2nd ed., 1997.",
        ],
    )
