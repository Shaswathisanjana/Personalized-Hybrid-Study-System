# Separate agent buttons for faculty demonstrations

Added three labelled buttons across the existing student interface: Learning Agent, Coding Agent and Research Agent. Each opens a topic form using the existing semantic query/orchestration workflow. If that agent is the current activity, its button resumes the current workspace without starting another request. The research entry also offers Open my research collection.

The common query input, automatic agent selection, bounded multi-step plans, lessons/quizzes, coding exercise/editor/evaluation/review, research search/PDF/report tools, progress dashboard, persistence and professor page remain in place. Clicking an entry button alone does not evaluate answers, change mastery or replace the active saved plan. Starting a topic explicitly invokes the existing workflow. Entry buttons are disabled while an operation or interrupted assessment needs completion. No new backend router or generic chatbot was introduced.

Exact files:
- Modified frontend/src/App.tsx and frontend/src/style.css.
- Created frontend/e2e/agent-buttons.spec.ts and AGENT_BUTTONS_REPORT.md.
- Updated WEB_FILES_CHANGED.json inventory.
- Rebuilt ignored frontend/dist assets. Original Streamlit code, main branch and backend services were not changed.

Actual verification:
- Production TypeScript/Vite build passed; existing large editor-chunk warning remains.
- Chrome: 6 passed, 30.6 seconds. Direct agent buttons opened real learning/adaptive quiz, coding/editor, and research/search/PDF interfaces. A saved unanswered quiz survived switching through the three agents. Common input remained accessible. Other checks covered actual coding submission/review and saved drafts, learning topic/difficulty recovery, no unnecessary research downloads, research refresh, empty/populated progress and responsive layouts.
- No backend suite rerun was needed for these frontend-only changes; no claim is made that it was rerun.
- Provider boundaries used offline fixtures; no paid live request or real-student assessment was generated for testing.

Use: press Ctrl+F5 and click any of the three buttons at the top. Enter a topic and click Start Learning/Coding/Research activity. For saved PDFs click Research Agent then Open my research collection. If the agent is already active, its button resumes that activity. Overview and Study workspace retain the shared natural-language query box and automatic routing. Existing backend provider configuration and availability still govern live generation/search. Agent entry views are navigation state; a browser refresh restores the existing application landing page and persisted active workflow, which can be resumed through the matching agent button or Study workspace.
