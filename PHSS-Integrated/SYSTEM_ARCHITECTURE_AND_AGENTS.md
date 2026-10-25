# Integrated architecture

The browser uses a React interface and same-origin Express API. Express authenticates accounts, owns browser sessions, hosts the interview/offline coding workspace, and forwards AI requests to an internal FastAPI service using a shared service key. The browser never receives this key.

The FastAPI LangGraph coordinator classifies a request into an ordered list of Learning, Coding and Research operations. Each operation receives the current topic, bounded previous-workspace context, shared cognitive evidence and previous agent output. One agent's failure does not discard another agent's completed result.

Learning retains PHSS-Unified's resource discovery, roadmap, quizzes, saved journeys and remediation. Coding provides direct AI answers and retains the existing executable practice bank, company catalogue, Pyodide runner and optional Judge0 verification. Research retains the paper/PDF/evidence pipeline, including its existing dedicated background-job workspace.

Smera's cognitive engine is imported from smera_app. Shared CACM state is rebuilt from persisted MongoDB learning quizzes and coding results, with client-only attempts treated as provisional. The original learning engine also keeps its own SQLite memory; its learning progress and shared CACM are separately labeled in the interface.

The generated-video API creates a slide transcript. The browser renders captions into a canvas stream and records a downloadable WebM. No server-side arbitrary code execution or external generative-video service is introduced.

See README.md, SETUP.md and VALIDATION.md for behavior, limitations and configuration.
