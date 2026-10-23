# CACM-PHSS: Separate Professional Web Application
## Simple and detailed project report

Prepared: 21 October 2026
Project: C:\Users\DELL\OneDrive\Documents\PHSS_Web_App
Audience: Friends, classmates and project demonstration visitors

## 1. What is this version?

PHSS_Web_App is a separate web application built around the existing CACM-PHSS Python services. It presents the study system through a React frontend and a FastAPI backend instead of using Streamlit as its primary interface.

PHSS means Personalized Hybrid Study System. CACM means Cross-Agent Cognitive Modeling: assessed information from different study activities is brought together in one student model.

The aim was to provide a modern educational website experience while reusing the actual learning, coding, research and cognitive services.

A short explanation for a friend is:

> After building the Python and Streamlit system, I created a separate web version. React builds the screens, FastAPI connects those screens to the existing Python services, and a shared cognitive model supports personalization.

This independent version has its own SQLite database (a local database file), Python environment and frontend dependencies. It was not installed over the original project.

## 2. Why create another version?

Streamlit is useful for quickly building a Python interface and demonstrating features. A React frontend gives more direct control over layout, reusable components, navigation and the code-editor experience.

The second version added presentation and API layers. It did not rewrite the agents in JavaScript or replace the system with a generic chatbot.

The applications share a starting design but are independent. Changes and student records do not automatically synchronise between them.

## 3. What was added in this version?

- A responsive React/TypeScript frontend built with Vite.
- A consistent interface using Tailwind CSS and Radix UI components.
- A FastAPI adapter around existing Python services.
- A student home page with one common question box and saved-progress information.
- A unified workspace displaying actual learning, coding and research activities.
- A Monaco editor for Python exercises and standalone code review.
- Profile-owned storage and refresh recovery in a separate SQLite database.
- A progress screen and a professor inspection screen.
- Loading, error, retry and recovery states.
- Direct review mode for pasted existing code, added after the initial web build.
- API and Chrome tests for the connected workflows.

The controls are not identical in every detail. For example, the current web practice API supports 1-10 questions, with a default of 3. Streamlit offers sessions of 5, 10, 15 or 20. This report describes the web application as implemented, not an exact copy of every Streamlit control.

## 4. Architecture in simple words

The frontend is what the student sees. The backend carries out the Python work. An API is the agreed way for those parts to exchange requests and results.

```text
Student in a browser
  -> React sends an API request
  -> FastAPI validates the request
  -> Existing orchestrator chooses the workflow
  -> Existing Python services do the work
  -> Evaluated student work can update CACM
  -> Independent SQLite storage saves supported state
  -> React displays the result
```

Clicking Start therefore does more than change a screen. The backend prepares the actual selected activity through the Python services.

The normal built version serves React files and the API from one FastAPI server. A separate Vite server is useful for frontend development but is not needed just to open the built application.

## 5. Technologies and their responsibilities

| Technology | Job in this project |
| --- | --- |
| React | Builds interactive student screens |
| TypeScript | Adds frontend type checking |
| Vite | Supports frontend development and production builds |
| Tailwind CSS | Supports interface styling |
| Radix UI | Supplies component primitives such as tabs and progress elements |
| Monaco | Provides the embedded code editor |
| FastAPI | Exposes Python operations as API endpoints |
| Uvicorn | Runs the FastAPI server |
| Existing Python services | Perform agent, orchestration and cognitive work |
| SQLite | Saves profiles, supported state and collections |
| Gemini and external sources | Supply generated content, semantic work and available resources |

Node.js and npm support frontend development/building. They do not perform the Python agents' work. The implemented component primitives are Radix-based; the project should not be presented as a completed installation of another UI library merely because it was considered during planning.

## 6. Main student-facing screens

### Student home

The home page includes the common question input, example requests, topic browsing, assessed-progress summaries, recent assessed activity where available and a way to continue a saved sequence.

A local profile selector determines whose records are shown. A new profile starts independently.

### Unified study workspace

The student types a natural-language request and clicks Start. The orchestrator selects a specialist, and the actual activity appears in the same workspace.

A label such as 'Handling this activity: Coding Agent' identifies the current specialist. The student does not need to choose an agent first.

### Progress

The progress screen displays recorded topics, assessed attempts, mastery/confidence estimates, evidence history and existing study-planning information. These come from stored records rather than decorative invented dashboard numbers.

### Professor view

The professor screen explains the architecture and shows the saved plan, shared-state observations and actual conflicts. It helps demonstrate connected decision-making.

A normal student's performance is not fabricated to create a convincing conflict example. Diagnostics become relevant when actual evaluated evidence disagrees.

## 7. Learning Agent in this version

### What was reused

The backend calls the existing learning runtime, content-generation services, resource recommendation, adaptive practice, progress tracker, study planner and cognitive infrastructure.

The agent still uses assessed information to select suitable help. React is a new presentation layer, not a new JavaScript learning algorithm.

### What the student can do

The student can ask for a lesson, read a personalized explanation and inspect available educational resources. Topic browsing provides another starting point.

The student can start adaptive practice, choose a supported question count, answer questions and inspect feedback. Saved question IDs and assessment records help prevent an identical completed answer from being applied again.

The underlying policy can recommend explanation, practice, verification, remediation (focused help for a weak area) or advancement. Misconception evidence can influence follow-up help. The existing study planner can consider prerequisites and revision needs.

### Example learning procedure

1. Ask, 'Teach me recursion.'
2. React sends the request to FastAPI.
3. The existing orchestrator selects learning.
4. The backend prepares an actual learning experience using shared state.
5. The page displays the lesson and available resources.
6. Start practice and submit an actual answer.
7. The evaluator and cognitive services process that response.
8. The next question or recommendation uses the updated record.
9. Supported progress is saved for recovery.

Reading a lesson, opening a screen or advancing without assessment is not proof of understanding and does not create mastery evidence.

## 8. Coding Agent: two different workflows

The new interface distinguishes practising a new exercise from checking a program that already exists.

### Workflow A: give me an exercise

A request such as 'Give me a coding problem on linked lists' selects the practice workflow. Existing policies choose a difficulty. The service loads a curated exercise or requests a validated package for a custom Python topic.

The page displays the problem, examples and Monaco editor. The student can edit the starter code, ask for progressive hints and submit their original solution.

The existing Python workflow runs supplied behavioral tests and evaluates the submission. Accepted original-code evidence can update CACM. Existing receipts prevent the same completed submission from adding duplicate evidence.

Guided review and verification can check a proposed correction against the loaded exercise's tests. Correction testing remains separate from assessed student evidence.

### Workflow B: check my existing code

A request containing Python code and a question such as 'Is this code correct?' can now select review mode instead of generating a replacement exercise.

This was an important later refinement. The initial web version selected the Coding Agent but still opened a practice problem. The fix introduced semantic review mode, a separate editor workflow and a persistent review draft.

The new review interface shows:

- The student's original source rather than replacement starter code.
- A field describing expected behavior or input/output.
- Deterministic Python syntax findings.
- AI explanations of supported issues, hints and suggested fixes.
- Suggested corrected code when supplied by the reviewer.
- Clear labels saying that no behavioral tests were run in standalone review.
- Saved drafts/results that recover after refresh and remain profile-specific.

Existing CodeReviewEngine, AICodeReviewer, GuidedCodeReviewCoordinator and CorrectionVerifier services are reused. The semantic router selects the kind of coding request; the frontend is not a replacement keyword router.

### What 'correct' means

Valid Python syntax does not mean that a program calculates the right answer. AI feedback can identify likely problems, but an untested correction is not verified execution.

Standalone review does not execute the pasted program. It does not invent tests and then claim the code passed them. If intended behavior is unclear, the student should add context.

An unchanged successful review can be reused. Editing code or context invalidates earlier feedback. Provider failures preserve the draft and allow an explicit retry.

### Two short request examples

Practice:

> Give me a Python coding problem on recursion.

Result: a task to solve, code editor, hints, submission and assessment feedback.

Review:

> Here is my Fibonacci program. Is it correct? Explain mistakes and suggest a correction.

Result: the original code, syntax inspection, AI feedback and a clearly labelled proposed correction.

Requesting a review does not increase mastery. AI-generated corrected code is not evidence that the student independently solved the problem.

## 9. Research Agent in this version

### Academic search

A request such as 'Find research papers about agentic AI' opens the actual search workflow. The student can set a topic and target, retrieve more results and select individual papers for the saved collection.

Available titles, authors, years, abstracts, DOI values and source links are displayed. Missing details are not invented. The page shows relevant limits, and there is no five-paper restriction.

The backend reuses the existing academic search session, provider parsing, source identity and duplicate-detection services.

### Multiple PDF uploads

Students can upload multiple PDFs into their own collection. Existing limits bound file size, total storage, pages, extracted text and batch processing.

The extractor reads actual PDF content in its existing worker process. Corrupted, unsupported and text-poor PDFs retain truthful status information. Image-only/scanned papers need OCR, which is not currently provided.

### Source-based analysis

The selected chunks are analysed through the existing quote-grounded services. Supported statements retain a source document and page/chunk location. Abstract-only results and full-text excerpts are labelled separately.

Successful chunks are retained when another chunk fails, so the interface does not have to pretend that an entire collection succeeded or restart everything unnecessarily.

### Comparison and synthesis

The application can present paper-level information, a methodology comparison table and grouped source evidence. Preliminary gaps and future research directions can be proposed from reported limitations.

This uses available supported fields and quotations. Matching wording does not prove scientific agreement; different wording does not automatically prove contradictory findings. Suggestions still require independent reading and feasibility checks.

### Reports and comprehension

The student can choose supported Word report sections and generate a real DOCX. Sections include sources/references, overviews, objectives, methods, datasets/evaluation, comparison, synthesis, similarities/differences, gaps, directions and coverage limitations.

Active collection selection determines the sources included. Source labels and provenance remain important. Markdown download is also available.

Research comprehension uses the existing assessment service. Searching, uploading, analysing and downloading a report do not change mastery. Only an evaluated student comprehension answer can contribute research evidence.

### Example research procedure

1. Ask for papers about a topic.
2. Choose a search target and inspect actual results.
3. Select useful results and add them to the collection.
4. Upload additional PDFs.
5. Extract and analyse selected batches.
6. Inspect claims and source locations.
7. Compare available methods and limitations.
8. Choose report sections and download Word or Markdown.
9. Answer a comprehension question if assessed research learning is desired.

## 10. CACM and communication between agents

CACM records topics, assessed attempts, mastery/confidence estimates, misconception hypotheses, evidence and conflicts. The three agents use that common record inside the new application.

They communicate through the shared Python model and cognitive engine, not by needing separate chatbot conversations.

For example:

1. A student answers recursion theory questions correctly.
2. The student later submits code that fails a related exercise.
3. Shared services can detect disagreement across evaluated results.
4. A diagnostic gathers further evidence.
5. Its assessed result can help resolve the conflict.
6. Later recommendations use the updated shared record.

The cognitive approach remains rule-based. Gemini helps with generation, routing and semantic evaluation, but existing Python evidence/update rules govern state changes. A mastery percentage is not a scientifically validated probability of ability.

## 11. Autonomous orchestration and multi-step requests

'Teach me recursion and then give me coding practice' can create an ordered saved plan. The system prepares the current activity and waits for student actions. When the student continues, later preparation reads updated shared state.

The cycle is Observe, Reason, Plan, Act, Evaluate, Update CACM and Replan. In ordinary words: inspect the record, decide what help is useful, provide it, evaluate actual work and decide what should happen next.

The existing sequence is bounded to distinct activities for a shared topic. It is not an unrestricted worker performing unlimited actions or silently completing the student's work.

A student may advance without submitting an assessment where allowed. That is a visit, not assessed success. Genuine unresolved conflicts block sequence advancement until the supported diagnostic flow addresses them.

## 12. Persistence and separation from Streamlit

The new database is data/student_state/phss.sqlite3 inside PHSS_Web_App. The original has a file with the same relative name inside PHSS_Git. They are different files in different folders and must not share the same writable database.

Records do not automatically move between the versions. The browser remembers the selected local profile, while the backend stores supported cognitive and workflow state.

Saved exercise drafts, review drafts, receipts and research collections can recover after refresh or restart. Coding uses explicit save controls. Unsubmitted text answers are not promised as saved work.

The API checks requests and relevant saved revisions. A stale write can receive a recoverable conflict instead of silently replacing newer work. The current design is for local use with one backend worker.

Local profiles support continuity, not production login or access control.

## 13. Development procedure followed

1. Verified the source folder and separate destination.
2. Copied relevant source while excluding credentials, original student data, private uploads, environments, Git metadata and generated artifacts.
3. Created the new application's own Python environment and frontend dependencies.
4. Added FastAPI adapters around existing services.
5. Built the React screens, styling and Monaco editor.
6. Connected common-query routing, preparation and continuation.
7. Integrated learning, coding, research, CACM, profiles and recovery.
8. Added offline API tests and Chrome tests using separate fixture data.
9. Corrected integration issues found during testing, including PDF-upload wiring and a refresh-read race.
10. Added standalone code review after pasted code was found to open a new exercise.
11. Rebuilt and tested the refinement and restarted the managed local server.

The original project was preserved. Some copied router/codec/adapter files were later extended for review mode and compatibility. It is accurate to say that services were reused and adapted; it is no longer accurate to say that every copied source file remains unchanged.

## 14. How to run and demonstrate it

In PowerShell:

```powershell
cd "C:\Users\DELL\OneDrive\Documents\PHSS_Web_App"
.\.venv\Scripts\python.exe -B -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Open http://127.0.0.1:8000 in Chrome, Brave or Edge. Keep the terminal running. The backend serves the built frontend; another frontend terminal is not needed for this normal mode.

Uvicorn does not automatically open a browser. From a second PowerShell terminal you can use:

```powershell
Start-Process "http://127.0.0.1:8000"
```

If port 8000 is already running, first try opening that address rather than starting another server. Frontend development is a different mode: npm.cmd --prefix frontend run dev starts Vite.

The new app reads its own .env in PHSS_Web_App. Configure private GEMINI_API_KEY, YOUTUBE_API_KEY and OPENALEX_API_KEY values as appropriate, then restart the backend. An .env in PHSS_Git is not the new app's .env. No real values belong in this report.

Suggested demonstration:

1. Select a local profile.
2. Request a lesson and submit a learning answer.
3. Request a coding exercise and inspect submission feedback.
4. Paste existing code and ask whether it is correct.
5. Add context, save the review draft and refresh.
6. Search literature and select multiple sources.
7. Upload PDFs, process batches and inspect provenance.
8. Download a report.
9. Show progress and professor observations.
10. Switch profiles to demonstrate separate records.

## 15. Recorded verification

The latest review refinement recorded 28 passing API tests and 8 passing Chrome scenarios. The API suite contains 18 existing tests and 10 new review-focused tests.

Browser scenarios cover landing/mobile layout, learning and refresh, coding editor/hints, seven-paper selection, multi-step continuation, PDF extraction/Word download, clarification and standalone review.

Existing targeted regressions also passed: 11 unified-query tests, 7 persistence tests and code-review engine/guided-review scripts. One guided-review run timed out before passing on an isolated retry; the timeout remains in the records.

The initial full copied regression run was 63/67 cases, with 202 unittest executions and 41 standalone script cases. All four initially failing cases later passed separately. That is different from claiming the original full run passed 67/67. The full set was not repeated for the later focused review fix.

The frontend passed TypeScript/build checks. Earlier real-browser startup checks confirmed that React and FastAPI could run together locally.

These are recorded results, not new application tests performed while writing this report. Offline provider fixtures make software checks repeatable; they are not real academic findings, live-provider validation or proof of educational effectiveness.

## 16. Comparison with the original project

| Area | Original Streamlit project | Separate web application |
| --- | --- | --- |
| Folder | PHSS_Git | PHSS_Web_App |
| Interface | Streamlit built with Python | React/TypeScript |
| Connection to services | Direct Python calls | FastAPI endpoints/adapters |
| Normal port | 8501 | 8000 |
| Main entry | run_phss.py | Uvicorn/FastAPI |
| Code editor | Streamlit coding controls | Monaco |
| Existing-code review | Advanced Paste Code & AI Review tab | Common query review mode and Check my code |
| Database | Inside PHSS_Git | Separate file inside PHSS_Web_App |
| Cognitive approach | Rule-based shared CACM | Reused rule-based shared CACM |
| Main contribution | Connected Python study prototype | New presentation/API layers and web integration |

A more polished interface does not automatically make the cognitive model more accurate. The second version changes access and presentation; it does not establish improved learning gains or mastery calibration.

## 17. Current limitations and future directions

- Live provider availability, costs and answer quality need separate evaluation.
- Mastery remains rule-based without a real-student calibration study.
- Local profiles are not production authentication or authorization.
- Python practice execution is local, with timeouts rather than secure hostile-code isolation.
- Standalone review does not execute pasted programs or prove untested corrections.
- Generated exercise tests do not cover every possible input.
- PDF OCR is unavailable and coverage is limited to successfully processed content.
- The application is local and single-worker, not a tested large-scale public service.
- The technical report records dependency advisories and a relatively large Monaco bundle.
- Changes and records do not automatically synchronise across the two projects.

Future work could include secure accounts, isolated execution, accessibility testing, broader live evaluation, OCR and an ethical student study. Those are possible improvements, not completed claims.

## 18. Useful words and implementation references

| Word | Simple meaning |
| --- | --- |
| Frontend | The screens the student sees |
| Backend | Python application carrying out requests |
| API | Defined way to exchange requests/results |
| Adapter | Connection between an existing service and a new interface |
| Build | Prepared frontend files delivered by the server |
| Monaco | The embedded code editor |
| Recovery | Restoring supported saved work |
| Provenance | Where a research statement came from |

Main areas: frontend/src/App.tsx, backend/main.py, backend/service.py, reused app/ modules and app/coding_agent/review_request.py.

Supporting records: WEB_APP_COMPLETION_REPORT.md, CODE_REVIEW_FIX_REPORT.md, docs/WEB_SETUP.md, data/code-review-api-results.xml and data/web-e2e/results.json.

## 19. A short explanation to say aloud

> My second version gives PHSS a React frontend and a FastAPI backend. The actual Learning, Coding, Research and CACM services stay in Python. One question box selects a real activity, including reviewing existing code rather than always generating practice. Supported records are saved in a separate database. It is a working local prototype with tested software behavior, not a production platform or a scientifically validated learning model.
