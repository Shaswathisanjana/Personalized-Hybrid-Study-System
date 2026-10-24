# Learning quiz topic isolation and difficulty labels

The web adapter previously returned the last practice_session regardless of the active lesson topic. An unfinished quiz then blocked practice for the new topic. The UI also omitted QuizQuestion.difficulty even though the adaptive policy supplied it.

Changes:
- backend/practice_context.py scopes visible practice to the active learning topic using the existing conservative concept identity rules. Switching topics saves the old quiz and feedback in a persisted per-topic cache, then restores the selected topic's saved work or starts it without a stale quiz. Same-topic unfinished practice resumes instead of being duplicated.
- backend/service.py binds topic practice on learning preparation/start, filters stale legacy sessions out of responses, clears feedback for newly generated practice and rejects stale question IDs from other activities before recording a pending assessment.
- app/persistence/session_recovery.py persists and validates the per-topic cache. Existing recursive ownership checks reject cross-student sessions. No cognitive policy or scoring changes.
- frontend/src/App.tsx shows the current question's actual topic and Easy/Medium/Hard difficulty. frontend/src/style.css supplies distinct difficulty badge colours.
- backend/tests/test_learning_topic_quiz.py adds six offline regressions for topic switching, cached restart recovery, difficulty metadata, feedback isolation, stale answers, same-topic reuse, legacy stale state and cross-profile ownership.
- frontend/e2e/learning-quiz.spec.ts verifies difficulty changes against actual backend questions, topic-specific quizzes, refresh recovery and resuming saved questions in Chrome.
- test_unified_query_refinement.py adds an explicit Arrays semantic response fixture for offline tests only. The production router is unchanged.
- WEB_FILES_CHANGED.json records the created files.

Executed verification:
- Production TypeScript/Vite build passed. Existing large-bundle warning remains.
- Complete backend suite: 58 passed, 1 existing Starlette deprecation warning, 34.15 seconds.
- Chrome topic/difficulty/refresh scenario: 1 passed, 10.5 seconds. Screenshot: data/web-e2e/screenshots/learning-topic-difficulty.png (synthetic offline profile).
- Existing offline test_student_persistence: 7 passed; test_persistence_streamlit: 8 passed. No skipped tests.
- Restarted the verified separate web servers on local ports 8000 and 8001.

Manual check: press Ctrl+F5. Ask Teach me recursion and start practice; the question displays its actual difficulty. Ask Teach me arrays; the old question and feedback should disappear. Start practice for Arrays and confirm the topic label. Refresh, then return to Recursion: its unfinished question resumes. Topic switching and viewing questions do not add mastery; only evaluated responses do. Pending evaluations still require recovery before navigating to another request. Saved quizzes are retained per topic, so returning to the same topic intentionally resumes its unfinished quiz.

No real-provider calls, original Streamlit changes, environment changes or student-data edits were used for this verification. The work is scoped to the phss-web-app branch.
