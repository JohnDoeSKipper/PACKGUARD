# packguard_physics

Reliability physics library for PackGuard v2.0. Ten modules, one output type,
one entry point for the Orchestrator.

## Install

```bash
cd packguard-physics
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Quick Start (for Person 3 — Orchestrator)

```python
from packguard_physics.api import run_all_models, run_survival_simulation

state = {
    "delta_t_celsius": 100,
    "cycles_per_year": 1000,
    "service_life_years": 10,
    "solder_alloy": "SAC305",
    "current_density_A_per_cm2": 1e6,
    "temperature_celsius": 85,
    "void_fraction": 0.15,
    "crack_length_mm": 0.0,
}

results = run_all_models(state)
for name, r in results.items():
    print(r.summary())

# Defect survival trace
trace = run_survival_simulation({"crack_length_mm": 1.8, "profile": "automotive"})
if trace:
    trace.print_trace()
```

## Output Shape (every module)

Every function returns `ReliabilityResult`:

| Field | Type | Description |
|-------|------|-------------|
| `probability_of_failure` | float [0,1] | P(fail) within service life |
| `confidence_interval` | (float, float) | 90% CI on P(fail) |
| `predicted_lifetime` | float | Lifetime in `units` |
| `units` | str | e.g. "cycles", "hours", "mm" |
| `model_used` | str | Canonical model name |
| `assumptions` | list[str] | Constants and simplifications used |
| `inputs` | dict | Echo of inputs for audit trail |
| `citations` | list[str] | Published sources for all constants |

## Module Reference

### `coffin_manson.predict_solder_fatigue`
```python
predict_solder_fatigue(
    delta_t_celsius=100, cycles_per_year=1000,
    service_life_years=10, solder_alloy="SAC305"
)  # → ReliabilityResult, units="cycles"
```
Alloys: `SAC305`, `SAC405`, `Sn63Pb37`.

### `blacks_equation.predict_electromigration`
```python
predict_electromigration(
    current_density_A_per_cm2=1e6, temperature_celsius=85,
    conductor_material="Cu", service_life_years=7
)  # → ReliabilityResult, units="hours"
```
Materials: `Cu`, `Al`.

### `pecks_model.predict_humidity_failure`
```python
predict_humidity_failure(
    relative_humidity_pct=85, temperature_celsius=85,
    msl_rating=3, service_life_years=5
)  # → ReliabilityResult, units="hours"
```
MSL ratings 1–6 per IPC/JEDEC J-STD-020E.

### `arrhenius_imc.predict_imc_thickness`
```python
predict_imc_thickness(
    temperature_history_celsius=[150, 200],
    time_at_temperature_hours=[100, 50],
    wire_pad_metallurgy="Au-Al"
)  # → ReliabilityResult, units="micrometers"
```
Metallurgies: `Au-Al`, `Cu-Al`, `Au-Au`.

### `griffith_fracture.assess_crack_growth`
```python
assess_crack_growth(
    crack_length_mm=0.5, applied_stress_MPa=50,
    fracture_toughness_MPa_sqrt_m=0.83, material="silicon"
)  # → ReliabilityResult, units="mm" (critical crack length)
```

### `void_thermal_resistance.assess_void_impact`
```python
assess_void_impact(
    void_fraction=0.3, void_distribution="dispersed",
    nominal_thermal_resistance_K_per_W=1.0,
    max_junction_temp_C=125, ambient_temp_C=25, power_dissipation_W=5
)  # → ReliabilityResult, units="celsius" (predicted T_j)
```

### `wire_sweep.predict_wire_sweep`
```python
predict_wire_sweep(
    wire_length_mm=1.5, wire_diameter_um=25,
    resin_viscosity_Pa_s=5, fill_velocity_m_per_s=0.05,
    wire_pitch_mm=0.1, wire_material="gold"
)  # → ReliabilityResult, units="mm" (deflection)
```

### `warpage.predict_warpage`
```python
predict_warpage(
    die_cte_ppm_per_C=2.6, substrate_cte_ppm_per_C=18,
    package_size_mm=25, peak_reflow_temp_C=260,
    room_temp_C=25, package_thickness_mm=1.0
)  # → ReliabilityResult, units="mm" (warpage)
```

### `weibull_fit.fit_weibull`
```python
fit_weibull(
    time_to_failure_hours=[800, 850, 900, 950, 1000],
    censored=None
)  # → ReliabilityResult, units="hours"; inputs dict has beta, eta
```

### `survival_simulator.simulate_defect`
```python
simulate_defect(
    initial_crack_mm=1.8, profile="automotive",
    solder_alloy="SAC305"
)  # → SimulationTrace (not ReliabilityResult)
```
Profiles: `automotive`, `server`, `consumer`.

## Citations

All constants are sourced from published literature. See module docstrings
and `references/CITATIONS.md` for full references.

## Tests

```bash
pytest -v
pytest --cov=packguard_physics --cov-report=html
```

## Key Files

- `CLAUDE.md` — onboarding doc for future Claude Code sessions
- `references/killer_demo_trace.txt` — 1.8 mm crack automotive demo output
- `src/packguard_physics/api.py` — single entry point for Person 3
