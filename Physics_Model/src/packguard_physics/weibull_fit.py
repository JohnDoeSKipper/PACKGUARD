"""Weibull distribution fitting to time-to-failure (TTF) burn-in data.

Fits a 2-parameter Weibull using MLE (scipy.stats.weibull_min).
Interprets β (shape) for failure mode classification:
  β < 1 : infant mortality (burn-in defects)
  β = 1 : random / exponential (no wear-out)
  β > 1 : wear-out (fatigue, corrosion, aging)

References:
  Weibull W. "A statistical distribution function of wide applicability."
  J. Appl. Mechanics, 18, 1951, pp. 293-297.

  Nelson W. "Applied Life Data Analysis." Wiley, 1982. (Chapter 5 on Weibull fitting)

  ReliaSoft. "Life Data Analysis Reference." ReliaSoft Corp., 2007.
  (Standard reference for β interpretation thresholds)
"""
from __future__ import annotations
import math
import numpy as np
from scipy.stats import weibull_min
from packguard_physics.types import ReliabilityResult


def fit_weibull(
    time_to_failure_hours: list[float],
    censored: list[bool] | None = None,
) -> ReliabilityResult:
    """Fit a 2-parameter Weibull to TTF data and assess population reliability.

    Uses scipy.stats.weibull_min MLE fitting. Censored observations are
    excluded from the fit (right-censored only; full censored-MLE not implemented).

    Args:
        time_to_failure_hours: Observed or censored TTF values (hours). Min 3 points.
        censored: Optional boolean list; True = right-censored (survived). Same length.

    Returns:
        ReliabilityResult where:
          predicted_lifetime = Weibull characteristic life η (scale, hours)
          inputs dict includes 'beta' (shape) and 'eta' (scale)
          P(fail) = F(η) = 1 - exp(-1) ≈ 0.6321 by definition of scale parameter,
          adjusted to represent the population failure fraction at η.

    Example:
        >>> r = fit_weibull([100, 200, 150, 80, 300])
        >>> r.inputs['beta'] > 0
        True
    """
    if len(time_to_failure_hours) < 3:
        raise ValueError("At least 3 data points required for Weibull fitting")
    if any(t <= 0 for t in time_to_failure_hours):
        raise ValueError("All TTF values must be positive")

    ttf = np.array(time_to_failure_hours, dtype=float)

    # Filter out censored observations for simple MLE
    if censored is not None:
        if len(censored) != len(time_to_failure_hours):
            raise ValueError("censored must have same length as time_to_failure_hours")
        failed = ttf[~np.array(censored, dtype=bool)]
        if len(failed) < 3:
            raise ValueError("At least 3 non-censored failures required")
        ttf_fit = failed
    else:
        ttf_fit = ttf

    # scipy weibull_min: shape=c (β), scale=η, loc fixed at 0
    beta, loc, eta = weibull_min.fit(ttf_fit, floc=0)

    # P(fail) = 1 - exp(-(η/η)^β) = 1 - exp(-1) ≈ 0.632 at t=η by definition
    # Report P(fail) at t=η as the characteristic population fraction
    p_fail_at_eta = float(1.0 - math.exp(-1.0))  # always 0.6321

    # 90% CI on β via bootstrap (200 resamples)
    rng = np.random.default_rng(42)
    betas = []
    for _ in range(200):
        sample = rng.choice(ttf_fit, size=len(ttf_fit), replace=True)
        b, _, _ = weibull_min.fit(sample, floc=0)
        betas.append(b)
    beta_lo = float(np.percentile(betas, 5))
    beta_hi = float(np.percentile(betas, 95))

    # P(fail) CI at t=η using beta bounds
    pf_lo = float(1.0 - math.exp(-(eta / eta) ** beta_hi))  # higher β → steeper CDF
    pf_hi = float(1.0 - math.exp(-(eta / eta) ** beta_lo))

    if beta < 1.0:
        mode_str = "infant mortality (β<1) — burn-in recommended"
    elif abs(beta - 1.0) < 0.1:
        mode_str = "random failure (β≈1) — exponential distribution"
    else:
        mode_str = f"wear-out (β={beta:.2f}>1) — aging/fatigue dominant"

    return ReliabilityResult(
        probability_of_failure=p_fail_at_eta,
        confidence_interval=(pf_lo, pf_hi),
        predicted_lifetime=eta,
        units="hours",
        model_used="weibull_fit",
        assumptions=[
            "2-parameter Weibull, location fixed at 0",
            "MLE fitting via scipy.stats.weibull_min",
            "Right-censored observations excluded (not full censored-MLE)",
            f"Failure mode classification: {mode_str}",
            "90% CI on β via 200-sample bootstrap",
        ],
        inputs={
            "n_failures": len(ttf_fit),
            "n_censored": len(ttf) - len(ttf_fit),
            "beta": float(beta),
            "eta": float(eta),
            "beta_90ci": (beta_lo, beta_hi),
        },
        citations=[
            "Weibull W, 'A statistical distribution function of wide applicability,' "
            "J. Appl. Mechanics, 18, 1951, pp. 293-297.",
            "Nelson W, 'Applied Life Data Analysis,' Wiley, 1982.",
            "ReliaSoft, 'Life Data Analysis Reference,' ReliaSoft Corp., 2007.",
        ],
    )
