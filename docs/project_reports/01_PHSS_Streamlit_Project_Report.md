# CACM-PHSS: Original Streamlit Project
## Simple and detailed project report

Prepared: 21 October 2026
Project: C:\Users\DELL\OneDrive\Documents\PHSS_Git
Audience: Friends, classmates and project demonstration visitors

## 1. What is this project?

CACM-PHSS is a personalized study-support application. It brings three kinds of student help into one place: understanding a topic, practising programming and working with research papers.

PHSS means Personalized Hybrid Study System. CACM means Cross-Agent Cognitive Modeling. In simple words, the three specialist agents share one record of what the student has demonstrated through assessed work.

The application connects explanations, practice, feedback, research tools and saved progress. The next activity can use evidence collected during an earlier activity.

A short explanation for a friend is:

> I built a study assistant with three specialists. One helps you learn, one helps you code and one helps you understand research papers. They share your assessed progress, so the system can adapt its next activity.

This report describes the original Python and Streamlit application. The separate React/FastAPI application has its own report.

## 2. What problem does it try to solve?

Students often learn a concept in one place, practise code elsewhere and read papers in another tool. These tools usually do not share the student's learning record.

For example, a student may explain recursion correctly but still struggle to implement a recursive function. A lesson-only tool might assume that the topic is understood. A coding-only tool might know nothing about the earlier explanation.

PHSS connects these experiences. It brings assessed results together, identifies weak areas or disagreement and chooses a suitable follow-up. This is the project's purpose; improved learning outcomes have not yet been proved through a real-student study.

## 3. What was built in the Streamlit version?

The original application established the main Python system and a usable interface around it.

- Learning, Coding and Research agents with separate responsibilities.
- A shared CACM model for mastery estimates, confidence, misconceptions and conflicts.
- An orchestrator that selects activities from natural-language requests.
- A common Student View that displays actual activities on the same page.
- SQLite storage for saved progress and supported unfinished work.
- Advanced agent pages and professor demonstration facilities.
- Automated checks for services, persistence, interface behavior and failures.

An agent here is a specialist software component with decision rules and tools. It is not necessarily a separate computer or an independently running chatbot.

## 4. The three agents at a glance

| Agent | Main responsibility | Example request | Typical output |
| --- | --- | --- | --- |
| Learning | Help understand a topic | Teach me recursion | Lesson, resources, questions and feedback |
| Coding | Help practise or inspect Python | Give me coding practice on arrays | Exercise, tests, hints and code feedback |
| Research | Help work with academic sources | Find papers about agentic AI | Sources, analysis, comparisons and reports |

## 5. Learning Agent: its work in detail

### Personalized explanations

The Learning Agent reads the student's record for a topic. It considers assessed attempts, mastery estimates, confidence and possible misconceptions. Its existing policy chooses whether the student needs an explanation, practice, verification, remediation (focused help for a weak area) or a more advanced activity.

Gemini can generate the student-facing explanation from that context. The AI supplies educational content, while the Python decision and cognitive services control assessment evidence and state updates.

### Educational resources

Available resources can come from YouTube, Wikipedia and supported official documentation. Existing services rank resources using factors such as relevance, difficulty and quality information. Retrieval depends on external availability and provider configuration.

### Topic browsing and study planning

The topic bank contains 50 topics, and custom topic requests are also supported. The study planner considers prerequisites and assessed readiness. For example, it may suggest functions before a more advanced recursion topic.

Revision recommendations use the saved record and existing scheduling rules. These are project rules, not a scientifically calibrated model of forgetting.

### Adaptive practice

The Streamlit interface offers sessions of 5, 10, 15 or 20 questions. Questions are generated sequentially. Each response is evaluated before the next question or activity is chosen using the updated cognitive state.

A misconception is a possible misunderstanding, such as believing that recursion never needs a stopping condition. The system tracks evidence supporting or contradicting such a hypothesis and can direct follow-up learning toward it.

### Example learning procedure

1. The student asks, 'Teach me recursion.'
2. The system prepares a lesson and available resources.
3. The student starts adaptive practice.
4. The student answers a question about base cases.
5. The evaluator returns feedback and assessed performance.
6. CACM processes the evaluated response and saves the updated record.
7. The Learning Agent chooses the next suitable question or activity.

Reading a lesson or opening a resource does not increase mastery by itself.

## 6. Coding Agent: its work in detail

### Personalized practice

The Coding Agent reads the same shared model. It selects a recommended activity and difficulty using existing evidence. A less experienced student can receive easier practice, while a stronger assessed record can support more difficult work.

There are 18 curated exercises across six concepts, with different difficulty levels. Free-text Python topics are also supported through generated exercise packages.

### Checking generated exercise packages

For a custom topic, the provider can generate a task, starter code, a reference solution, behavioral tests and hints. Before accepting the package, the system checks its structure and runs its reference solution against the supplied tests.

This is useful validation, but generated tests may miss important cases. A generated reference solution and generated tests are not independent proof of correctness.

### Assessing original student code

The student writes a solution and submits it. Existing services inspect the code and run the exercise's tests in Python subprocesses. Semantic evaluation also contributes feedback and possible misconception information.

Only the assessed original submission is eligible to produce coding evidence for CACM. Identical completed submissions are recognised so they do not repeatedly increase attempts or mastery.

### Hints

The student can request up to three progressive hints. They provide stronger guidance in stages. Requesting a hint does not itself demonstrate understanding or update mastery.

### Reviewing a program that already exists

The Advanced Coding Agent has a 'Paste Code & AI Review' tab. A student can paste a Python program there and request explanations of possible mistakes and suggested fixes.

This general review is different from submitting a solution to a loaded exercise. A review does not automatically prove that a program is correct or update mastery.

The unified Streamlit coding path mainly opens the exercise workflow. The newer web version adds explicit review-mode routing from its common query box; that later change was kept separate from this original project.

### Corrections and verification

For an assessed exercise, the student can request guided review and test a proposed correction against the supplied exercise tests. The outcome can report passed tests, failed tests, a timeout or an unverified correction.

Passing supplied tests is not proof that code works for every possible input. AI-generated corrected code is never treated as evidence that the student independently solved the problem.

### Example coding procedure

1. Ask for a Python problem on recursion.
2. Read the exercise and edit the starter code.
3. Request a hint if needed.
4. Submit the original solution.
5. Inspect test results and assessment feedback.
6. Optionally request a separately checked correction.
7. Follow the updated recommendation for further practice.

Only Python execution is supported. The local runner has time limits but is not secure isolation for hostile code.

## 7. Research Agent: its work in detail

### Academic topic search

The agent can search for papers through the existing provider architecture, including OpenAlex. Results display actual available metadata: title, authors, year, abstract, DOI and source link.

Search supports configurable targets and additional pages. There is no fixed five-paper collection rule. Limits control processing, storage and provider use. A shortfall in valid papers is reported instead of inventing extra results.

### Saved research collections

Students can select individual search results and upload multiple PDFs. Collections belong to the selected profile and can recover after refresh or restart.

Duplicate checks avoid repeatedly storing the same source. Corrupted, unsupported or text-poor files keep appropriate failure or coverage information rather than fabricated analysis.

### Actual PDF analysis

The workflow extracts actual PDF text, divides it into manageable chunks and analyses selected chunks. A filename is not evidence of the paper's findings.

A supported statement keeps its source document and page/chunk information. This is called provenance: the reader can trace where a claim came from.

### Source coverage

A retrieved abstract is not the complete paper. Uploaded PDFs can provide full-text excerpts, but even those may have incomplete coverage. The application labels abstract-only analysis separately from analysed PDF excerpts.

If only an abstract was analysed, the system should not pretend it examined every experimental detail. Missing metadata, methods, datasets or findings stay unavailable rather than being invented.

### Comparison, synthesis and research suggestions

Available evidence can be organised into overviews, objectives, methods, datasets, evaluation information, findings and limitations. The system can compare reported methodologies and group source evidence by field.

This helps organise reading. It is not an exhaustive systematic review or proof of scientific consensus. Preliminary gaps and future directions are suggestions motivated by source limitations; they still need independent reading and feasibility checks.

### Reports and comprehension

The project retains Markdown export and can generate real Word documents. Selectable sections include paper details, overviews, objectives, methods, datasets/evaluation, comparisons, synthesis, similarities/differences, gaps, directions and limitations.

Research comprehension assessment is separate from content processing. Searching, uploading, analysing and exporting do not increase mastery. Only an evaluated student comprehension response can create research assessment evidence.

### Example research procedure

1. Search for papers on agentic AI in education.
2. Select useful results and save them.
3. Upload PDFs that you are allowed to use.
4. Extract and analyse selected sources in bounded batches.
5. Inspect supported claims and source locations.
6. Compare the reported methodologies and limitations.
7. Generate a report using the selected sources and sections.
8. Answer comprehension questions if you want assessed learning evidence.

## 8. CACM: the shared student record

CACM is common cognitive infrastructure, not a fourth content-generating agent.

| Information | Simple meaning |
| --- | --- |
| Concept | The topic being studied |
| Mastery estimate | The system's estimate of understanding |
| Confidence | How much assessed evidence supports that estimate |
| Attempts | Accepted evaluated activities for the topic |
| Misconceptions | Possible misunderstandings supported by evidence |
| Evidence source | Learning, coding or research assessment |
| Conflicts | Disagreement across assessed results from different agents |

The current cognitive model is rule-based. Defined rules combine assessed performance, evidence reliability and task difficulty. It has not learned each student's true ability from a large training dataset.

For example, a student might answer theory questions well but fail a related coding exercise. The engine can treat the disagreement as a reason to collect more evidence through a diagnostic question.

The evaluated diagnostic can support conflict resolution and new recommendations. Merely opening a diagnostic screen does not resolve a conflict.

## 9. How the agents communicate

The agents share a Python student model, evidence store and cognitive engine. They do not need to exchange chat messages.

```text
Student request
  -> Orchestrator selects an activity
  -> Relevant agent performs its work
  -> Student submits an answer or original code
  -> Evaluation produces evidence
  -> Shared CACM processes accepted evidence
  -> Next activity reads the updated record
  -> SQLite saves supported state
```

The cycle is Observe, Reason, Plan, Act, Evaluate, Update and Replan. In everyday language: look at the student's record, choose useful help, provide it, evaluate actual work and choose what happens next.

Gemini supplies semantic routing and generated content, while the Python policies and evidence rules remain important. The project is not just a chatbot prompt.

## 10. Student View and multi-step requests

The main experience starts with 'What would you like help with today?' The student enters a natural-language request and clicks Start without selecting an agent first.

The actual lesson, coding activity or research activity appears in the same Student View. A small caption identifies the current agent. Detailed internal information is kept in an optional Professor/Developer Debug expander.

'Teach me recursion and then give me coding practice' can produce an ordered sequence. The system prepares the active step, waits for student actions and prepares a later step using updated state.

The plan is bounded to up to three distinct activities for the router's shared topic. It is not unlimited autonomous planning. Advancing without assessment is recorded as a visit, not assessed success, and creates no mastery evidence.

Advanced agent pages, progress, topic browsing and professor demonstrations remain available.

## 11. Persistence and refresh recovery

Earlier information held only in Streamlit session memory could disappear when a session was lost. The current persistence layer saves supported state in SQLite at important checkpoints. SQLite stores a database in a local file.

The database is data/student_state/phss.sqlite3 inside PHSS_Git. The selected profile has a stable identifier, including through the student URL parameter.

Saved records include cognitive evidence, relevant progress, conflicts, supported assessment state and research collections. Completed assessment stages and receipt identifiers help prevent duplicate evidence updates after retries.

Recovery depends on retaining the correct database and selecting the same profile. Local profile identifiers provide continuity; they are not secure login accounts.

## 12. Interface and technology

Streamlit builds the page using Python. Button actions call the Python services directly.

| Part | Implementation |
| --- | --- |
| Interface | Streamlit, beginning at review_ui.py |
| Language and agents | Python modules under app/ |
| Shared cognitive model | app/cognitive/ |
| Orchestration | app/orchestrator/ |
| Storage and recovery | SQLite through app/persistence/ |
| Generated content and semantic work | Existing Gemini provider classes |
| Academic search | Existing providers including OpenAlex |
| PDF extraction and Word export | pypdf and python-docx |

The older separate Node/MongoDB prototype is not required to run this Streamlit application.

## 13. Development procedure followed

1. Inspected and retained the existing architecture.
2. Connected the three study workflows to shared cognitive services.
3. Added durable profiles, snapshots and recovery.
4. Kept content generation separate from assessed evidence.
5. Added recoverable assessment stages and duplicate prevention.
6. Extended research with PDF text extraction, provenance and mixed-source collections.
7. Added academic topic search and Word reports.
8. Extended coding with validated free-text Python exercise packages.
9. Connected shared policies, genuine conflict diagnostics and bounded sequences.
10. Refined Student View so real activities open inline and the active agent is identified.
11. Verified supported behavior with controlled offline and interface/browser checks.

This engineering procedure is different from conducting a learning-outcome study with real students.

## 14. How to run and demonstrate it

In a VS Code PowerShell terminal:

```powershell
cd "C:\Users\DELL\OneDrive\Documents\PHSS_Git"
python -B run_phss.py --check
python -B run_phss.py
```

Open http://127.0.0.1:8501 in a normal browser. Keep the server terminal running. Use the project's existing configured environment; this report does not ask you to recreate it.

Keep provider values private in this original project's environment or .env. Relevant variable names include GEMINI_API_KEY, YOUTUBE_API_KEY and OPENALEX_API_KEY. No real values belong in a shared report.

A short demonstration is: select a profile, request a lesson, answer a question, continue to coding, inspect updated state, search papers, analyse sources, export a report and refresh to show recovery.

For standalone review in this version, use Advanced Coding Agent -> Paste Code & AI Review. Use actual evaluated work for a live conflict example; separately seeded professor examples must be clearly labelled as demonstrations.

## 15. Recorded verification

A recorded original-project full offline run passed 67 of 67 selected cases. It recorded 202 unittest executions and 41 standalone script cases. Later targeted interface checks, including the agent caption, were recorded separately.

These checks exercise state changes, duplicate prevention, recovery, profile separation, coding behavior, source-grounded research, provider failures and interface actions.

These are earlier recorded results, not a new test run while writing this report. Source evidence includes data/evaluation/20261020T165311535966Z and the existing milestone/refinement reports.

Controlled provider fixtures support repeatable software checks. They do not prove live-provider quality, faster student learning or scientific mastery calibration.

## 16. Current limitations and future directions

- Mastery/confidence values are heuristic. No real-student study establishes learning gains or calibration.
- External generation and retrieval depend on provider availability and quality.
- Local profiles are not production authentication or authorization.
- Python execution has timeouts but is not a secure sandbox for untrusted code.
- Generated tests do not guarantee correctness for every input.
- PDF OCR is unavailable; analysis covers successfully processed excerpts.
- Search coverage is bounded and research suggestions need independent verification.
- Activity plans do not support arbitrary complex task graphs.

Future improvements could include secure accounts, isolated execution, accessibility testing, OCR, broader provider evaluation and an ethical student study. They are future directions, not completed claims.

## 17. Useful words and implementation references

| Word | Simple meaning |
| --- | --- |
| Agent | A specialist application component |
| Orchestrator | Coordinator that selects and orders activities |
| Adaptive | Changes the next activity using assessed progress |
| Evidence | Accepted result from evaluated student work |
| Persistence | Saving supported information for later recovery |
| Provenance | Source location supporting a research statement |
| Diagnostic | Focused assessment to investigate a difficulty/conflict |
| API key | A private value used to access a provider |

Main areas: review_ui.py, app/learning_agent/, app/coding_agent/, app/research_agent/, app/cognitive/, app/orchestrator/ and app/persistence/.

Supporting explanations: README.md, docs/ARCHITECTURE.md, docs/UNIFIED_STUDY_WORKSPACE.md, docs/METHODOLOGY.md and docs/LIMITATIONS.md.

## 18. A short explanation to say aloud

> My original project is a Streamlit-based personalized study system. Learning, Coding and Research agents use one shared cognitive model. A normal question opens the relevant activity. Evaluated answers and original code affect the saved record; just reading content does not. The main contribution is connecting the workflows, evidence, diagnostics and recovery in one working prototype.
