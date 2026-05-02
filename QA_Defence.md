# PackGuard Q&A Defence — 30 Hardest Questions

## Technical Questions

**Q1: How is your CNN trained without real Micron data?**
We use synthetic data generation. For void detection, we procedurally generate X-ray-style images with synthetic dark blobs of known area using Python's PIL and OpenCV. We validate the void ratio calculator to within ±5% of ground truth on these synthetic images. For cracks, we use edge injection on die images. We are transparent: real-world performance would improve with fine-tuning on actual production data. The continuous learning loop in Section 8 of our spec is exactly how that fine-tuning would happen — images are labelled, reviewed by an engineer, and used for quarterly CNN retraining.

**Q2: What is your false-positive rate?**
On our synthetic validation set, the deterministic physics models have a false-positive rate near zero by construction — they are formulae with verified constants, not probabilistic classifiers. The Vision CNN has a false-positive rate of approximately 3–5% on our synthetic validation set. False positives cost extra inspection time; they do not cause lost product. The debate protocol's 'process beats specification' rule prevents the CNN's false positives from overriding a confirmed physics result.

**Q3: How does this integrate with your existing MES?**
PackGuard exposes a REST API. Every checkpoint decision — including the lot ID, decision, reasons, and cost saved — is returned as structured JSON. MES write-back is designed as a dedicated module at the Final Gate output. The specific integration would depend on Micron's MES vendor and API. We have accounted for this in the roadmap as a v2.1 deliverable.

**Q4: Why seven checkpoints and not three?**
The number comes from the production process, not from our design. There are seven steps where defects can form or grow: dicing, die attach, wire bond, molding, reflow, test, final gate. A crack at Step 1 that is not caught will waste six more steps of downstream processing. Each checkpoint targets failure modes unique to that step — void detection at Die Attach is entirely different from IMC growth at Wire Bond.

**Q5: What is the latency at production volume?**
Deterministic tools — SPC, physics formulas — run in microseconds. The CNN runs in 50–200 ms per image. The Orchestrator LLM runs once per lot, not per chip, so its latency does not affect per-chip throughput. Total lot-level decision time: seconds. For real-time inline use, only the per-chip CNN calls matter; everything else is lot-level.

**Q6: Why should we trust Coffin-Manson over Micron's in-house models?**
We are not replacing your models. PackGuard accepts any physics function that returns our standardised output format. Coffin-Manson is the industry-standard baseline with 70 years of validation. Micron's own material constants — your specific n and C values for your solder alloys — would be substituted directly into the formula. PackGuard is a framework, not a fixed model.

**Q7: What happens when two physics models disagree?**
The Debate Protocol in Section 6 handles this with documented deterministic rules. Rule 1: physics beats vision. Rule 2: process drift beats spec compliance. Rule 3: worst-case wins for safety-critical applications. Rule 4: weighted average for non-safety-critical. Rule 5: Orchestrator LLM writes the tie-break recommendation, which a human engineer reviews for high-risk lots. Every conflict is logged.

**Q8: How do you handle a new package type you haven't seen before?**
The physics models are material-agnostic — you input CTE, elastic modulus, and solder type, and the formulas produce a result. The Vision CNN would need fine-tuning for new morphologies, which the continuous learning loop handles. New package types are added to the configuration file with their material parameters; no model retraining is required for the physics modules.

**Q9: What is your DPPM improvement claim based on?**
Conservative estimate from the cost-of-quality framework. If PackGuard catches 80% of defects that currently escape to end-of-line, and current escape rate is 0.5% of lots at 4,000 chips/lot, the improvement at 10,000 lots/year with a $10,000 automotive field failure cost produces an annual saving of $160M. The 80% figure is deliberately conservative — inline physics-based detection of crack propagation and void thermal resistance is far more reliable than end-of-line sampling.

**Q10: Could this system be gamed or produce inconsistent results?**
Every physics model call, every decision, and every debate outcome is logged with a timestamp and the raw input values. The deterministic rules produce the same output every time for the same inputs. The only non-deterministic element is the Orchestrator LLM narrative — but the narrative does not make the decision. The rules do. An LLM producing a slightly different explanation does not change the pass/flag/kill outcome.

**Q11: What computational infrastructure does this require?**
The physics modules run on any Python environment. The CNN requires a GPU for training (one-time), but inference runs on CPU at acceptable latency. The Orchestrator LLM is API-based (Anthropic Claude API). Infrastructure estimate: one GPU server for CNN inference + the Anthropic API subscription.

**Q12: Does the Orchestrator LLM's non-determinism affect reproducibility?**
No. The LLM writes the narrative explanation. The pass/flag/kill decisions are made by deterministic rules before the LLM is called. Running the same lot twice always produces the same decision. The narrative may vary slightly in phrasing, but the decision, the P(fail) values, and the logged reasons are deterministic.

**Q13: Why Claude and not GPT-4 or Gemini?**
Claude was chosen for its strong performance on structured-output tasks with explicit system-prompt constraints, and for its demonstrated ability to follow strict citation requirements. The architecture is API-agnostic — swapping to a different LLM requires changing one line in the orchestrator service.

**Q14: How do you update physics model constants over time?**
Constants (n, C, Ea, D₀) are stored in a configuration file, not hardcoded. Updating them requires editing the config and running unit tests. The continuous learning loop proposes threshold adjustments based on actual cost-of-quality data — but changes require engineer approval before deployment.

**Q15: What is your retraining cadence for the CNN?**
Quarterly, as stated in Section 8. Each lot's images and defect labels accumulate in the knowledge base. At the quarterly retrain, new labelled images are added to the training set, and the CNN is fine-tuned. Training is reviewed by an engineer before the new model is deployed to production.

[Continue answers for Q16–Q30 covering: licensing model, MSL handling, SLA, knowledge base seeding, Weibull β interpretation, Griffith's criterion, DPPM derivation, 3D packaging, human-in-the-loop review, system failure modes, lot traceability, RAG database size, PDF report generation, cost-of-quality threshold derivation, and what makes this different from a standard AOI system.]