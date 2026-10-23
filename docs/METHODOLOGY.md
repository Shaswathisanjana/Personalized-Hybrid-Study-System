# Methodology and claims

## Engineering approach

PHSS was extended incrementally within its existing architecture: durable student snapshots; conservative concept identity migration; recoverable assessment transactions; fuller Learning, Coding and Research workflows; shared navigation; and reproducible evaluation. Milestone reports record scope and verification. Existing unrelated changes were retained.

The design separates content generation from evaluated evidence. Each agent observes the shared model, selects an appropriate bounded action, uses tools, evaluates submitted work, updates CACM and replans. Generating a lesson, listing resources or navigating to a page does not update mastery. This distinction is necessary for meaningful personalization.

Cross-agent disagreement is treated as a reason to gather diagnostic evidence, rather than silently replace one score with another. Shared concept identities make evidence comparable; ownership checks and saved receipts prevent cross-profile mixing and replay. Mastery/confidence values are application heuristics, not validated psychometric estimates.

The implemented mastery rule in `app/cognitive/mastery_engine.py` uses `w = reliability * (0.5 + 0.5 * difficulty)` and `new_mastery = old_mastery + w * (performance - old_mastery)`, clamped to [0, 1] and rounded. Each accepted evidence item increments attempts; confidence increases by `0.1 * w` up to 1. The conflict detector compares performances for the same student/concept from different agents, using default disagreement thresholds 0.35 and 0.60 for high severity. These are inspectable design parameters, not empirically optimized values. Diagnostics and misconception handling add their own state transitions; the score formula alone is not the entire CACM model.

## Evaluation design

The primary evidence is executable assertion-based testing of state changes, failure recovery and UI boundaries. Synthetic providers make scenarios reproducible and avoid paid calls. Coding reference solutions additionally exercise the actual subprocess test runner. Streamlit AppTest exercises the main application with fixture services and temporary storage.

Tests intentionally include negative cases: stale revisions, changed replay payloads, failed follow-up generation, invalid source quotes, duplicate publications, rejected abstracts, unsupported coding topics and profile switches. Passing these checks supports the tested behavior in the recorded environment. It does not establish reliability for every prompt, platform, provider outage or concurrent deployment.

Standalone historical scripts are reported separately because a zero exit code is a weaker observation than an assertion-bearing unit test. Unselected tests, live integrations, manual browser checks and educational outcomes are not inferred from suite success.

## Defensible project contribution

The implemented contribution is an integrated prototype connecting three study workflows to shared evidence, cross-agent conflict diagnostics and durable recovery. Demonstrate its specific state transitions and compare them with independent per-agent state as a design motivation. Do not claim superiority over other systems without an explicit comparative evaluation.

Academic analysis uses retrieved paper metadata/abstracts and checked quotes. It is abstract-grounded assistance, not a completed systematic literature review. There is no documented exhaustive database search, preregistered selection protocol, full-text appraisal or measured inter-rater agreement.

For a dissertation, separate design decisions, software verification, illustrative scenarios and future empirical validation into distinct sections. Cite actual papers consulted and actual experimental records; do not turn fixture reports into literature evidence.
