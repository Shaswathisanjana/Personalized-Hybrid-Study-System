# Learning and Coding topic lists plus custom entry

Both ways to choose a topic are now available on the Learning/Coding agent entry screens AND within active workflows:
- Learning: the existing 50-topic catalogue grouped by subject, plus an editable custom topic field. In an active lesson open Choose another learning topic.
- Coding: 25 suggestions: six verified exercise topics and 19 explicitly grouped AI-generated topics, plus custom topic entry. In active coding practice open Choose a coding topic. Generated suggestions and unlisted topics use the existing bounded generation/validation workflow and may need provider availability or retries.

Choosing a dropdown option fills the editable field. Typing a topic not in the options resets the dropdown to its placeholder; the Start button uses the typed value. Empty or whitespace-only topics cannot start coding generation. Profile changes clear these temporary entry choices. New topics still use the existing query router and real agent services; no simplified router or replacement chatbot was introduced.

Unfinished learning quizzes, difficulty labels, saved coding drafts, actual submission/evaluation/review, research tools, report exports, common natural-language input, automatic routing, progress and three agent buttons remain intact. Browsing topics does not add mastery. Active topic chooser details remain collapsed until clicked.

Exact files:
Modified frontend/src/App.tsx, frontend/src/style.css and test_unified_query_refinement.py (offline semantic response fixtures only).
Created frontend/src/components/TopicFields.tsx, frontend/e2e/topic-options.spec.ts and TOPIC_OPTIONS_REPORT.md.
Updated WEB_FILES_CHANGED.json. Generated frontend/dist rebuilt and ignored. Original Streamlit project and production backend policies unchanged.

Actual verification:
- Final TypeScript/Vite build passed; the existing large editor-chunk warning remains.
- Complete backend suite: 66 passed, one existing Starlette deprecation warning, 39.96 seconds.
- Final Chrome browser run: 6 passed, 25.4 seconds. Covers dropdown and typed topic selection in entry/active Learning and Coding, a genuinely unlisted coding topic, blank-input rejection, refresh, existing three-agent buttons, saved quiz recovery, actual coding submission/review/draft switching, adaptive difficulty and lazy research loading.
- An initial new learning browser assertion matched both the activity and lesson headings. It was scoped to the activity heading, then all six browser scenarios were rerun successfully. No tests were skipped or timeouts loosened.
- The catalogue count was checked directly: 50 learning entries. Coding suggestions consist of the six real verified catalogue topics plus 19 generated-topic suggestions.
- Tests use deterministic provider fixtures, not paid live generation. Custom-topic acceptance and verification plumbing are tested, but no claim is made that every possible topic will generate successfully with a live provider.

Manual check: Ctrl+F5, then Learning Agent or Coding Agent. Choose a topic from the dropdown OR type a custom topic in the adjacent field, then Start. Once an activity is open, expand its topic chooser to find both options again. On returning to a current agent, its button resumes the activity, so use that active topic chooser rather than expecting the entry form to replace saved work. No backend restart is required for this UI update.
