# Cognitive Learning Agent

> An Agentic AI Learning Assistant with persistent Cognitive Memory that discovers, recommends, and continuously adapts real online learning materials based on a student's evolving cognitive state—**without fabricating educational content**.

---

## 🌟 Key Architecture & Philosophy

The agent strictly follows the principle of **content recommendation, not generation**:
- **Zero Content Fabrication:** The agent does not generate lessons or synthetic explanations. Instead, it discovers existing authoritative online resources (videos, interactive tutorials, official documentation, practice challenges, and visualizations) with direct validated URLs.
- **Cognitive Memory Isolation:** Cognitive state (mastery, confidence, misconceptions, prerequisites, learning history, and atomic evidence) is maintained separately from ordinary conversation history in a persistent SQLite database via SQLAlchemy.
- **Empirical Mastery Invariant:** The agent **never claims concept mastery without sufficient empirical evidence** (minimum 3 evidence items, verified assessment score $\ge 88\%$, and confidence $\ge 70\%$).
- **Multi-Modal Cognitive Engine:** Incorporates modular components:
  1. **Evidence Store:** Ingestion and retrieval of atomic learning observations (quiz scores, completion records, perceived difficulty, and self-ratings).
  2. **Mastery Engine:** Evidence-based Bayesian / EWMA updating of concept-wise mastery and confidence scores.
  3. **Misconception Manager:** Active diagnosis and tracking of conceptual misconceptions, automatically marked rectified upon successful remediation.
  4. **Conflict Detector and Resolver:** Identifies contradictions between self-claimed proficiency and observed performance, resolves them via calibrated confidence penalties.
  5. **Prerequisite DAG:** Graph traversal and topological sorting ensuring foundational concepts are satisfied before advanced topics.
  6. **Adaptive Re-planner:** Restructures the learning path dynamically based on learning feedback and cognitive signals.

---

## 📐 Component Architecture

```
User Input (Goal, Outcome, Knowledge Level, Format Preference)
               │
               ▼
       [ Learning Agent ]
               │
   ┌───────────┴──────────────────────────┐
   ▼                                      ▼
[ LLM Client ]                   [ Prerequisite DAG ]
- Goal Decomposition             - Topological Sorting
- Misconception Diagnosis        - Dependency Traversal
   │                                      │
   └──────────────────┬───────────────────┘
                      ▼
            [ Resource Discovery ]
            - DuckDuckGo Search (ddgs)
            - Link Validation (HEAD/GET 200 checks)
            - URL Deduplication & Normalization
            - Page Metadata Extraction (BS4 + Requests)
            - Semantic & Difficulty Ranker (Sentence Transformers)
                      │
                      ▼
           [ Recommended Learning Path ]
                      │
               (User Interaction)
                      ▼
         [ Assessment & Feedback Ingestion ]
                      │
                      ▼
             [ Cognitive Engine ]
   ┌──────────────────┼──────────────────┐
   ▼                  ▼                  ▼
[ Evidence Store ]  [ Conflict Resolver ]  [ Misconception Manager ]
(Atomic Evidence)   (Contradiction Check) (Gap & Fallacy Diagnosis)
   │                  │                  │
   └──────────────────┴─────────┬────────┘
                                ▼
                       [ Mastery Engine ]
                     (Bayesian / EWMA Update)
                                │
                                ▼
                      [ Agent Re-planner ]
                   (Dynamic Path Adaptation)
                                │
                                ▼
                   [ Persistent SQLite DB ]
                    (Cognitive State Models)
```

---

## 📂 Project Directory Structure

```
cognitive_learning_agent/
├── __init__.py
├── config.py                       # Configuration (Settings, DB URLs, thresholds)
├── cognitive_memory.db             # Persistent SQLite database
├── models/
│   ├── __init__.py
│   ├── schemas.py                  # Pydantic validation schemas
│   └── db_models.py                # SQLAlchemy ORM models
├── memory/
│   ├── __init__.py
│   ├── database.py                 # SQLite engine & session management
│   └── repository.py               # Cognitive Memory CRUD operations
├── cognitive_engine/
│   ├── __init__.py
│   ├── evidence_store.py           # Atomic observation store
│   ├── mastery_engine.py           # Bayesian/EWMA mastery & confidence updates
│   ├── misconception_manager.py    # Active & rectified misconception tracking
│   ├── conflict_detector.py        # Contradiction detection & resolution
│   ├── prerequisite_graph.py       # DAG prerequisite management
│   └── replanner.py                # Dynamic adaptive path re-planner
├── discovery/
│   ├── __init__.py
│   ├── searcher.py                 # DuckDuckGo Search discovery
│   ├── extractor.py                # Page extraction (Requests + BeautifulSoup)
│   ├── validator.py                # Link validation & URL deduplication
│   └── ranker.py                   # Semantic embeddings & difficulty ranker
├── llm/
│   ├── __init__.py
│   ├── client.py                   # Multi-provider LLM (Groq, Gemini, Heuristic)
│   └── prompts.py                  # Curriculum & diagnostic system prompts
├── core/
│   ├── __init__.py
│   └── agent.py                    # LearningAgent orchestrating 7-step loop
├── ui/
│   ├── __init__.py
│   └── app.py                      # Modern Streamlit UI dashboard
├── tests/
│   ├── __init__.py
│   ├── test_link_validation.py     # Link validator & deduplication tests
│   ├── test_resource_ranking.py    # Semantic ranking & format weighting tests
│   ├── test_cognitive_memory.py    # Persistent SQLite CRUD tests
│   ├── test_mastery_engine.py      # Bayesian mastery updates & invariant tests
│   ├── test_misconception_manager.py # Misconception detection & resolution tests
│   ├── test_conflict_resolver.py   # Contradiction detection tests
│   └── test_replanning.py          # Adaptive re-planning tests
├── run_cli.py                      # End-to-end CLI interactive demonstration
└── README.md                       # Complete documentation
```

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Core Agent** | Python 3.11 | Agent logic, planning, and coordination |
| **Interactive UI** | Streamlit | Responsive dashboard, progress metrics, and feedback console |
| **Web Search** | DuckDuckGo Search (`ddgs`) | Discover online tutorials, videos, and documentation |
| **Page Extraction** | Requests + BeautifulSoup4 | Extract real titles, descriptions, format, and read times |
| **LLM Reasoning** | Groq API / Google Gemini API | Goal decomposition into DAG and misconception diagnosis |
| **Cognitive Memory** | SQLite + SQLAlchemy 2.0 | Persist mastery, confidence, misconceptions, and evidence |
| **Embeddings** | Sentence Transformers | Semantic similarity between learning goals and resources |
| **Validation** | Pydantic V2 | Strict schema validation of learner states and resources |
| **Testing** | Pytest | Complete unit and integration test suite (16 tests) |

---

## 🚀 Setup & Execution Instructions

### 1. Environment Activation
Activate the designated Conda environment:
```powershell
conda activate D:\conda_envs\ai_env
```

### 2. Run Automated Pytest Suite
Run all unit and integration tests across link validation, semantic ranking, cognitive memory persistence, mastery calculation, misconception resolution, and adaptive re-planning:
```powershell
python -m pytest cognitive_learning_agent/tests -v
```

### 3. Run the End-to-End CLI Demonstration
Run the end-to-end command line demo showing initial goal parsing, discovery of online resources, evidence ingestion, and adaptive re-planning:
```powershell
python -u cognitive_learning_agent/run_cli.py
```

### 4. Launch the Streamlit Interactive Dashboard
Launch the web UI dashboard to interact with the agent visually:
```powershell
streamlit run cognitive_learning_agent/ui/app.py
```
*The Streamlit interface will open in your browser at `http://localhost:8501`.*

---

## 🔄 The 7-Step Learning Loop in Action

1. **Understand Goal:** Decomposes target learning goal into sequential concepts and dependencies.
2. **Assess Prior Knowledge:** Calibrates starting baseline with realistic confidence scores.
3. **Discover & Rank Resources:** Searches DuckDuckGo for live tutorials, videos, and documentation; validates HTTP 200 liveness; deduplicates canonical URLs; and ranks by semantic similarity.
4. **Recommend Learning Path:** Generates ordered path with direct clickable links, estimated reading/watch durations, and difficulty levels.
5. **Collect Learning Evidence:** Records atomic feedback on completion, quiz score, perceived difficulty, and learner notes.
6. **Update Cognitive Memory:**
   - Detects cognitive conflicts (e.g., claimed "Advanced" vs quiz failure).
   - Diagnoses active misconceptions.
   - Computes Bayesian mastery score and confidence.
7. **Replan Recommendations:**
   - Injects remedial prerequisite resources for identified stumbling blocks.
   - Adjusts difficulty and switches media formats (e.g., text to video).
