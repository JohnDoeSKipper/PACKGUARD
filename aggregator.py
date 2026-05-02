"""
PackGuard — Probability Aggregator & Application Threshold Engine

Aggregation formula: P(any failure) = 1 - ∏(1 - Pi)
with explicit interaction terms for known coupled failure modes.
"""

import math
from typing import Optional


# ── Interaction multipliers for known coupled failure modes ───────────────────
# When both modes are present, the first mode's probability is amplified.
# Source: JEDEC failure interaction models, IEEE TDMR Vol.18
INTERACTION_TERMS: dict[tuple[str, str], float] = {
    ("delamination",        "corrosion"):        1.40,  # delamination lets moisture in
    ("thermal_cycling",     "cte_mismatch"):     1.30,  # multiplicative damage
    ("void_thermal",        "solder_fatigue"):   1.20,  # voids concentrate thermal stress
    ("imc_wire_bond",       "thermal_cycling"):  1.25,  # IMC growth accelerated by cycling
    ("die_crack_propagation","solder_fatigue"):  1.50,  # crack propagates faster under reflow
}


def aggregate_failure_probability(per_mode_probs: dict[str, float]) -> float:
    """
    Combine per-mode probabilities into a single lot-level P(failure).

    Steps:
    1. Apply interaction multipliers for known coupled mode pairs.
    2. Clamp all probabilities to [0, 1].
    3. Compute 1 - ∏(1 - Pi) assuming conditional independence after step 1.

    Args:
        per_mode_probs: {failure_mode_name: probability_0_to_1}

    Returns:
        float: P(any failure occurs) in [0, 1]
    """
    # Work on a mutable copy
    probs = dict(per_mode_probs)

    # Step 1: apply interaction terms
    for (mode_a, mode_b), multiplier in INTERACTION_TERMS.items():
        if mode_a in probs and mode_b in probs:
            # Amplify mode_a when mode_b is also present
            probs[mode_a] = min(1.0, probs[mode_a] * multiplier)

    # Step 2 & 3: 1 - ∏(1 - Pi)
    if not probs:
        return 0.0
    p_no_failure = math.prod(max(0.0, 1.0 - p) for p in probs.values())
    return min(1.0, 1.0 - p_no_failure)


def dppm_from_probability(p_fail: float) -> float:
    """Convert a failure probability to Defects Per Million Parts."""
    return p_fail * 1_000_000


# ── Application-specific thresholds ──────────────────────────────────────────
# Source: AEC-Q100, JEDEC JESD47, cost-of-quality analysis (§5.3 of project brief)
APP_THRESHOLDS: dict[str, dict] = {
    "automotive": {
        "dppm_limit":    10,
        "p_fail_max":    0.00001,     # 10 DPPM
        "lifetime_yr":   15,
        "top_failure_modes": ["solder_fatigue", "imc_wire_bond", "corrosion"],
        "standard":      "AEC-Q100",
        "field_failure_cost_usd": 10_000,
        "rework_cost_usd":         50,
    },
    "server": {
        "dppm_limit":    100,
        "p_fail_max":    0.0001,      # 100 DPPM
        "lifetime_yr":   7,
        "top_failure_modes": ["electromigration", "solder_fatigue"],
        "standard":      "JEDEC JESD47",
        "field_failure_cost_usd": 2_000,
        "rework_cost_usd":         50,
    },
    "consumer": {
        "dppm_limit":    1000,
        "p_fail_max":    0.001,       # 1000 DPPM
        "lifetime_yr":   3,
        "top_failure_modes": ["solder_fatigue", "void_thermal"],
        "standard":      "IPC-9701",
        "field_failure_cost_usd": 300,
        "rework_cost_usd":         20,
    },
    "industrial": {
        "dppm_limit":    50,
        "p_fail_max":    0.00005,     # 50 DPPM
        "lifetime_yr":   10,
        "top_failure_modes": ["corrosion", "imc_wire_bond"],
        "standard":      "IPC-6012",
        "field_failure_cost_usd": 5_000,
        "rework_cost_usd":         50,
    },
}


def get_threshold(application: str) -> dict:
    """Return the quality threshold config for an application type."""
    return APP_THRESHOLDS.get(application.lower(), APP_THRESHOLDS["consumer"])


def compute_gate_decision(overall_p_fail: float, application: str) -> str:
    """
    Apply the application-specific threshold to produce a gate decision.

    Returns:
        "ship"   — P(fail) safely below threshold
        "hold"   — P(fail) within 5× of threshold (borderline)
        "reject" — P(fail) exceeds threshold
    """
    t = get_threshold(application)
    limit = t["p_fail_max"]

    if overall_p_fail <= limit:
        return "ship"
    elif overall_p_fail <= limit * 5:
        return "hold"
    else:
        return "reject"


def estimate_cost_saved(lot: object, checkpoints: list) -> float:
    """
    Estimate how much money PackGuard saved by catching defects early
    rather than letting the lot reach final test or field deployment.

    Cost avoided = (cost of remaining steps) + (field failure exposure)
    """
    # Approximate per-step processing cost (USD per lot of 3,000 chips)
    step_costs = {
        1: 0,       # dicing — no value added yet
        2: 500,     # die attach
        3: 800,     # wire bond
        4: 600,     # molding
        5: 400,     # reflow
        6: 700,     # test + burn-in
        7: 200,     # final gate
    }

    total = 0.0
    for chk in checkpoints:
        if hasattr(chk, 'cost_avoided'):
            total += chk.cost_avoided if chk.cost_avoided else 0.0

    return total if total > 0 else sum(step_costs.values()) * 0.3
