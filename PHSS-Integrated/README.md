# PHSS Integrated — Learning, Coding and Research

This project integrates the supplied PHSS-Unified application with Smera's multi-agent routing contract and shared cognitive engine. Read SETUP.md first.

## What is connected

- A doubt bar in every React workspace routes natural-language requests to Learning, Coding, Research, or an ordered combination. Semantic routing uses the configured LLM; Smera's deterministic fallback is retained and extended for interview/debugging requests.
- The Coding Agent now answers questions and explains supplied code directly. Responses include suggested code and complexity where appropriate. Suggested code is not presented as executed or verified.
- Learning retains the original roadmap, saved journeys, resources, quizzes, remediation and progress. A routed learning response also gives a direct explanation. Existing roadmaps are resumed instead of duplicated.
- Research reports are passed into follow-up context. Use “Learn this topic” or the shared doubt bar to request an explanation, implementation plan or coding help. These handoffs support project work; they do not autonomously build and validate an entire research project.
- The original company/topic/difficulty interview catalogue and Pyodide workspace are embedded in the Coding tab. Routed topics prefill supported practice filters. The full workspace is also available at /coding/.
- All 26 executable built-in problems now have worked solutions and server-only verification cases. The external interview catalogue contains additional problems; not every external problem has executable tests. Its existing readiness labels are preserved.
- Offline coding remains available after its runtime and question pack have downloaded successfully. AI answers, resource discovery and paper retrieval require an internet connection.
- Each roadmap resource offers YouTube search and a generated lesson-video option. Original resource discovery can also return YouTube links. Video creation produces an AI-authored transcript and a real browser-rendered, captioned WebM (no audio), taking eight seconds per slide. It requires MediaRecorder/canvas capture support. This is a slide-based teaching video, not a photorealistic generated film.

## CACM monitoring

The shared panel replays the latest 500 persisted learning quiz records and latest 500 coding attempts through Smera's CognitiveEngine. Concept keys normalize case, underscores and hyphens. Quiz scores are calculated by the existing learning evaluator. Only server-verified coding results update shared CACM mastery. Browser-only coding attempts are visible as provisional evidence; the original coding workspace separately displays its local practice estimate and revision tasks.

Cross-agent disagreement raises a diagnostic recommendation. The orchestrator receives this cognitive context when answering. The panel can route weak concepts back to Learning. Merely opening a lesson, generating a video, or reading a paper supplies no mastery evidence. Cognitive values are heuristic educational estimates, not calibrated measures.

The original learning module retains its SQLite cognitive memory; MongoDB stores accounts, coding history, shared snapshots' source records and learning mirrors. They are not a single physical database. Use the same MongoDB URI/database for Node and Python. Do not reuse the original ZIP's private databases in a shared deployment.

## Source ownership

PHSS-Unified provides the application shell, authentication, roadmap and quiz pipeline, interview catalogue, offline runner and research pipeline. `backend-python/smera_app` contains namespaced Smera source. The live integration uses its QueryRouter fallback and CognitiveEngine; the old Streamlit orchestrator is retained as source, not launched as a second application. `app/orchestrator` adapts its semantic multi-agent contract to the unified web API, with Groq/Gemini support.

See VALIDATION.md for completed checks and limitations. No original .env values, private learning database, cached papers, node_modules or virtual environments are included in the distribution.
