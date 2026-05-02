"""Package warpage prediction using bimetallic-strip / Stoney's equation analogy.

Equation (modified Stoney for bilayer):
  δ = (3 * (α_die - α_sub) * ΔT * L²) / (2 * t_pkg)

where:
  α_die, α_sub = CTE of die and substrate (ppm/°C)
  ΔT = peak reflow temp − room temp (°C)
  L  = package diagonal or side length (mm)
  t_pkg = package thickness (mm)

JEDEC warpage spec: ≤ 8 mils = 0.2032 mm for BGA packages (JEDEC JESD22-B112A).

References:
  Stoney GG. "The tension of metallic films deposited by electrolysis."
  Proc. R. Soc. Lond. A, 82, 1909, pp. 172-175.

  JEDEC JESD22-B112A, "Package Warpage Measurement of Surface Mount
  Integrated Circuits at Elevated Temperature," JEDEC, 2009.

  Liu Y, Irving S, Luk T. "Thermomechanical modeling of solder joint
  reliability for flip chip BGA packages." Microelectronics Reliability,
  44, 2004, pp. 189-196.
"""
from __future__ import annotations
from scipy.stats import norm
from packguard_physics.types import ReliabilityResult

_JEDEC_WARPAGE_LIMIT_MM = 0.2032  # 8 mils in mm (JESD22-B112A)


def predict_warpage(
    die_cte_ppm_per_C: float,
    substrate_cte_ppm_per_C: float,
    package_size_mm: float,
    peak_reflow_temp_C: float,
    room_temp_C: float = 25.0,
    package_thickness_mm: float = 1.0,
) -> ReliabilityResult:
    """Predict package warpage and BGA solder-joint stress risk.

    Equation: δ = 3 * ΔCTE * ΔT * L² / (2 * t_pkg)

    P(fail) via normal CDF at warpage relative to JEDEC 8-mil spec.

    Args:
        die_cte_ppm_per_C: CTE of die material (ppm/°C). Silicon ≈ 2.6.
        substrate_cte_ppm_per_C: CTE of substrate (ppm/°C). FR4 ≈ 18; BT ≈ 15.
        package_size_mm: Package side length or diagonal (mm).
        peak_reflow_temp_C: Peak reflow temperature (°C). Lead-free SAC ≈ 260°C.
        room_temp_C: Reference temperature (°C). Default 25°C.
        package_thickness_mm: Total package thickness (mm).

    Returns:
        ReliabilityResult with units="mm" (predicted warpage).

    Example:
        >>> r = predict_warpage(2.6, 18, 25, 260)
        >>> r.predicted_lifetime > 0
        True
    """
    if package_size_mm <= 0:
        raise ValueError("package_size_mm must be positive")
    if package_thickness_mm <= 0:
        raise ValueError("package_thickness_mm must be positive")

    delta_cte = abs(die_cte_ppm_per_C - substrate_cte_ppm_per_C) * 1e-6  # /°C
    delta_T = peak_reflow_temp_C - room_temp_C

    # Stoney-analogous bilayer formula: δ in mm (same units as L and t)
    warpage_mm = (3.0 * delta_cte * delta_T * package_size_mm**2) / (2.0 * package_thickness_mm)

    sigma_mm = 0.03  # ±0.03 mm measurement scatter (shadow moiré typical)
    p_fail = float(norm.cdf(warpage_mm, loc=_JEDEC_WARPAGE_LIMIT_MM, scale=sigma_mm))
    p_fail = max(0.0, min(1.0, p_fail))

    pf_low  = max(0.0, min(1.0, float(norm.cdf(warpage_mm - 1.645 * sigma_mm,
                                                 loc=_JEDEC_WARPAGE_LIMIT_MM, scale=sigma_mm))))
    pf_high = max(0.0, min(1.0, float(norm.cdf(warpage_mm + 1.645 * sigma_mm,
                                                 loc=_JEDEC_WARPAGE_LIMIT_MM, scale=sigma_mm))))

    return ReliabilityResult(
        probability_of_failure=p_fail,
        confidence_interval=(pf_low, pf_high),
        predicted_lifetime=warpage_mm,
        units="mm",
        model_used="warpage",
        assumptions=[
            "Stoney bilayer analogy; uniform CTE mismatch across package",
            f"JEDEC warpage limit = {_JEDEC_WARPAGE_LIMIT_MM:.4f} mm (8 mils, JESD22-B112A)",
            "Shadow moiré measurement uncertainty ≈ ±0.03 mm",
            "Package modeled as free plate with no constraining underfill",
        ],
        inputs={
            "die_cte_ppm_per_C": die_cte_ppm_per_C,
            "substrate_cte_ppm_per_C": substrate_cte_ppm_per_C,
            "package_size_mm": package_size_mm,
            "peak_reflow_temp_C": peak_reflow_temp_C,
            "room_temp_C": room_temp_C,
            "package_thickness_mm": package_thickness_mm,
            "predicted_warpage_mm": warpage_mm,
        },
        citations=[
            "Stoney GG, 'The tension of metallic films deposited by electrolysis,' "
            "Proc. R. Soc. Lond. A, 82, 1909, pp. 172-175.",
            "JEDEC JESD22-B112A, 'Package Warpage Measurement of Surface Mount ICs,' 2009.",
            "Liu Y et al., 'Thermomechanical modeling of solder joint reliability,' "
            "Microelectronics Reliability, 44, 2004, pp. 189-196.",
        ],
    )
