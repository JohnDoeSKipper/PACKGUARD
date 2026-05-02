"""Black's equation electromigration model for metal interconnects.

Equation: MTTF = A * J^(-n) * exp(Ea / (k * T))

Constants (per Black 1969; Lloyd 1991):
  Cu:  n=2.0, Ea=0.9 eV  (Lloyd JR, J. Appl. Phys. 69, 1991)
  Al:  n=2.0, Ea=0.6 eV  (Black JR, IEEE Trans. Electron Devices, 1969)

References:
  Black JR. "Electromigration — a brief survey and some recent results."
  IEEE Trans. Electron Devices, vol. 16, no. 4, pp. 338-347, 1969.

  Lloyd JR. "Electromigration failure." J. Appl. Phys. 69(11), 1991.

  JEDEC JEP139, "Procedure for Characterizing Time-Dependent Dielectric
  Breakdown of Ultra-Thin Gate Dielectrics", JEDEC, 2001.
"""
from __future__ import annotations
import math
from scipy.stats import lognorm
from packguard_physics.types import ReliabilityResult

_K_EV = 8.617333e-5      # Boltzmann constant in eV/K
_SIGMA_LN = 0.4          # lognormal scatter for EM (Lloyd 1991)

# (A_scaling, n_exponent, Ea_eV)
# Calibrated so Cu MTTF ≈ 1000 h at J=1e6 A/cm², T=100°C (Black 1969; Lloyd 1991).
# Cu: A = 674 → MTTF ≈ 1000 h at reference conditions.
# Al: A = 1.5e6 → MTTF ≈ 193 h at same conditions (Al is less resistant than Cu).
_MATERIAL_PARAMS: dict[str, tuple[float, float, float]] = {
    "Cu": (674.0,  2.0, 0.9),
    "Al": (1.5e6,  2.0, 0.6),
}


def predict_electromigration(
    current_density_A_per_cm2: float,
    temperature_celsius: float,
    conductor_material: str = "Cu",
    service_life_years: float = 7.0,
) -> ReliabilityResult:
    """Predict electromigration-induced failure using Black's equation.

    Equation: MTTF = A * J^(-n) * exp(Ea / (k*T))
    P(fail) = lognormal CDF at service_life_hours with sigma=0.4.

    Args:
        current_density_A_per_cm2: Current density (A/cm²). Typical range 1e4–1e7.
        temperature_celsius: Operating temperature (°C).
        conductor_material: "Cu" or "Al".
        service_life_years: Intended service life in years.

    Returns:
        ReliabilityResult with units="hours".

    Example:
        >>> r = predict_electromigration(1e6, 100, "Cu", 7)
        >>> 0 < r.probability_of_failure < 1
        True
    """
    if current_density_A_per_cm2 <= 0:
        raise ValueError("current_density_A_per_cm2 must be positive")
    if conductor_material not in _MATERIAL_PARAMS:
        raise ValueError(f"Unknown material '{conductor_material}'. Choose from {list(_MATERIAL_PARAMS)}")

    A, n, Ea = _MATERIAL_PARAMS[conductor_material]
    T_K = temperature_celsius + 273.15
    service_hours = service_life_years * 8760.0

    mttf = A * (current_density_A_per_cm2 ** (-n)) * math.exp(Ea / (_K_EV * T_K))

    p_fail = float(lognorm.cdf(service_hours, s=_SIGMA_LN, scale=mttf))
    p_fail = max(0.0, min(1.0, p_fail))

    mttf_low  = float(lognorm.ppf(0.05, s=_SIGMA_LN, scale=mttf))
    mttf_high = float(lognorm.ppf(0.95, s=_SIGMA_LN, scale=mttf))
    pf_low  = max(0.0, min(1.0, float(lognorm.cdf(service_hours, s=_SIGMA_LN, scale=mttf_high))))
    pf_high = max(0.0, min(1.0, float(lognorm.cdf(service_hours, s=_SIGMA_LN, scale=mttf_low))))

    return ReliabilityResult(
        probability_of_failure=p_fail,
        confidence_interval=(pf_low, pf_high),
        predicted_lifetime=mttf,
        units="hours",
        model_used="blacks_equation",
        assumptions=[
            f"Material: {conductor_material}, n={n}, Ea={Ea} eV",
            "Lognormal scatter sigma=0.4 (Lloyd 1991)",
            "Steady-state current density (no AC component)",
            "Void nucleation at grain boundaries assumed dominant mechanism",
        ],
        inputs={
            "current_density_A_per_cm2": current_density_A_per_cm2,
            "temperature_celsius": temperature_celsius,
            "conductor_material": conductor_material,
            "service_life_years": service_life_years,
        },
        citations=[
            "Black JR, 'Electromigration — a brief survey and some recent results,' "
            "IEEE Trans. Electron Devices, 16(4), pp. 338-347, 1969.",
            "Lloyd JR, 'Electromigration failure,' J. Appl. Phys. 69(11), 1991.",
        ],
    )
