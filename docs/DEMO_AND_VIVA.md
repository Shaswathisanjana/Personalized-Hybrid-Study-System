# Presentation and demonstration guide

## Suggested six-slide outline

1. **Problem:** separate study tools can make inconsistent assumptions about one student's understanding.
2. **Architecture:** three specialized agents share CACM; show the diagram in ARCHITECTURE.md.
3. **Evidence loop:** assessed activity changes state, disagreement requests diagnostics, diagnostic evidence updates recommendations.
4. **Reliability:** durable profiles, exact concept aliases, saved transaction stages, duplicate prevention and source traceability.
5. **Evaluation:** show a freshly generated summary, distinguish unittest counts from standalone scripts, and walk through the controlled integration scenario.
6. **Boundaries and future work:** local execution/identity limits, live-provider validation and a future real-student study.

## Reproducible offline demonstration

Run `python -B tools/evaluate_offline.py --only test_student_journey` and show its logs plus `docs/EVALUATION.md`. Explain the five learning answers, failing original code, research assessment and diagnostic resolution. The scenario uses real services and cognitive updates with synthetic provider fixtures; it does not populate the real app's student database.

For visible controlled Streamlit verification, run `python -B tools/evaluate_offline.py --only test_student_journey_streamlit`. AppTest exercises the UI programmatically; this is not a live classroom recording or a substitute for a manual browser check.

## Manual browser checklist

Use a disposable local profile. Live content/assessment actions require configured providers and may cost money; prepare and authorize that separately.

- Start `review_ui.py`, note the profile URL, choose Recursion and inspect the shared recommendations. An unassessed topic must not appear as demonstrated mastery.
- Generate learning content, start a quiz and submit an answer. Refresh using the same profile URL; confirm saved progress and the active assessment.
- Use Continue coding practice. Explicitly load the recommended exercise and enter a draft. Switch pages and return; confirm the draft and exercise survive.
- Use Continue research. Confirm topic/concept prefill without automatic provider work. If authorized, run a small analysis and inspect accepted/rejected sources and shortfalls.
- Switch to a second profile; confirm the first profile's answers/code/job are absent. Return to the first profile and confirm restoration.
- If a genuine conflict occurs, use Resolve conflicting evidence and complete the diagnostic. Do not insert artificial state or claim a conflict is guaranteed from every answer sequence.

The CACM Professor Demo page is an illustration. Clearly distinguish it from evidence collected in an actual student session. Do not expose keys, private profile URLs or answers in slides.

## Short answers for viva questions

**What makes this agentic?** Each workflow observes the shared model, selects an activity using policies, invokes tools, evaluates submitted work and replans. Prompt routing alone is not the contribution.

**How do agents communicate?** Through the same cognitive model, engine and evidence history in one Python application. They are not separate networked agents.

**Why did refresh lose progress?** The original state was session-local. UUID-selected SQLite snapshots now restore both UI progress and underlying CACM/evidence, rather than just a dashboard total.

**Does passing evaluation prove better learning?** No. It verifies the specified software behavior using controlled fixtures. Educational impact needs a separate participant study.

**Is research output a systematic review?** No. It assists analysis of retrieved abstracts with source traceability; exhaustive search and full-text appraisal have not been established.

**Is code execution safe for public submissions?** The current subprocess runner is suitable only for trusted local use. Timeouts do not provide a security sandbox.
