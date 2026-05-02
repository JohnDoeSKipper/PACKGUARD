"""Wire sweep model for resin-flow-induced bond wire deflection during molding.

Simplified Stokes-flow drag on a cylinder (Nguyen 1993):
  F_drag = 3π * η * v * L  (per unit length scaling)
  δ = F * L³ / (3 * E * I)   (cantilever beam deflection)

  where I = π d⁴ / 64  (second moment of area for circular wire)
        E = 80 GPa (gold wire); 110 GPa (copper wire)

Critical: δ > 0.10 * pitch → shorting risk.

References:
  Nguyen LT. "Reactive flow simulation in transfer molding of IC packages."
  Proc. 43rd ECTC, 1993, pp. 375-390.

  Tay AAO, Lin TY. "Moisture diffusion and heat transfer in plastic IC packages."
  IEEE Trans. Components Packag. Manuf. Technol., 19(2), 1996.

  IPC-7711/7721, "Rework, Modification, and Repair of Electronic Assemblies," IPC, 2017.
"""
from __future__ import annotations
import math
from scipy.stats import norm
from packguard_physics.types import ReliabilityResult

# Young's modulus per wire material (Pa)
_E_GOLD   = 80e9    # 80 GPa
_E_COPPER = 110e9   # 110 GPa


def predict_wire_sweep(
    wire_length_mm: float,
    wire_diameter_um: float,
    resin_viscosity_Pa_s: float,
    fill_velocity_m_per_s: float,
    wire_pitch_mm: float = 0.1,
    wire_material: str = "gold",
) -> ReliabilityResult:
    """Predict bond wire sweep deflection during transfer molding.

    Equation:
        F = 3π * η * v * L  [N/m drag per unit length, simplified Stokes]
        I = π * d⁴ / 64     [m⁴]
        δ = F * L³ / (3EI)  [m]

    P(fail) = norm CDF at δ with σ = 5% of pitch; failure if δ > 10% pitch.

    Args:
        wire_length_mm: Free wire span (mm).
        wire_diameter_um: Wire diameter (µm).
        resin_viscosity_Pa_s: Mold compound viscosity at fill temperature (Pa·s).
        fill_velocity_m_per_s: Resin flow front velocity (m/s).
        wire_pitch_mm: Center-to-center wire pitch (mm). Default 0.1 mm.
        wire_material: "gold" or "copper".

    Returns:
        ReliabilityResult with units="mm" (predicted deflection).

    Example:
        >>> r = predict_wire_sweep(2.0, 25, 10.0, 0.05)
        >>> 0 <= r.probability_of_failure <= 1
        True
    """
    if wire_length_mm <= 0:
        raise ValueError("wire_length_mm must be positive")
    if wire_diameter_um <= 0:
        raise ValueError("wire_diameter_um must be positive")
    if resin_viscosity_Pa_s <= 0:
        raise ValueError("resin_viscosity_Pa_s must be positive")
    if fill_velocity_m_per_s <= 0:
        raise ValueError("fill_velocity_m_per_s must be positive")
    if wire_material not in ("gold", "copper"):
        raise ValueError("wire_material must be 'gold' or 'copper'")

    E = _E_GOLD if wire_material == "gold" else _E_COPPER

    L = wire_length_mm * 1e-3        # m
    d = wire_diameter_um * 1e-6      # m
    I = math.pi * d**4 / 64.0       # m⁴

    # Oseen-Burgers distributed drag [N/m] on slender cylinder in viscous flow.
    # f = 4π * η * v / (ln(2L/d) - 0.5772)   (Oseen 1910; Burgers 1938)
    oseen_denom = math.log(2.0 * L / d) - 0.5772
    oseen_denom = max(oseen_denom, 1.0)  # guard against degenerate L/d
    f_per_m = 4.0 * math.pi * resin_viscosity_Pa_s * fill_velocity_m_per_s / oseen_denom
    # Cantilever deflection with distributed load: δ = f * L⁴ / (8EI)
    delta_m = f_per_m * L**4 / (8.0 * E * I)
    delta_mm = delta_m * 1e3

    # Failure criterion: δ > 10% of wire span (industry-standard sweep ratio)
    critical_mm = 0.10 * wire_length_mm
    sigma_mm = 0.02 * wire_length_mm  # ±2% of span process scatter

    p_fail = float(norm.cdf(delta_mm, loc=critical_mm, scale=sigma_mm))
    p_fail = max(0.0, min(1.0, p_fail))

    pf_low  = max(0.0, min(1.0, float(norm.cdf(delta_mm - 1.645 * sigma_mm,
                                                 loc=critical_mm, scale=sigma_mm))))
    pf_high = max(0.0, min(1.0, float(norm.cdf(delta_mm + 1.645 * sigma_mm,
                                                 loc=critical_mm, scale=sigma_mm))))

    return ReliabilityResult(
        probability_of_failure=p_fail,
        confidence_interval=(pf_low, pf_high),
        predicted_lifetime=delta_mm,
        units="mm",
        model_used="wire_sweep",
        assumptions=[
            f"Wire material: {wire_material}, E={E/1e9:.0f} GPa",
            "Oseen-Burgers distributed drag on slender cylinder (f = 4πηv / ln(2L/d))",
            "Cantilever Euler-Bernoulli deflection under distributed load",
            f"Failure criterion: δ > 10% of wire span = {critical_mm:.4f} mm",
        ],
        inputs={
            "wire_length_mm": wire_length_mm,
            "wire_diameter_um": wire_diameter_um,
            "resin_viscosity_Pa_s": resin_viscosity_Pa_s,
            "fill_velocity_m_per_s": fill_velocity_m_per_s,
            "wire_pitch_mm": wire_pitch_mm,
            "wire_material": wire_material,
            "predicted_deflection_mm": delta_mm,
            "critical_deflection_mm": critical_mm,
        },
        citations=[
            "Nguyen LT, 'Reactive flow simulation in transfer molding of IC packages,' "
            "Proc. 43rd ECTC, 1993, pp. 375-390.",
            "IPC-7711/7721, 'Rework, Modification, and Repair of Electronic Assemblies,' "
            "IPC, 2017.",
        ],
    )
