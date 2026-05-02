"""Standardized output types for all PackGuard physics modules.

Every reliability model in this package returns a `ReliabilityResult`. This
uniform shape is the contract the Orchestrator relies on. Changes to this
file affect every other module — discuss with Person 3 before modifying.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class ReliabilityResult(BaseModel):
    """Result returned by every reliability physics function.

    Attributes:
        probability_of_failure: P(fail) within the assumed service life,
            a number between 0 and 1.
        confidence_interval: (lower, upper) bounds at 90% confidence on
            probability_of_failure.
        predicted_lifetime: Expected lifetime in `units` before failure.
            Use float('inf') if the model predicts effectively no wear-out
            within reasonable timescales.
        units: Units for predicted_lifetime, e.g. "cycles", "hours", "years".
        model_used: Short canonical name, e.g. "coffin_manson", "blacks_equation".
        assumptions: Human-readable list of assumptions made.
        inputs: Echo of input parameters for traceability and audit.
        citations: List of references that justify the constants used.
    """
    model_config = ConfigDict(frozen=True)

    probability_of_failure: float = Field(ge=0.0, le=1.0)
    confidence_interval: tuple[float, float]
    predicted_lifetime: float
    units: str
    model_used: str
    assumptions: list[str]
    inputs: dict[str, Any]
    citations: list[str]

    def summary(self) -> str:
        """One-line summary suitable for logs and reports."""
        ci_low, ci_high = self.confidence_interval
        return (
            f"[{self.model_used}] P(fail) = {self.probability_of_failure:.4f} "
            f"(90% CI: {ci_low:.4f}–{ci_high:.4f}); "
            f"predicted lifetime = {self.predicted_lifetime:.2f} {self.units}"
        )
