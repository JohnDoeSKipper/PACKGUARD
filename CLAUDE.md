# PackGuard Physics — Claude Code Session Memory

## Project Context

`packguard_physics` is a Python library of 10 reliability physics modules for
PackGuard v2.0. It is consumed by Person 3's Orchestrator via a single entry
point (`api.py`). Every module returns `ReliabilityResult` — do not change
that type without coordinating with Person 3.

## Output Contract (IMMUTABLE — coordinate with Person 3 before changing)

Every physics function returns `packguard_physics.types.ReliabilityResult`:

```python
class ReliabilityResult(BaseModel):
    probability_of_failure: float   # [0, 1]
    confidence_interval: tuple[float, float]
    predicted_lifetime: float
    units: str
    model_used: str
    assumptions: list[str]
    inputs: dict[str, Any]
    citations: list[str]
```

## Coding Rules (apply to every module)

1. Every constant (n, C, Ea, k, etc.) must be cited with author, paper, year.
2. Every function has a docstring with equation, parameters+units, example.
3. Every module has a test file in `tests/` with ≥3 tests: happy-path, edge, error.
4. Use `scipy` for distributions and fitting. Use `numpy` for arrays.
5. Return `ReliabilityResult` — never a raw dict or custom type.

## Module Inventory

| File | Model | Key Equation |
|------|-------|-------------|
| `coffin_manson.py` | Solder thermal fatigue | Nf = C × ΔT^(-n) |
| `blacks_equation.py` | Electromigration | MTTF = A × J^(-n) × exp(Ea/kT) |
| `pecks_model.py` | Humidity corrosion | TTF = A × RH^(-n) × exp(Ea/kT) |
| `arrhenius_imc.py` | IMC wire bond growth | x = √(D0 × exp(-Ea/kT) × t) |
| `griffith_fracture.py` | Crack criticality | a_c = (1/π)(K_Ic/σ)² |
| `void_thermal_resistance.py` | Void thermal impact | R_eff = R_nom/(1-f)^k |
| `wire_sweep.py` | Wire deflection in mold | δ = f×L⁴/(8EI), Oseen drag |
| `warpage.py` | Package warpage | δ = 3ΔCTE×ΔT×L²/(2t) |
| `weibull_fit.py` | Burn-in TTF distribution | Weibull MLE via scipy |
| `survival_simulator.py` | Step-through defect fate | Calls above modules |
| `api.py` | Orchestrator facade | run_all_models(lot_state) |

## Calibration Notes (checked during build — DO NOT revert)

- **Coffin-Manson C constants**: n=2.0, C=2.0e7 for SAC305 (calibrated to
  Nf≈2000 at ΔT=100°C per IPC-9701A). The original "C=26300" from raw
  Schubert strain-life tables is WRONG when ΔT is in °C — it gives Nf<20 cycles.

- **Peck's model A constant**: A=1.045 (calibrated to TTF=1000h at 85°C/85%RH).
  A=1.045e-3 is wrong — it gives TTF=1h at JEDEC standard conditions.

- **Black's equation A (Cu)**: A=674, calibrated so MTTF≈1000h at J=1e6 A/cm²,
  T=100°C.

- **Wire sweep criterion**: δ > 10% of wire SPAN (not pitch). Oseen-Burgers
  drag formula: f = 4πηv / (ln(2L/d) − 0.5772).

## Orchestrator Integration Snippet (for Person 3)

```python
from packguard_physics.api import run_all_models, run_survival_simulation

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
```

## Killer Demo Scenario

1.8 mm crack, automotive profile, SAC305 → fails at `die_attach` (P=1.0,
crack grows to 2.115 mm). Full trace in `references/killer_demo_trace.txt`.

## Project Layout

```
src/packguard_physics/   all 11 modules + types.py
tests/                   one test file per module
references/              killer_demo_trace.txt, CITATIONS.md
notebooks/               validation notebooks
```

## How to Run

```bash
source .venv/bin/activate
pytest -v                                        # all tests
pytest --cov=packguard_physics --cov-report=html # coverage
```
