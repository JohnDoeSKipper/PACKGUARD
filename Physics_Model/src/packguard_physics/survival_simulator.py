"""Survival simulator: propagates a defect through manufacturing steps.

Each step applies a stress model that can grow or kill the defect.
Output is a step-by-step trace of the defect's fate.

Manufacturing steps in order:
  1. die_attach     — cure shrinkage, thermal stress (Griffith fracture)
  2. wire_bond      — IMC nucleation, vibration stress
  3. molding        — wire sweep risk, encapsulant cure stress
  4. reflow         — peak thermal shock, Coffin-Manson + Griffith
  5. burn_in        — elevated T + V stress (Arrhenius acceleration)
  6. field_service  — cyclic fatigue (Coffin-Manson over service life)

A defect is killed (fails) when P(fail) ≥ kill_threshold at any step.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

from packguard_physics.griffith_fracture import assess_crack_growth
from packguard_physics.coffin_manson import predict_solder_fatigue
from packguard_physics.arrhenius_imc import predict_imc_thickness
from packguard_physics.wire_sweep import predict_wire_sweep
from packguard_physics.void_thermal_resistance import assess_void_impact


@dataclass
class DefectState:
    """Mutable state of a single defect being propagated through manufacturing."""
    crack_length_mm: float = 0.0
    imc_thickness_um: float = 0.0
    wire_deflection_mm: float = 0.0
    void_fraction: float = 0.0
    alive: bool = True
    fail_step: str | None = None
    fail_reason: str | None = None


@dataclass
class StepResult:
    """Result from one manufacturing step."""
    step_name: str
    p_fail: float
    defect_killed: bool
    metric_name: str
    metric_value: float
    metric_units: str
    notes: str


@dataclass
class SimulationTrace:
    """Full simulation trace for one defect."""
    initial_crack_mm: float
    profile: str
    solder_alloy: str
    steps: list[StepResult] = field(default_factory=list)
    survived: bool = True
    kill_step: str | None = None

    def print_trace(self) -> None:
        print(f"\n=== Survival Simulation: crack={self.initial_crack_mm}mm, "
              f"profile={self.profile}, alloy={self.solder_alloy} ===")
        for s in self.steps:
            status = "KILLED" if s.defect_killed else "SURVIVED"
            print(f"  [{s.step_name:20s}] {status:8s}  "
                  f"P(fail)={s.p_fail:.4f}  "
                  f"{s.metric_name}={s.metric_value:.4f} {s.metric_units}")
            if s.notes:
                print(f"                           → {s.notes}")
        outcome = "SURVIVES to field service" if self.survived else f"FAILS at {self.kill_step}"
        print(f"\n  OUTCOME: {outcome}\n")


# Thermal profiles: (delta_T_die_attach, stress_MPa_die_attach,
#                    delta_T_reflow, cycles_per_year_field, service_life_years)
_PROFILES: dict[str, dict[str, Any]] = {
    "automotive": {
        "die_attach_delta_T": 175,    # °C, cure shrinkage equivalent ΔT
        "die_attach_stress_MPa": 80,
        "reflow_delta_T": 240,        # °C, peak reflow − ambient
        "reflow_stress_MPa": 120,
        "field_delta_T": 190,
        "field_cycles_per_year": 1000,
        "field_service_years": 15,
        "wire_bond_temps_C": [200, 250],
        "wire_bond_times_h": [0.5, 0.25],
        "wire_sweep_velocity": 0.08,
        "burn_in_temp_C": 125,
        "burn_in_hours": 48,
    },
    "server": {
        "die_attach_delta_T": 120,
        "die_attach_stress_MPa": 50,
        "reflow_delta_T": 230,
        "reflow_stress_MPa": 90,
        "field_delta_T": 60,
        "field_cycles_per_year": 2000,
        "field_service_years": 7,
        "wire_bond_temps_C": [175, 200],
        "wire_bond_times_h": [0.5, 0.25],
        "wire_sweep_velocity": 0.05,
        "burn_in_temp_C": 105,
        "burn_in_hours": 24,
    },
    "consumer": {
        "die_attach_delta_T": 80,
        "die_attach_stress_MPa": 35,
        "reflow_delta_T": 220,
        "reflow_stress_MPa": 70,
        "field_delta_T": 40,
        "field_cycles_per_year": 200,
        "field_service_years": 3,
        "wire_bond_temps_C": [150, 175],
        "wire_bond_times_h": [0.5, 0.25],
        "wire_sweep_velocity": 0.005,
        "burn_in_temp_C": 85,
        "burn_in_hours": 12,
    },
}

_KILL_THRESHOLD = 0.90  # P(fail) >= 90% at a step → defect killed / part fails


def simulate_defect(
    initial_crack_mm: float = 0.0,
    profile: str = "automotive",
    solder_alloy: str = "SAC305",
    kill_threshold: float = _KILL_THRESHOLD,
    wire_pad_metallurgy: str = "Au-Al",
    void_fraction: float = 0.0,
    wire_length_mm: float = 1.0,
    wire_diameter_um: float = 25.0,
) -> SimulationTrace:
    """Propagate a defect through all 6 manufacturing + field steps.

    At each step the relevant physics module is called. If P(fail) >= kill_threshold
    the defect is declared a failure at that step and simulation stops.

    Args:
        initial_crack_mm: Starting crack half-length (mm). 0 = no crack.
        profile: Thermal profile — "automotive", "server", or "consumer".
        solder_alloy: Solder alloy for Coffin-Manson step.
        kill_threshold: P(fail) >= this value → part fails at this step.
        wire_pad_metallurgy: Metallurgy for IMC step.
        void_fraction: Die-attach void fraction (0–0.9).
        wire_length_mm: Bond wire free span (mm).
        wire_diameter_um: Bond wire diameter (µm).

    Returns:
        SimulationTrace with full step-by-step results.
    """
    if profile not in _PROFILES:
        raise ValueError(f"Unknown profile '{profile}'. Choose from {list(_PROFILES)}")

    p = _PROFILES[profile]
    state = DefectState(
        crack_length_mm=initial_crack_mm,
        void_fraction=void_fraction,
    )
    trace = SimulationTrace(
        initial_crack_mm=initial_crack_mm,
        profile=profile,
        solder_alloy=solder_alloy,
    )

    def record(step_name: str, p_fail: float, metric_name: str,
               metric_value: float, metric_units: str, notes: str = "") -> bool:
        killed = p_fail >= kill_threshold
        trace.steps.append(StepResult(
            step_name=step_name,
            p_fail=p_fail,
            defect_killed=killed,
            metric_name=metric_name,
            metric_value=metric_value,
            metric_units=metric_units,
            notes=notes,
        ))
        if killed:
            trace.survived = False
            trace.kill_step = step_name
            state.alive = False
        return killed

    # ── Step 1: Die Attach ──────────────────────────────────────────────────
    r1 = assess_crack_growth(
        crack_length_mm=state.crack_length_mm,
        applied_stress_MPa=p["die_attach_stress_MPa"],
    )
    # Crack growth: Δa proportional to ΔT (simplified Paris-like increment)
    crack_growth = 0.001 * p["die_attach_delta_T"] * state.crack_length_mm
    state.crack_length_mm += crack_growth
    if record("die_attach", r1.probability_of_failure,
              "crack_mm", state.crack_length_mm, "mm",
              f"stress={p['die_attach_stress_MPa']} MPa, "
              f"crack grew by {crack_growth:.4f} mm"):
        return trace

    # ── Step 2: Wire Bond (IMC) ─────────────────────────────────────────────
    r2 = predict_imc_thickness(
        temperature_history_celsius=p["wire_bond_temps_C"],
        time_at_temperature_hours=p["wire_bond_times_h"],
        wire_pad_metallurgy=wire_pad_metallurgy,
    )
    state.imc_thickness_um = r2.predicted_lifetime
    if record("wire_bond", r2.probability_of_failure,
              "imc_um", state.imc_thickness_um, "µm",
              f"metallurgy={wire_pad_metallurgy}"):
        return trace

    # ── Step 3: Molding (Wire Sweep) ────────────────────────────────────────
    r3 = predict_wire_sweep(
        wire_length_mm=wire_length_mm,
        wire_diameter_um=wire_diameter_um,
        resin_viscosity_Pa_s=5.0,
        fill_velocity_m_per_s=p["wire_sweep_velocity"],
    )
    state.wire_deflection_mm = r3.predicted_lifetime
    if record("molding", r3.probability_of_failure,
              "deflection_mm", state.wire_deflection_mm, "mm",
              f"fill_velocity={p['wire_sweep_velocity']} m/s"):
        return trace

    # ── Step 4: Reflow (Griffith at peak thermal shock) ─────────────────────
    r4 = assess_crack_growth(
        crack_length_mm=state.crack_length_mm,
        applied_stress_MPa=p["reflow_stress_MPa"],
    )
    reflow_crack_growth = 0.003 * p["reflow_delta_T"] * max(state.crack_length_mm, 0.001)
    state.crack_length_mm += reflow_crack_growth
    if record("reflow", r4.probability_of_failure,
              "crack_mm", state.crack_length_mm, "mm",
              f"peak ΔT={p['reflow_delta_T']}°C, stress={p['reflow_stress_MPa']} MPa"):
        return trace

    # ── Step 5: Burn-in (Arrhenius-accelerated void impact) ─────────────────
    r5 = assess_void_impact(
        void_fraction=state.void_fraction,
        ambient_temp_C=p["burn_in_temp_C"],
        power_dissipation_W=3.0,
    )
    if record("burn_in", r5.probability_of_failure,
              "T_j_C", r5.predicted_lifetime, "°C",
              f"burn-in at {p['burn_in_temp_C']}°C for {p['burn_in_hours']}h"):
        return trace

    # ── Step 6: Field Service (Coffin-Manson fatigue) ───────────────────────
    r6 = predict_solder_fatigue(
        delta_t_celsius=p["field_delta_T"],
        cycles_per_year=p["field_cycles_per_year"],
        service_life_years=p["field_service_years"],
        solder_alloy=solder_alloy,
    )
    record("field_service", r6.probability_of_failure,
           "Nf_cycles", r6.predicted_lifetime, "cycles",
           f"ΔT={p['field_delta_T']}°C, "
           f"{p['field_cycles_per_year']} cy/yr × {p['field_service_years']} yr")

    return trace


def simulate_batch(
    defects: list[dict],
    profile: str = "automotive",
    solder_alloy: str = "SAC305",
) -> list[SimulationTrace]:
    """Run simulate_defect for a list of defect parameter dicts.

    Args:
        defects: List of dicts; each dict can override any kwarg of simulate_defect.
        profile: Default thermal profile.
        solder_alloy: Default solder alloy.

    Returns:
        List of SimulationTrace, one per defect.
    """
    results = []
    for d in defects:
        kwargs = {"profile": profile, "solder_alloy": solder_alloy}
        kwargs.update(d)
        results.append(simulate_defect(**kwargs))
    return results
