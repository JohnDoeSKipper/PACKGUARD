"""Single entry point for the PackGuard Orchestrator.

Person 3's Orchestrator should call run_all_models(lot_state) and receive
a dict mapping model_name → ReliabilityResult. Models whose required inputs
are absent from lot_state are silently skipped.

Expected lot_state keys (all optional — missing keys just skip that model):

    Coffin-Manson (solder fatigue):
        delta_t_celsius          float   Temperature swing per cycle (°C)
        cycles_per_year          float   Thermal cycles per year
        service_life_years       float   Intended service life (years)
        solder_alloy             str     "SAC305" | "SAC405" | "Sn63Pb37"

    Black's equation (electromigration):
        current_density_A_per_cm2  float  Current density (A/cm²)
        temperature_celsius         float  Operating temperature (°C)
        conductor_material          str    "Cu" | "Al"

    Peck's model (humidity):
        relative_humidity_pct    float   RH (%)
        msl_rating               int     Moisture sensitivity level (1–6)
        # temperature_celsius shared with Black's equation

    Arrhenius IMC (wire bond intermetallic):
        wire_bond_temps_C        list[float]  Temperature stages (°C)
        wire_bond_times_h        list[float]  Time at each stage (hours)
        wire_pad_metallurgy      str          "Au-Al" | "Cu-Al" | "Au-Au"

    Griffith fracture (crack criticality):
        crack_length_mm          float   Observed crack half-length (mm)
        applied_stress_MPa       float   Applied tensile stress (MPa)
        fracture_toughness_MPa_sqrt_m  float  K_Ic (MPa·√m); default silicon

    Void thermal resistance:
        void_fraction            float   Die-attach void area fraction (0–0.9)
        void_distribution        str     "dispersed" | "clustered"
        nominal_thermal_resistance_K_per_W  float  R_th no-void (K/W)
        max_junction_temp_C      float   Max allowed T_j (°C)
        ambient_temp_C           float   Ambient temperature (°C)
        power_dissipation_W      float   Die power (W)

    Wire sweep:
        wire_length_mm           float   Bond wire free span (mm)
        wire_diameter_um         float   Wire diameter (µm)
        resin_viscosity_Pa_s     float   Mold compound viscosity (Pa·s)
        fill_velocity_m_per_s    float   Resin fill front velocity (m/s)
        wire_pitch_mm            float   Wire pitch (mm)

    Warpage:
        die_cte_ppm_per_C        float   Die CTE (ppm/°C)
        substrate_cte_ppm_per_C  float   Substrate CTE (ppm/°C)
        package_size_mm          float   Package side/diagonal (mm)
        peak_reflow_temp_C       float   Peak reflow temperature (°C)
        package_thickness_mm     float   Package thickness (mm)

    Weibull fit (burn-in TTF data):
        time_to_failure_hours    list[float]  TTF observations (hours)
        censored                 list[bool]   Optional: True = right-censored

    Survival simulator:
        initial_crack_mm         float   Initial crack length (mm)
        profile                  str     "automotive"|"server"|"consumer"
        # plus solder_alloy, wire_pad_metallurgy, void_fraction
"""
from __future__ import annotations
from typing import Any

from packguard_physics.types import ReliabilityResult
from packguard_physics.coffin_manson import predict_solder_fatigue
from packguard_physics.blacks_equation import predict_electromigration
from packguard_physics.pecks_model import predict_humidity_failure
from packguard_physics.arrhenius_imc import predict_imc_thickness
from packguard_physics.griffith_fracture import assess_crack_growth
from packguard_physics.void_thermal_resistance import assess_void_impact
from packguard_physics.wire_sweep import predict_wire_sweep
from packguard_physics.warpage import predict_warpage
from packguard_physics.weibull_fit import fit_weibull
from packguard_physics.survival_simulator import simulate_defect, SimulationTrace


def run_all_models(lot_state: dict[str, Any]) -> dict[str, ReliabilityResult]:
    """Run all applicable reliability physics models on lot_state.

    Models are skipped silently if their required inputs are not present.
    Results that raise exceptions are also skipped (with a print warning).

    Args:
        lot_state: Flat dict of measurement and configuration values.
                   See module docstring for full key reference.

    Returns:
        Dict mapping model canonical name → ReliabilityResult.
        Empty dict if no models had sufficient inputs.

    Example::

        from packguard_physics.api import run_all_models
        state = {
            "delta_t_celsius": 100,
            "cycles_per_year": 1000,
            "service_life_years": 10,
            "solder_alloy": "SAC305",
            "current_density_A_per_cm2": 1e6,
            "temperature_celsius": 85,
        }
        results = run_all_models(state)
        for name, r in results.items():
            print(r.summary())
    """
    results: dict[str, ReliabilityResult] = {}

    def _try(name: str, fn, *args, **kwargs) -> None:
        try:
            results[name] = fn(*args, **kwargs)
        except Exception as exc:
            print(f"[packguard_physics.api] {name} skipped: {exc}")

    s = lot_state  # alias for brevity

    # ── Coffin-Manson ────────────────────────────────────────────────────────
    if all(k in s for k in ("delta_t_celsius", "cycles_per_year", "service_life_years")):
        _try("coffin_manson", predict_solder_fatigue,
             delta_t_celsius=s["delta_t_celsius"],
             cycles_per_year=s["cycles_per_year"],
             service_life_years=s["service_life_years"],
             solder_alloy=s.get("solder_alloy", "SAC305"))

    # ── Black's equation ─────────────────────────────────────────────────────
    if all(k in s for k in ("current_density_A_per_cm2", "temperature_celsius")):
        _try("blacks_equation", predict_electromigration,
             current_density_A_per_cm2=s["current_density_A_per_cm2"],
             temperature_celsius=s["temperature_celsius"],
             conductor_material=s.get("conductor_material", "Cu"),
             service_life_years=s.get("service_life_years", 7.0))

    # ── Peck's model ─────────────────────────────────────────────────────────
    if all(k in s for k in ("relative_humidity_pct", "msl_rating")):
        _try("pecks_model", predict_humidity_failure,
             relative_humidity_pct=s["relative_humidity_pct"],
             temperature_celsius=s.get("temperature_celsius", 85.0),
             msl_rating=s["msl_rating"],
             service_life_years=s.get("service_life_years", 5.0))

    # ── Arrhenius IMC ────────────────────────────────────────────────────────
    if all(k in s for k in ("wire_bond_temps_C", "wire_bond_times_h")):
        _try("arrhenius_imc", predict_imc_thickness,
             temperature_history_celsius=s["wire_bond_temps_C"],
             time_at_temperature_hours=s["wire_bond_times_h"],
             wire_pad_metallurgy=s.get("wire_pad_metallurgy", "Au-Al"))

    # ── Griffith fracture ────────────────────────────────────────────────────
    if all(k in s for k in ("crack_length_mm", "applied_stress_MPa")):
        _try("griffith_fracture", assess_crack_growth,
             crack_length_mm=s["crack_length_mm"],
             applied_stress_MPa=s["applied_stress_MPa"],
             fracture_toughness_MPa_sqrt_m=s.get("fracture_toughness_MPa_sqrt_m", 0.83),
             material=s.get("material", "silicon"))

    # ── Void thermal resistance ──────────────────────────────────────────────
    if "void_fraction" in s:
        _try("void_thermal_resistance", assess_void_impact,
             void_fraction=s["void_fraction"],
             void_distribution=s.get("void_distribution", "dispersed"),
             nominal_thermal_resistance_K_per_W=s.get(
                 "nominal_thermal_resistance_K_per_W", 1.0),
             max_junction_temp_C=s.get("max_junction_temp_C", 125.0),
             ambient_temp_C=s.get("ambient_temp_C", 25.0),
             power_dissipation_W=s.get("power_dissipation_W", 5.0))

    # ── Wire sweep ───────────────────────────────────────────────────────────
    if all(k in s for k in ("wire_length_mm", "wire_diameter_um",
                            "resin_viscosity_Pa_s", "fill_velocity_m_per_s")):
        _try("wire_sweep", predict_wire_sweep,
             wire_length_mm=s["wire_length_mm"],
             wire_diameter_um=s["wire_diameter_um"],
             resin_viscosity_Pa_s=s["resin_viscosity_Pa_s"],
             fill_velocity_m_per_s=s["fill_velocity_m_per_s"],
             wire_pitch_mm=s.get("wire_pitch_mm", 0.1),
             wire_material=s.get("wire_material", "gold"))

    # ── Warpage ──────────────────────────────────────────────────────────────
    if all(k in s for k in ("die_cte_ppm_per_C", "substrate_cte_ppm_per_C",
                            "package_size_mm", "peak_reflow_temp_C")):
        _try("warpage", predict_warpage,
             die_cte_ppm_per_C=s["die_cte_ppm_per_C"],
             substrate_cte_ppm_per_C=s["substrate_cte_ppm_per_C"],
             package_size_mm=s["package_size_mm"],
             peak_reflow_temp_C=s["peak_reflow_temp_C"],
             room_temp_C=s.get("room_temp_C", 25.0),
             package_thickness_mm=s.get("package_thickness_mm", 1.0))

    # ── Weibull fit ──────────────────────────────────────────────────────────
    if "time_to_failure_hours" in s and len(s["time_to_failure_hours"]) >= 3:
        _try("weibull_fit", fit_weibull,
             time_to_failure_hours=s["time_to_failure_hours"],
             censored=s.get("censored"))

    return results


def run_survival_simulation(lot_state: dict[str, Any]) -> SimulationTrace | None:
    """Run the survival simulator if crack_length_mm is present in lot_state.

    Args:
        lot_state: Same dict passed to run_all_models.

    Returns:
        SimulationTrace or None if crack_length_mm is absent.
    """
    if "crack_length_mm" not in lot_state:
        return None
    try:
        return simulate_defect(
            initial_crack_mm=lot_state["crack_length_mm"],
            profile=lot_state.get("profile", "automotive"),
            solder_alloy=lot_state.get("solder_alloy", "SAC305"),
            wire_pad_metallurgy=lot_state.get("wire_pad_metallurgy", "Au-Al"),
            void_fraction=lot_state.get("void_fraction", 0.0),
            wire_length_mm=lot_state.get("wire_length_mm", 1.0),
            wire_diameter_um=lot_state.get("wire_diameter_um", 25.0),
        )
    except Exception as exc:
        print(f"[packguard_physics.api] survival_simulator skipped: {exc}")
        return None
