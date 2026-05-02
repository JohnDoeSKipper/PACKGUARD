"""Peck's model for humidity-driven corrosion and moisture failure.

Equation: TTF = A * RH^(-n) * exp(Ea / (k * T))

Constants (Peck 1986):
  n   = 2.7  (relative humidity exponent)
  Ea  = 0.79 eV  (activation energy)

References:
  Peck DS. "Comprehensive model for humidity testing correlation."
  Proc. 24th IEEE Int. Reliability Physics Symposium (IRPS), 1986, pp. 44-50.

  JEDEC JESD22-A101, "Steady-State Temperature-Humidity Bias Life Test,"
  JEDEC Solid State Technology Association, 2009.
"""
from __future__ import annotations
import math
from scipy.stats import lognorm
from packguard_physics.types import ReliabilityResult

_K_EV    = 8.617333e-5
_N_RH    = 2.7       # Peck 1986
_EA_EV   = 0.79      # Peck 1986
_SIGMA_LN = 0.5

# A calibrated so TTF = 1000 h at RH=85%, T=85°C (JEDEC 85/85 standard condition).
# TTF = A * 85^(-2.7) * exp(0.79/(k*358.15))
# exp(0.79/0.030862) = exp(25.60) ≈ 1.548e11
# 85^(-2.7) = 6.185e-6
# A * 6.185e-6 * 1.548e11 = A * 957.4 = 1000 → A = 1.045
_A = 1.045

# MSL-to-maximum-safe-exposure mapping (IPC/JEDEC J-STD-020E)
_MSL_SAFE_HOURS: dict[int, float] = {
    1: float("inf"),
    2: 8760.0,   # 1 year
    3: 168.0,    # 1 week
    4: 72.0,
    5: 48.0,
    6: 6.0,
}


def predict_humidity_failure(
    relative_humidity_pct: float,
    temperature_celsius: float,
    msl_rating: int,
    service_life_years: float = 5.0,
) -> ReliabilityResult:
    """Predict humidity-driven corrosion failure using Peck's model.

    Equation: TTF = A * RH^(-n) * exp(Ea / (k*T))
    P(fail) = lognormal CDF at service_life_hours with sigma=0.5.

    Args:
        relative_humidity_pct: Relative humidity (%). Must be 1–100.
        temperature_celsius: Operating temperature (°C).
        msl_rating: Moisture Sensitivity Level (1–6) per J-STD-020E.
        service_life_years: Service life in years.

    Returns:
        ReliabilityResult with units="hours".

    Example:
        >>> r = predict_humidity_failure(85, 85, 3, 5)
        >>> 0 <= r.probability_of_failure <= 1
        True
    """
    if not (1 <= relative_humidity_pct <= 100):
        raise ValueError("relative_humidity_pct must be between 1 and 100")
    if msl_rating not in _MSL_SAFE_HOURS:
        raise ValueError(f"msl_rating must be one of {list(_MSL_SAFE_HOURS)}")

    T_K = temperature_celsius + 273.15
    service_hours = service_life_years * 8760.0

    ttf = _A * (relative_humidity_pct ** (-_N_RH)) * math.exp(_EA_EV / (_K_EV * T_K))

    # MSL penalty: reduce effective TTF if part is used beyond its rated exposure
    msl_safe = _MSL_SAFE_HOURS[msl_rating]
    if msl_safe != float("inf") and service_hours > msl_safe:
        overshoot = service_hours / msl_safe
        ttf = ttf / overshoot  # proportional penalty for MSL violation

    p_fail = float(lognorm.cdf(service_hours, s=_SIGMA_LN, scale=ttf))
    p_fail = max(0.0, min(1.0, p_fail))

    ttf_low  = float(lognorm.ppf(0.05, s=_SIGMA_LN, scale=ttf))
    ttf_high = float(lognorm.ppf(0.95, s=_SIGMA_LN, scale=ttf))
    pf_low  = max(0.0, min(1.0, float(lognorm.cdf(service_hours, s=_SIGMA_LN, scale=ttf_high))))
    pf_high = max(0.0, min(1.0, float(lognorm.cdf(service_hours, s=_SIGMA_LN, scale=ttf_low))))

    return ReliabilityResult(
        probability_of_failure=p_fail,
        confidence_interval=(pf_low, pf_high),
        predicted_lifetime=ttf,
        units="hours",
        model_used="pecks_model",
        assumptions=[
            f"n={_N_RH}, Ea={_EA_EV} eV (Peck 1986)",
            "Lognormal scatter sigma=0.5",
            "Uniform RH and T throughout service life",
            f"MSL {msl_rating} safe exposure limit = {msl_safe} h (J-STD-020E)",
        ],
        inputs={
            "relative_humidity_pct": relative_humidity_pct,
            "temperature_celsius": temperature_celsius,
            "msl_rating": msl_rating,
            "service_life_years": service_life_years,
        },
        citations=[
            "Peck DS, 'Comprehensive model for humidity testing correlation,' "
            "Proc. 24th IEEE IRPS, 1986, pp. 44-50.",
            "IPC/JEDEC J-STD-020E, 'Moisture/Reflow Sensitivity Classification "
            "for Nonhermetic Packages,' 2014.",
        ],
    )
