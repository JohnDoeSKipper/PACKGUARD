"""Griffith fracture mechanics model for crack criticality assessment.

Equation: a_c = (1/π) * (K_Ic / σ)²

If actual crack length a >= a_c → imminent fracture.
Remaining margin → P(fail) via normal CDF.

Constants:
  Silicon K_Ic ≈ 0.83 MPa·√m  (Lawn & Wilshaw 1975; Chen & Leipold 1980)
  Al₂O₃   K_Ic ≈ 3.5 MPa·√m  (Evans 1972)
  SiN      K_Ic ≈ 6.0 MPa·√m  (Casellas et al. 2003)

References:
  Griffith AA. "The phenomena of rupture and flow in solids."
  Phil. Trans. R. Soc. Lond. A, 221, 1921, pp. 163-198.

  Lawn BR, Wilshaw TR. "Fracture of Brittle Solids." Cambridge Univ. Press, 1975.

  Chen CP, Leipold MH. "Fracture toughness of silicon."
  Am. Ceram. Soc. Bull. 59(4), 1980, pp. 469-472.
"""
from __future__ import annotations
import math
from scipy.stats import norm
from packguard_physics.types import ReliabilityResult

_MATERIAL_KIC: dict[str, float] = {
    "silicon": 0.83,   # MPa·√m  (Chen & Leipold 1980)
    "Al2O3":   3.5,    # MPa·√m  (Evans 1972)
    "SiN":     6.0,    # MPa·√m  (Casellas et al. 2003)
}

_MM_TO_M = 1e-3


def assess_crack_growth(
    crack_length_mm: float,
    applied_stress_MPa: float,
    fracture_toughness_MPa_sqrt_m: float = 0.83,
    material: str = "silicon",
) -> ReliabilityResult:
    """Assess fracture risk using the Griffith critical crack length criterion.

    Equation: a_c = (1/π) * (K_Ic / σ)²
    If a >= a_c → P(fail) = 1.0.
    Otherwise P(fail) via normal CDF on (a / a_c) ratio.

    Args:
        crack_length_mm: Observed crack half-length (mm).
        applied_stress_MPa: Applied tensile stress (MPa).
        fracture_toughness_MPa_sqrt_m: K_Ic of material (MPa·√m). Defaults to silicon.
        material: Material name for assumption reporting (str).

    Returns:
        ReliabilityResult with units="mm" (predicted critical crack length).

    Example:
        >>> r = assess_crack_growth(0.5, 50)
        >>> 0 <= r.probability_of_failure <= 1
        True
    """
    if crack_length_mm < 0:
        raise ValueError("crack_length_mm must be >= 0")
    if applied_stress_MPa <= 0:
        raise ValueError("applied_stress_MPa must be positive")
    if fracture_toughness_MPa_sqrt_m <= 0:
        raise ValueError("fracture_toughness_MPa_sqrt_m must be positive")

    # a_c in metres, convert to mm
    a_c_m = (1.0 / math.pi) * (fracture_toughness_MPa_sqrt_m / applied_stress_MPa) ** 2
    a_c_mm = a_c_m * 1e3

    if crack_length_mm == 0.0:
        p_fail = 0.0
        pf_low, pf_high = 0.0, 0.0
    elif crack_length_mm >= a_c_mm:
        p_fail = 1.0
        pf_low, pf_high = 1.0, 1.0
    else:
        # Ratio a/a_c; sigma = 15% of a_c (scatter in crack size measurement)
        sigma_mm = 0.15 * a_c_mm
        ratio = crack_length_mm / a_c_mm
        p_fail = float(norm.cdf(ratio, loc=1.0, scale=sigma_mm / a_c_mm))
        p_fail = max(0.0, min(1.0, p_fail))
        pf_low  = max(0.0, min(1.0, float(norm.cdf(ratio - 1.645 * sigma_mm / a_c_mm,
                                                     loc=1.0, scale=sigma_mm / a_c_mm))))
        pf_high = max(0.0, min(1.0, float(norm.cdf(ratio + 1.645 * sigma_mm / a_c_mm,
                                                     loc=1.0, scale=sigma_mm / a_c_mm))))

    return ReliabilityResult(
        probability_of_failure=p_fail,
        confidence_interval=(pf_low, pf_high),
        predicted_lifetime=a_c_mm,
        units="mm",
        model_used="griffith_fracture",
        assumptions=[
            f"Material: {material}, K_Ic = {fracture_toughness_MPa_sqrt_m} MPa·√m",
            "Plane-strain, mode-I loading assumed",
            "Semi-elliptical surface crack geometry (edge-crack factor = 1)",
            "15% scatter on crack size measurement",
        ],
        inputs={
            "crack_length_mm": crack_length_mm,
            "applied_stress_MPa": applied_stress_MPa,
            "fracture_toughness_MPa_sqrt_m": fracture_toughness_MPa_sqrt_m,
            "material": material,
            "critical_crack_length_mm": a_c_mm,
        },
        citations=[
            "Griffith AA, 'The phenomena of rupture and flow in solids,' "
            "Phil. Trans. R. Soc. Lond. A, 221, 1921, pp. 163-198.",
            "Chen CP, Leipold MH, 'Fracture toughness of silicon,' "
            "Am. Ceram. Soc. Bull. 59(4), 1980, pp. 469-472.",
            "Lawn BR, Wilshaw TR, 'Fracture of Brittle Solids,' Cambridge Univ. Press, 1975.",
        ],
    )
