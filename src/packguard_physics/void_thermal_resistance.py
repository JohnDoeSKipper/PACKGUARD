"""Void impact on die-attach thermal resistance.

Model: R_th_eff = R_th_nominal * (1 / (1 - void_fraction))^k
  k = 1.0 for dispersed voids
  k = 1.5 for clustered voids (worst-case; Zahn 2002)

Predicted junction temp T_j = T_ambient + P_diss * R_th_eff.
If T_j > T_j_max → P(fail) rises sharply.

References:
  Zahn BA. "Finite element based solder joint fatigue life predictions
  for a same die size stacked chip scale package."
  Proc. SEMI Int. Symposium, 2002.

  JEDEC JESD51-1, "Integrated Circuit Thermal Measurement Method —
  Electrical Test Method (Single Semiconductor Device)," JEDEC, 1995.

  Niwa H et al. "Void formation in solder joints."
  Proc. 37th ECTC, 1987.
"""
from __future__ import annotations
from scipy.stats import norm
from packguard_physics.types import ReliabilityResult

_K_DISPERSED = 1.0
_K_CLUSTERED = 1.5


def assess_void_impact(
    void_fraction: float,
    void_distribution: str = "dispersed",
    nominal_thermal_resistance_K_per_W: float = 1.0,
    max_junction_temp_C: float = 125.0,
    ambient_temp_C: float = 25.0,
    power_dissipation_W: float = 5.0,
) -> ReliabilityResult:
    """Assess thermal failure risk due to die-attach voids.

    Equation: R_th_eff = R_th_nominal / (1 - void_fraction)^k
    T_j = T_ambient + P * R_th_eff
    P(fail) derived from normal CDF centered at T_j_max with sigma=5°C.

    Args:
        void_fraction: Fractional void area (0 to 0.9). Values > 0.5 are extreme.
        void_distribution: "dispersed" (k=1.0) or "clustered" (k=1.5).
        nominal_thermal_resistance_K_per_W: R_th with zero voids (K/W).
        max_junction_temp_C: Maximum allowed junction temperature (°C).
        ambient_temp_C: Ambient temperature (°C).
        power_dissipation_W: Die power dissipation (W).

    Returns:
        ReliabilityResult with units="celsius" (predicted junction temperature).

    Example:
        >>> r = assess_void_impact(0.3)
        >>> 0 <= r.probability_of_failure <= 1
        True
    """
    if not (0.0 <= void_fraction < 1.0):
        raise ValueError("void_fraction must be in [0, 1)")
    if void_distribution not in ("dispersed", "clustered"):
        raise ValueError("void_distribution must be 'dispersed' or 'clustered'")

    k = _K_CLUSTERED if void_distribution == "clustered" else _K_DISPERSED
    r_eff = nominal_thermal_resistance_K_per_W / ((1.0 - void_fraction) ** k)
    t_junction = ambient_temp_C + power_dissipation_W * r_eff

    sigma_c = 5.0  # ±5°C measurement + process scatter
    p_fail = float(norm.cdf(t_junction, loc=max_junction_temp_C, scale=sigma_c))
    p_fail = max(0.0, min(1.0, p_fail))

    pf_low  = max(0.0, min(1.0, float(norm.cdf(t_junction - 1.645 * sigma_c,
                                                 loc=max_junction_temp_C, scale=sigma_c))))
    pf_high = max(0.0, min(1.0, float(norm.cdf(t_junction + 1.645 * sigma_c,
                                                 loc=max_junction_temp_C, scale=sigma_c))))

    return ReliabilityResult(
        probability_of_failure=p_fail,
        confidence_interval=(pf_low, pf_high),
        predicted_lifetime=t_junction,
        units="celsius",
        model_used="void_thermal_resistance",
        assumptions=[
            f"Void distribution: {void_distribution}, k={k} (Zahn 2002)",
            f"R_th model: R_eff = R_nom / (1 - f_void)^k",
            f"Failure criterion: T_j > {max_junction_temp_C}°C (JEDEC JESD51-1)",
            "Normal scatter sigma=5°C on T_j",
        ],
        inputs={
            "void_fraction": void_fraction,
            "void_distribution": void_distribution,
            "nominal_thermal_resistance_K_per_W": nominal_thermal_resistance_K_per_W,
            "max_junction_temp_C": max_junction_temp_C,
            "ambient_temp_C": ambient_temp_C,
            "power_dissipation_W": power_dissipation_W,
            "effective_R_th": r_eff,
            "predicted_T_j_C": t_junction,
        },
        citations=[
            "Zahn BA, 'Finite element based solder joint fatigue life predictions,' "
            "Proc. SEMI Int. Symposium, 2002.",
            "JEDEC JESD51-1, 'IC Thermal Measurement Method — Electrical Test Method,' 1995.",
        ],
    )
