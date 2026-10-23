# Web stages 3 and 4

FastAPI adapter: backend/main.py and backend/service.py. Reuses copied Python services; no JavaScript agent replacement. Independent database constrained to the new project. All copied app/ algorithms remain unchanged.

React TypeScript frontend: Vite, Tailwind v4, Radix UI primitives, Lucide icons, local Monaco Python editor, Markdown rendering without raw HTML. Home, unified workspace, inline specialized workflows, progress and professor view. Build uses npm.cmd on Windows because npm.ps1 is restricted by local execution policy.

Executed: separate Python venv creation and pip installation; npm.cmd install; FastAPI route import; npm.cmd run build. TypeScript and production build passed after updating Monaco export paths. Monaco is dynamically loaded; its editor bundle remains large. API and browser tests continue in stages 5-8. No credentials copied and no paid provider calls made.

Reference implementation documentation: https://fastapi.tiangolo.com/tutorial/request-files/ , https://vite.dev/guide/ , https://tailwindcss.com/docs/installation/using-vite .
