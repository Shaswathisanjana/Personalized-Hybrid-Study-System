# Open-topic Coding Agent (Phase 4)

The Advanced Coding Agent page retains its curated bank and accepts an optional
**What coding topic would you like to practise?** field. Nonblank text overrides
the bank selector. Exact existing CACM aliases are reused; other names are
normalized only by whitespace and case. Different algorithms are not guessed
to be the same concept.

## Local manual verification

1. Start `python -B run_phss.py` in the existing configured environment. Select
   a student profile and **Advanced Coding Agent / Personalized Practice**.
2. Leave the custom topic empty and load a curated exercise. This needs no
   generation provider and retains the existing 18 tasks across three levels.
3. Enter `merge sort`, `binary search trees` or `Python decorators`. Keep
   **Execution language: Python**, select 1–3 generation attempts, and click
   **Load Coding Exercise**. A configured Gemini key is needed for this live
   operation. Generation never changes mastery, confidence or attempts.
4. Inspect the description, input/output contract, constraints, examples,
   recommended difficulty and validation coverage statement. Successful
   packages have 3–8 distinct-input tests. A reference solution must pass all
   supplied tests; the unfinished starter and a constant-None probe must fail
   at least one. Failed packages are not published as verified exercises.
5. Ask for hints, edit code and refresh the same profile URL. The package,
   editor, hint history and progression should recover. Hints are assistance,
   not cognitive evidence. For custom topics, curated pattern-based
   misconception hints may be unavailable; the three generated hints remain.
6. Submit your original code. Examine the actual test results and semantic
   feedback. This evaluated submission may update CACM once. Resubmitting
   identical code for the same package reuses its assessment receipt.
   Custom topics appear in Cognitive Progress after coding evidence is recorded;
   genuine conflicts for them are also listed in the existing diagnostic tab.
7. After an assessment, click **Get Guided Review and Verify Correction**.
   Inspect the displayed correction status. A generated correction is tested
   against the loaded exercise's tests, and only labelled passed when those
   tests pass. Reviewing or executing a correction creates no mastery evidence.
8. Change the topic and make generation fail (for example with provider
   connectivity unavailable). The prior exercise and draft remain saved.
   Clear the custom topic and select its original bank topic to return to it.
   An interrupted generation is not silently restarted on refresh; explicitly
   click Load again. A fresh retry can make another provider request.
9. Select **SQL** for `SQL joins`: the UI states execution is unsupported and
   offers no generated exercise or submission action. JavaScript, Java and C++
   are also unsupported. Do not treat a Python exercise as a native SQL runtime.
10. Switch student profiles. The previous student's package, submissions,
    hints, review and custom-topic input must not appear in another profile.

## Bounds and interpretation

Generation reuses the existing Gemini client/model architecture. It allows
1–3 attempts (default 2), a 30-second HTTP timeout with SDK retries disabled,
6,500 output tokens, a 60,000-character package, a 160-character topic, up to
8 tests and 4,000 characters per test. Each reference, starter and probe test
uses the existing Python subprocess runner with a five-second wall-clock
timeout, including startup. Multiple tests and attempts can take several
minutes on a slow machine. HTTP timeout is the provider client's request
timeout, not an independent OS-enforced deadline for the whole generation job.

Only dependency-free Python functions with JSON-compatible inputs and return
values are supported for generated exercises. Imports and obvious host-access
operations are rejected before validation. These checks are **not a security
sandbox**. The local runner has the current user's filesystem/network rights
and no memory or output quota. Use this prototype only on a trusted local
machine; hostile generated or submitted code needs separately isolated
execution before deployment to other users.

Passing supplied tests proves agreement with those tests only. AI-generated
tests and reference solutions are not independent oracles. Topic relevance,
pedagogy, complexity requirements, boundary coverage and hint quality still
need review. The application does not claim these have been proven. A live
model may refuse a topic or fail validation; the curated bank remains available.

Saved profiles use the existing SQLite snapshots and optimistic concurrency.
An accepted package survives restart, while interrupted generation preserves
the previous package and requires explicit retry. Generation calls are not
exactly-once across a process crash. Profile IDs remain local identifiers,
not authentication. No environment, dependency or database schema change is
needed for this phase. Unified autonomous query routing is reserved for Phase 5.
