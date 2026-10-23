# Unified study workspace

Start the existing environment with `python -B run_phss.py`, choose a local
profile and stay in **Student View**. The main query opens the actual activity
below it; advanced pages remain optional. No new environment or package is
required.

## Manual acceptance walkthrough

1. Enter `Teach me recursion, then give me coding practice, then find research papers`
   and click **Start**. Inspect the displayed sequence. Semantic routing chooses
   the relevant activities and their order; a local fallback handles common
   requests when semantic routing is temporarily unavailable. Configure existing
   provider keys privately for live generation and retrieval.
2. The learning activity prepares a personalized lesson and exposes the existing
   adaptive practice interface. Select a question count, answer questions and
   inspect feedback and cognitive progress. Content generation alone adds no
   assessment evidence.
3. Click **Continue to next activity**. Coding opens inline and automatically
   loads the current curated exercise or requests a bounded, validated Python
   package for a custom topic. Existing matching work is reused. Difficulty
   comes from current CACM, including evaluated learning work from the previous
   step. Submit your original code, inspect actual test results, ask for hints
   and optionally request a separately verified correction.
4. Refresh the same profile URL. The sequence position, package, code, hint
   progression, assessment receipts and supported activity state should recover.
   Resubmit identical code: attempts must not increment again.
5. Continue to research. With no existing saved search, one bounded OpenAlex page
   is requested automatically. Select individual results and add them to the
   persistent collection; request more pages explicitly if needed. Existing
   searches/selections are retained rather than silently replaced. Check the
   **Saved search topic** label before using older results; click **Search academic
   papers** to replace the search topic explicitly.
6. Upload multiple PDFs, retain abstract/full-text coverage labels, analyze a
   selected collection and generate selected Word report sections. PDF analysis
   retains page/chunk provenance. Existing Markdown export and comprehension
   practice remain available. Searches, uploads, analysis and exports do not
   increase mastery. Only an evaluated comprehension response can add research
   evidence.
7. If actual cross-agent assessments disagree, the sequence pauses progression
   and shows the existing diagnostic interface. Generate and answer the diagnostic
   question; only its genuine evaluated evidence can resolve the conflict. The
   next activity reads the updated shared state. No conflict is manufactured to
   demonstrate this in the normal UI.
8. You may advance without answering. The step is recorded as **visited without
   assessment**, not assessed completion. Advancing or finishing never creates
   mastery evidence. The final sequence table records this distinction.
9. Try a provider failure and refresh. Interrupted learning preparation requires
   **Retry learning preparation**; coding retains the explicit Load action and
   research retains retry/search controls. No interrupted generation is silently
   replayed on refresh. Successfully saved stages and assessments remain.
10. Switch profiles and return. The sequence and activities should remain scoped
    to the original profile. A profile URL is a local identifier, not a login.

For a coding-only request, try `Give me Python coding practice on binary search
trees`. For research alone, try `Find research papers about agentic AI for
personalized learning`. The advanced pages preserve their independent controls.

## Scope and interpretation

One saved query sequence contains up to three distinct activities for the shared
topic returned by the existing router. It is not a general dependency graph,
multi-topic task scheduler, or repeated-agent planner. More complex requests
may need separate queries; review the displayed topic/order before proceeding.
An explicit new learning request starts a new short-term practice activity;
switching to coding/research preserves the existing learning session.

The initial research query is bounded to one page with a default target of ten,
clamped to configured limits. More retrieval, paper selection, analysis and
assessment remain meaningful student actions. Existing valid work is reused,
not replaced for the sake of automatic execution. Provider calls are not
guaranteed exactly-once if a process crashes between response and checkpoint.

Only Python is supported for executed coding practice. The runner is still a
local subprocess with timeouts, not a hostile-code sandbox. Generated tests do
not independently prove algorithm correctness or teaching quality. Live routing,
generated content and educational effectiveness require separate evaluation.

## Reproducible checks

```powershell
python -B tools/evaluate_offline.py
python -B -m unittest tools.test_local_delivery tools.test_evaluate_offline
python -B tools/browser_workspace_smoke.py
```

The last command uses an existing Chrome/Edge executable and the already installed
`websockets` package. It starts an isolated Streamlit fixture server and separate
SQLite database, drives real browser inputs via DevTools, checks inline coding
assessment/reload and research retrieval, and records a screenshot/results under
ignored `data/browser_smoke/`. It installs nothing and calls no live providers.
Its browser may need OS execution permission outside a restricted sandbox.
It is an offline software smoke test, not live provider or educational evidence.
