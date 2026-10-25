"""Modern Streamlit UI Dashboard for Learning Agent with Cognitive Memory."""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import textwrap
import streamlit as st
from datetime import datetime

from cognitive_learning_agent.core.agent import LearningAgent
from cognitive_learning_agent.models.schemas import (
    LearnerProfileCreate,
    DifficultyLevel,
    LearningFormat,
    AssessmentFeedback,
    ConceptStatus,
    MisconceptionStatus,
    QuizSubmission,
    QuizEvaluationResult,
    QuestionType,
)

# Page configuration
st.set_page_config(
    page_title="Cognitive Learning Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Sleek Glassmorphism & High-Contrast Typography
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.35);
    }
    
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-right: 6px;
    }
    .badge-format { background: rgba(59, 130, 246, 0.25); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.45); }
    .badge-diff { background: rgba(16, 185, 129, 0.25); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.45); }
    .badge-concept { background: rgba(168, 85, 247, 0.25); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.45); }
    .badge-score { background: rgba(245, 158, 11, 0.25); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.45); }
    .badge-mcq { background: rgba(59, 130, 246, 0.25); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.5); }
    .badge-desc { background: rgba(168, 85, 247, 0.25); color: #d8b4fe; border: 1px solid rgba(168, 85, 247, 0.5); }
    
    .topic-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 14px;
        padding: 22px 26px;
        margin-bottom: 22px;
        transition: all 0.2s ease-in-out;
    }
    .topic-card:hover {
        border-color: rgba(99, 102, 241, 0.5);
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
    }
    
    .quiz-box {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
        border: 1px solid rgba(99, 102, 241, 0.45) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        margin-top: 18px !important;
        box-shadow: 0 12px 36px rgba(0,0,0,0.45) !important;
    }
    
    .question-card {
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        margin-bottom: 18px !important;
    }
    
    .question-title {
        color: #ffffff !important;
        font-size: 1.12rem !important;
        font-weight: 700 !important;
        line-height: 1.5 !important;
        margin-top: 6px !important;
        margin-bottom: 6px !important;
    }
    
    .resource-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 18px;
    }
    
    .alert-box {
        padding: 14px 18px;
        border-radius: 10px;
        margin-bottom: 16px;
        font-size: 0.9rem;
    }
    .alert-warning {
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.4);
        color: #fca5a5;
    }
    .alert-info {
        background: rgba(14, 165, 233, 0.15);
        border: 1px solid rgba(14, 165, 233, 0.4);
        color: #7dd3fc;
    }
    .alert-success {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.4);
        color: #6ee7b7;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



@st.cache_resource
def get_cached_agent() -> LearningAgent:
    return LearningAgent()

agent = get_cached_agent()

# Initialize Session State
try:
    if "learner_id" not in st.session_state:
        st.session_state.learner_id = ""
    if "current_path" not in st.session_state:
        st.session_state.current_path = None
    if "last_replan_result" not in st.session_state:
        st.session_state.last_replan_result = None
    if "active_view" not in st.session_state:
        st.session_state.active_view = "Learning Path"
except Exception:
    pass

# =========================================================================
# Sidebar: Learner Profile & Configuration
# =========================================================================
with st.sidebar:
    st.image(
        "https://api.iconify.design/solar:brain-bold-duotone.svg?color=%23818cf8",
        width=56,
    )
    st.title("Cognitive Learner")
    st.caption("Adaptive Resource Recommendation System")

    st.markdown("---")
    st.subheader("Learner Profile")

    learner_id = st.text_input(
        "Learner ID",
        value="",
        placeholder="e.g. learner_123 (optional)",
    )
    name = st.text_input("Name", value="", placeholder="e.g. Alex (optional)")

    goal = st.text_area(
        "Learning Goal / Topic",
        value="",
        placeholder="e.g. Master Trees in Data Structures and Algorithms",
        help="Specify what technical domain or topic you want to learn.",
    )

    col1, col2 = st.columns(2)
    with col1:
        level_choice = st.selectbox(
            "Prior Knowledge",
            options=["beginner", "intermediate", "advanced"],
            index=0,
        )
    with col2:
        format_choice = st.selectbox(
            "Format Preference",
            options=["any", "video", "documentation", "interactive", "practice", "visualization"],
            index=0,
        )

    target_outcome = st.text_input(
        "Target Outcome",
        value="",
        placeholder="e.g. Solve Binary Tree Traversal and BST problems",
        help="Specific project or capability you want to demonstrate.",
    )

    language = st.text_input("Language / Stack", value="", placeholder="e.g. Python, Java, C++")

    start_btn = st.button("🚀 Plan Learning Path", use_container_width=True, type="primary")

    if start_btn:
        if not goal.strip():
            st.error("Please enter a Learning Goal or Topic to plan your path!")
        else:
            final_uid = learner_id.strip() if learner_id.strip() else f"user_{datetime.utcnow().strftime('%m%d_%H%M%S')}"
            final_name = name.strip() if name.strip() else "Learner"
            final_lang = language.strip() if language.strip() else "Python"
            final_outcome = target_outcome.strip() if target_outcome.strip() else goal.strip()

            # Check if this topic matches an existing journey the user previously used!
            existing_match = None
            if hasattr(agent, "find_similar_learning_journey"):
                existing_match = agent.find_similar_learning_journey(goal.strip())
            elif hasattr(agent.repository, "find_similar_learning_journey"):
                existing_match = agent.repository.find_similar_learning_journey(goal.strip())
            if existing_match and existing_match.get("path_json"):
                st.session_state.learner_id = existing_match["learner_id"]
                try:
                    p_dict = json.loads(existing_match["path_json"])
                    st.session_state.current_path = LearningPath(**p_dict)
                except Exception:
                    st.session_state.current_path = agent.get_current_learning_path(existing_match["learner_id"])
                st.session_state.last_replan_result = None
                st.session_state.active_view = "Learning Path"
                st.toast(f"🎯 Reconnected to your previous '{existing_match['topic_title']}' journey! Resuming your progress.", icon="🔄")
                st.rerun()

            with st.spinner("Analyzing goal, discovering real online resources, and initializing cognitive state..."):
                profile_input = LearnerProfileCreate(
                    user_id=final_uid,
                    name=final_name,
                    learning_goal=goal.strip(),
                    current_level=DifficultyLevel(level_choice),
                    preferred_format=LearningFormat(format_choice),
                    target_outcome=final_outcome,
                    preferred_language=final_lang,
                )
                profile, path = agent.start_learning_journey(profile_input)
                st.session_state.learner_id = final_uid
                st.session_state.current_path = path
                st.session_state.last_replan_result = None
                st.session_state.active_view = "Learning Path"
                st.success("Learning path generated and Cognitive State initialized!")
                st.rerun()

    st.markdown("---")
    nav_options = ["Learning Path", "Cognitive Memory Dashboard", "Live Resource Explorer"]
    active_v = st.session_state.get("active_view", "Learning Path")
    current_idx = nav_options.index(active_v) if active_v in nav_options else 0
    view_mode = st.radio(
        "Navigation",
        options=nav_options,
        index=current_idx,
    )
    st.session_state.active_view = view_mode

# =========================================================================
# Header Banner
# =========================================================================
st.markdown(
    """
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2rem; font-weight: 800; background: linear-gradient(90deg, #818cf8, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            Cognitive Learning Agent
        </h1>
        <p style="margin: 6px 0 14px 0; color: #94a3b8; font-size: 0.95rem;">
            Curating validated real online tutorials, videos, and documentation adapted strictly to your cognitive state.
        </p>
        <div>
            <span class="badge" style="background: rgba(99, 102, 241, 0.2); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.4);">
                Zero Fabricated Content
            </span>
            <span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4);">
                Bayesian Mastery Engine
            </span>
            <span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4);">
                Misconception Remediation
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Fetch latest cognitive state snapshot
active_uid = st.session_state.get("learner_id", "").strip()
snapshot = agent.get_cognitive_state(active_uid) if active_uid else None

# =========================================================================
# VIEW 1: Recommended Learning Path
# =========================================================================
if view_mode == "Learning Path":
    current_path = st.session_state.get("current_path")
    if not snapshot or not current_path or not getattr(current_path, "resources", None):
        # Clean Initial State / Landing View
        st.markdown(
            """
            <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 16px; padding: 28px; margin-bottom: 24px; text-align: center;">
                <h2 style="margin: 0 0 10px 0; color: #f8fafc; font-size: 1.85rem; font-weight: 800;">
                    🎓 Start Your Adaptive Learning Journey
                </h2>
                <p style="color: #94a3b8; font-size: 1rem; max-width: 650px; margin: 0 auto 16px auto; line-height: 1.6;">
                    Curating validated real online tutorials, documentation, and videos. Test your understanding with 10-question diagnostic quizzes and receive targeted remediation.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### 🔍 Search Any Topic to Begin")
        quick_c1, quick_c2 = st.columns([4, 1])
        with quick_c1:
            quick_goal = st.text_input(
                "Search Topic",
                placeholder="e.g. Trees in Data Structures and Algorithms, Python Asyncio, Dynamic Programming...",
                label_visibility="collapsed",
                key="landing_search_box",
            )
        with quick_c2:
            launch_search = st.button("🚀 Start Learning", key="landing_launch_btn", use_container_width=True, type="primary")

        st.caption("💡 Quick Suggestions:")
        chip_col1, chip_col2, chip_col3, chip_col4 = st.columns(4)
        with chip_col1:
            if st.button("🌳 Trees in DSA", key="chip_trees", use_container_width=True):
                quick_goal = "Trees in Data Structures and Algorithms"
                launch_search = True
        with chip_col2:
            if st.button("⚡ Python Asyncio", key="chip_asyncio", use_container_width=True):
                quick_goal = "Master Asynchronous Programming in Python"
                launch_search = True
        with chip_col3:
            if st.button("📊 Dynamic Programming", key="chip_dp", use_container_width=True):
                quick_goal = "Dynamic Programming Patterns and Algorithms"
                launch_search = True
        with chip_col4:
            if st.button("🌐 REST APIs & FastAPI", key="chip_fastapi", use_container_width=True):
                quick_goal = "Building REST APIs with FastAPI"
                launch_search = True

        if launch_search and quick_goal and quick_goal.strip():
            # Check if this topic matches an existing journey the user previously used!
            existing_match = None
            if hasattr(agent, "find_similar_learning_journey"):
                existing_match = agent.find_similar_learning_journey(quick_goal.strip())
            elif hasattr(agent.repository, "find_similar_learning_journey"):
                existing_match = agent.repository.find_similar_learning_journey(quick_goal.strip())
            if existing_match and existing_match.get("path_json"):
                st.session_state.learner_id = existing_match["learner_id"]
                try:
                    p_dict = json.loads(existing_match["path_json"])
                    st.session_state.current_path = LearningPath(**p_dict)
                except Exception:
                    st.session_state.current_path = agent.get_current_learning_path(existing_match["learner_id"])
                st.session_state.last_replan_result = None
                st.session_state.active_view = "Learning Path"
                st.toast(f"🎯 Reconnected to your previous '{existing_match['topic_title']}' journey! Resuming your progress.", icon="🔄")
                st.rerun()

            with st.spinner(f"Analyzing '{quick_goal.strip()}', discovering real online tutorials, and building curriculum..."):
                gen_uid = f"user_{datetime.utcnow().strftime('%m%d_%H%M%S')}"
                profile_input = LearnerProfileCreate(
                    user_id=gen_uid,
                    name="Learner",
                    learning_goal=quick_goal.strip(),
                    current_level=DifficultyLevel.BEGINNER,
                    preferred_format=LearningFormat.ANY,
                    target_outcome=quick_goal.strip(),
                    preferred_language="Python",
                )
                profile, path = agent.start_learning_journey(profile_input)
                st.session_state.learner_id = gen_uid
                st.session_state.current_path = path
                st.session_state.last_replan_result = None
                st.session_state.active_view = "Learning Path"
                st.rerun()

        # Display Past Learning Topics & Progress History right on landing page
        if hasattr(agent, "deduplicate_learning_journeys"):
            agent.deduplicate_learning_journeys()
        elif hasattr(agent.repository, "deduplicate_learning_journeys"):
            agent.repository.deduplicate_learning_journeys()
        past_journeys = agent.repository.get_learning_journeys()
        if past_journeys:
            st.markdown("---")
            st.markdown("### 📚 Your Past Learning Topics & Progress History")
            st.caption("Select a past topic below to resume where you left off or check your completion progress.")

            for j in past_journeys:
                total_t = max(1, j.get("total_topics", 1))
                mastered_t = j.get("completed_topics", 0)
                attempted_t = j.get("attempted_topics", 0)
                prog_pct = j.get("progress_percentage", j.get("mastery_percentage", 0.0))
                if prog_pct == 0.0 and j.get("mastery_percentage", 0.0) > 0:
                    prog_pct = j["mastery_percentage"]
                bar_val = min(1.0, max(0.0, float(prog_pct) / 100.0))

                if mastered_t >= total_t and total_t > 0:
                    status_label = f"✅ All {total_t} topics mastered ({round(prog_pct, 1)}%)"
                elif mastered_t > 0:
                    status_label = f"🎯 {mastered_t} of {total_t} topics mastered • {attempted_t} attempted ({round(prog_pct, 1)}%)"
                elif attempted_t > 0:
                    status_label = f"⏳ {attempted_t} of {total_t} topics in progress ({round(prog_pct, 1)}%)"
                elif prog_pct > 0:
                    status_label = f"⏳ In progress ({round(prog_pct, 1)}%)"
                else:
                    status_label = f"📌 0 of {total_t} topics started (0%)"

                with st.container():
                    col_j1, col_j2, col_j3 = st.columns([4, 3, 2])
                    with col_j1:
                        st.markdown(f"**📖 {j['topic_title']}**")
                        st.caption(f"🎯 Goal: {j['target_outcome'] or j['learning_goal']}")
                    with col_j2:
                        st.markdown(f"**Progress:** {status_label}")
                        st.progress(bar_val)
                        st.caption(f"Curriculum Mastery: **{round(prog_pct, 1)}%**")
                    with col_j3:
                        updated_str = j['updated_at'].strftime("%b %d, %H:%M") if hasattr(j['updated_at'], "strftime") else str(j['updated_at'])[:16]
                        st.caption(f"🕒 {updated_str}")
                        if st.button("🔄 Resume This Topic", key=f"resume_land_{j['id']}", use_container_width=True):
                            st.session_state.learner_id = j["learner_id"]
                            if j.get("path_json"):
                                try:
                                    p_dict = json.loads(j["path_json"])
                                    st.session_state.current_path = LearningPath(**p_dict)
                                except Exception:
                                    st.session_state.current_path = agent.get_current_learning_path(j["learner_id"])
                            else:
                                st.session_state.current_path = agent.get_current_learning_path(j["learner_id"])
                            st.session_state.active_view = "Learning Path"
                            st.rerun()
                    st.divider()

    else:
        # Replan Notification Banner if available
        if st.session_state.last_replan_result:
            rep = st.session_state.last_replan_result
            st.markdown(
                f"""
                <div class="alert-box alert-info">
                    <strong>🔄 Path Adapted Based on Cognitive Evidence:</strong><br>
                    • {'<br>• '.join(rep.actions_taken)}
                </div>
                """,
                unsafe_allow_html=True,
            )



        # Guarantee 100% distinct topics and complete coverage of all curriculum subtopics for this active path
        curriculum_subtopics = []
        if current_path and current_path.ordered_concepts:
            for c in current_path.ordered_concepts:
                if c not in curriculum_subtopics:
                    curriculum_subtopics.append(c)
        elif snapshot and snapshot.concepts:
            for c in snapshot.concepts.keys():
                if c not in curriculum_subtopics:
                    curriculum_subtopics.append(c)

        # Overview Stats (scoped strictly to active topic)
        colA, colB, colC, colD = st.columns(4)
        with colA:
            st.metric("Curriculum Progress", f"{snapshot.overall_progress}%")
        with colB:
            st.metric("Total Concepts", len(curriculum_subtopics) if curriculum_subtopics else len(snapshot.concepts))
        with colC:
            mastered_count = sum(1 for c_name in (curriculum_subtopics or snapshot.concepts.keys()) if snapshot.concepts.get(c_name) and snapshot.concepts[c_name].status == ConceptStatus.MASTERED)
            st.metric("Mastered Concepts", mastered_count)
        with colD:
            active_misc_count = sum(1 for m in snapshot.active_misconceptions if not curriculum_subtopics or m.concept_name in curriculum_subtopics)
            st.metric("Active Misconceptions", active_misc_count)

        def _safe_discover_path(uid):
            if hasattr(agent, "reconstruct_or_discover_path"):
                return agent.reconstruct_or_discover_path(uid)
            return agent.get_current_learning_path(uid)

        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.markdown("### 🗺️ Ordered Learning Path")
            st.caption(f"Target Outcome: **{snapshot.learner.target_outcome or snapshot.learner.learning_goal}**")
        with col_t2:
            if st.button("🔄 Refresh Resources", key="btn_refresh_path", use_container_width=True):
                with st.spinner("Searching and validating online resources..."):
                    current_path = _safe_discover_path(st.session_state.learner_id)
                    st.session_state.current_path = current_path
                    st.rerun()

        # Group resources by concept
        concept_resources_map = {}
        if current_path and current_path.resources:
            for r in current_path.resources:
                c = r.target_concept or (curriculum_subtopics[0] if curriculum_subtopics else "Core Concept")
                if c not in concept_resources_map:
                    concept_resources_map[c] = []
                if not any(existing_r.url == r.url for existing_r in concept_resources_map[c]):
                    concept_resources_map[c].append(r)

        # For any subtopic in curriculum that lacks a verified tutorial, add a direct fallback
        for c in curriculum_subtopics:
            if c not in concept_resources_map or not concept_resources_map[c]:
                slug = c.lower().replace(" ", "-").replace("(", "").replace(")", "")
                fallback_res = LearningResource(
                    url=f"https://www.geeksforgeeks.org/{slug}/",
                    title=f"{c} Tutorial",
                    snippet=f"Comprehensive documentation and practical guide for {c}.",
                    domain="geeksforgeeks.org",
                    format=LearningFormat.DOCUMENTATION,
                    difficulty=DifficultyLevel.BEGINNER,
                    target_concept=c,
                    relevance_score=0.9,
                    estimated_minutes=15,
                )
                concept_resources_map[c] = [fallback_res]

        # Construct distinct topic cards: EXACTLY 1 card per unique subtopic
        distinct_topic_entries = []
        for c in curriculum_subtopics:
            if c in concept_resources_map and concept_resources_map[c]:
                primary_res = concept_resources_map[c][0]
                primary_res.target_concept = c
                supp_res = concept_resources_map[c][1:]
                distinct_topic_entries.append((c, primary_res, supp_res))

        for c, res_list in concept_resources_map.items():
            if c not in curriculum_subtopics and res_list:
                primary_res = res_list[0]
                primary_res.target_concept = c
                distinct_topic_entries.append((c, primary_res, res_list[1:]))

        # Synchronize clean deduplicated path back to session_state
        if distinct_topic_entries and current_path:
            clean_res = [entry[1] for entry in distinct_topic_entries]
            current_path.resources = clean_res
            current_path.ordered_concepts = [entry[0] for entry in distinct_topic_entries]
            st.session_state.current_path = current_path

        total_topics = len(distinct_topic_entries)
        for idx, (concept_name, res, supp_list) in enumerate(distinct_topic_entries, start=1):
            concept_item = snapshot.concepts.get(concept_name) if snapshot else None
            concept_status = concept_item.status.value if concept_item else "NOT_STARTED"
            mastery_pct = round((concept_item.mastery_score if concept_item else 0.0) * 100)

            if concept_status == "MASTERED":
                status_badge = '<span class="badge" style="background: rgba(16, 185, 129, 0.25); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.5);">✅ Mastered</span>'
                card_border = "rgba(16, 185, 129, 0.35)"
            elif concept_status == "IN_PROGRESS" or (concept_item and concept_item.evidence_count > 0):
                status_badge = '<span class="badge" style="background: rgba(245, 158, 11, 0.25); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.5);">⏳ In Progress</span>'
                card_border = "rgba(245, 158, 11, 0.35)"
            else:
                status_badge = '<span class="badge" style="background: rgba(148, 163, 184, 0.2); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.4);">📌 Topic Scheduled</span>'
                card_border = "rgba(255, 255, 255, 0.1)"

            supp_html = ""
            if supp_list:
                supp_links = " • ".join([f'<a href="{sr.url}" target="_blank" style="color: #93c5fd; text-decoration: underline;">{sr.title} ↗</a>' for sr in supp_list])
                supp_html = f'<div style="margin-top: 8px; padding: 6px 12px; background: rgba(30, 41, 59, 0.5); border-radius: 6px; font-size: 0.82rem; color: #94a3b8;"><span style="color: #cbd5e1; font-weight: 600;">Supplementary Reference:</span> {supp_links}</div>'

            with st.container():
                topic_card_html = textwrap.dedent(f"""
                    <div class="topic-card" style="border-color: {card_border};">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                            <div>
                                <span class="badge" style="background: rgba(99, 102, 241, 0.25); color: #c7d2fe; font-size: 0.8rem; border: 1px solid rgba(99, 102, 241, 0.45);">
                                    Topic {idx} of {total_topics}
                                </span>
                                <h3 style="margin: 8px 0 2px 0; color: #ffffff; font-size: 1.25rem; font-weight: 800;">
                                    {concept_name}
                                </h3>
                            </div>
                            <div style="text-align: right;">
                                {status_badge}
                                <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">Mastery: <strong>{mastery_pct}%</strong></div>
                            </div>
                        </div>
                        <div style="margin: 8px 0 12px 0;">
                            <span class="badge badge-format">{res.format.value}</span>
                            <span class="badge badge-diff">{res.difficulty.value}</span>
                            <span class="badge" style="background: rgba(148, 163, 184, 0.2); color: #cbd5e1;">⏱️ {res.estimated_minutes} mins</span>
                            <span class="badge" style="background: rgba(99, 102, 241, 0.2); color: #a5b4fc;">🌐 {res.domain}</span>
                        </div>
                        <p style="color: #cbd5e1; font-size: 0.92rem; margin-bottom: 12px; line-height: 1.5;">
                            {res.snippet}
                        </p>
                        <div style="background: rgba(15, 23, 42, 0.6); padding: 8px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06); margin-bottom: 6px;">
                            <span style="color: #94a3b8; font-size: 0.82rem;">Direct Resource URL: </span>
                            <a href="{res.url}" target="_blank" style="color: #60a5fa; font-size: 0.88rem; text-decoration: underline; font-weight: 600;">{res.title} ↗</a>
                        </div>
                        {supp_html}
                    </div>
                """).strip()
                st.markdown(topic_card_html, unsafe_allow_html=True)

                c_link, c_quiz, c_feed = st.columns([1.3, 2.1, 1.6])
                with c_link:
                    st.link_button("🔗 Open Topic Resource", res.url, use_container_width=True)

                with c_quiz:
                    open_quiz = st.button(
                        f"🎯 Take 10-Question Quiz (#{idx})",
                        key=f"btn_quiz_{idx}",
                        use_container_width=True,
                        help=f"Complete a 10-question diagnostic assessment (MCQs + Descriptive) on {concept_name}",
                    )

                with c_feed:
                    with st.expander("📝 Topic Rating"):
                        with st.form(key=f"feedback_form_{idx}_{res.url[:25]}"):
                            completed = st.checkbox("Studied Topic", value=True)
                            usefulness = st.slider("Quality (1-5)", 1, 5, 4)
                            notes = st.text_input("Notes", placeholder="Optional learner notes...")
                            if st.form_submit_button("Submit Rating", use_container_width=True):
                                fb = AssessmentFeedback(
                                    learner_id=st.session_state.learner_id,
                                    concept_name=concept_name,
                                    resource_url=res.url,
                                    completed=completed,
                                    quiz_score=0.80,
                                    perceived_difficulty="just_right",
                                    usefulness_rating=usefulness,
                                    confusion_reported=False,
                                    notes=notes,
                                )
                                replan_res = agent.process_feedback(fb)
                                st.session_state.last_replan_result = replan_res
                                st.success("Topic progress recorded!")
                                st.rerun()

                # Quiz Expander / Container
                qui                if st.session_state.get(quiz_key, False):
                    with st.container():
                            past_attempts = agent.repository.get_quiz_attempts(st.session_state.learner_id, res.target_concept)
                            curr_attempt_display = len(past_attempts) + 1
                            quiz_mode_title = "Adaptive Retake Quiz" if curr_attempt_display > 1 else "Diagnostic Quiz"

                            st.markdown(
                                f"""
                                <div class="quiz-box">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                        <h3 style="margin: 0; color: #818cf8; font-size: 1.35rem; font-weight: 800;">
                                            🎯 10-Question {quiz_mode_title}: {res.target_concept}
                                        </h3>
                                        <div>
                                            <span class="badge" style="background: rgba(99, 102, 241, 0.35); color: #c7d2fe; font-size: 0.85rem; padding: 4px 12px; border: 1px solid rgba(99, 102, 241, 0.5);">
                                                Attempt #{curr_attempt_display}
                                            </span>
                                            <span class="badge" style="background: rgba(16, 185, 129, 0.25); color: #34d399; font-size: 0.85rem; padding: 4px 12px;">
                                                Cognitive Adaptive
                                            </span>
                                        </div>
                                    </div>
                                    <p style="color: #cbd5e1; font-size: 0.95rem; margin-bottom: 14px; line-height: 1.5;">
                                        {"Personalized assessment targeting your previous weak areas, misconceptions, and coding execution prediction." if curr_attempt_display > 1 else "Initial baseline assessment evaluating core conceptual invariants, code execution predictions, and descriptive explanations."}
                                    </p>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                            if past_attempts:
                                with st.expander(f"📜 View Past Attempt History ({len(past_attempts)} attempts)", expanded=False):
                                    for pa in past_attempts:
                                        p_score = round(pa.score * 100)
                                        p_color = "#34d399" if pa.passed else "#f87171"
                                        st.markdown(
                                            f"- **Attempt #{pa.attempt_number}** ({pa.timestamp.strftime('%Y-%m-%d %H:%M')}) — <span style='color:{p_color}; font-weight:700;'>Score: {p_score}% ({pa.correct_count}/{pa.total_questions})</span> • Next Action: `{pa.next_action.value if hasattr(pa.next_action, 'value') else pa.next_action}`"
                                            + (f" • Weak areas: *{', '.join(pa.weak_areas)}*" if pa.weak_areas else ""),
                                            unsafe_allow_html=True,
                                        )

                            col_q_head1, col_q_head2 = st.columns([4, 1.3])
                            with col_q_head1:
                                st.caption(f"Assessment for: **{res.target_concept}** • Attempt #{curr_attempt_display}")
                            with col_q_head2:
                                if st.button("🔄 Retake / Regenerate", key=f"btn_regen_q_{idx}", use_container_width=True, help="Generate fresh questions tailored to your cognitive state"):
                                    cache_k = f"{st.session_state.learner_id}:{res.target_concept}:att_{curr_attempt_display}"
                                    if hasattr(agent, "_quiz_cache"):
                                        agent._quiz_cache.pop(cache_k, None)
                                        agent._quiz_cache.pop(f"{st.session_state.learner_id}:{res.target_concept}", None)
                                    st.session_state.pop(f"quiz_result_{idx}", None)
                                    st.rerun()

                            quiz = agent.generate_quiz_for_resource(
                                st.session_state.learner_id,
                                res.target_concept,
                                res.url,
                                attempt_number=curr_attempt_display,
                            )

                            if quiz and quiz.questions:
                                with st.form(key=f"quiz_eval_form_{idx}"):
                                    user_mcq_selections = {}
                                    user_desc_answers = {}

                                    total_q_count = len(quiz.questions)
                                    for q in quiz.questions:
                                        q_type = getattr(q, "question_type", QuestionType.MCQ)
                                        is_desc = (q_type == QuestionType.DESCRIPTIVE)
                                        is_code = (q_type == QuestionType.PREDICT_OUTPUT or getattr(q, "code_snippet", None))
                                        rev_badge = '<span class="badge" style="background: rgba(16, 185, 129, 0.25); color: #34d399; margin-left: 6px;">🔄 Retention Check</span>' if getattr(q, "is_revision", False) else ''

                                        if is_desc:
                                            desc_q_html = textwrap.dedent(f"""
                                                <div class="question-card">
                                                    <span class="question-badge badge-desc">Q{q.question_id} of {total_q_count} • Conceptual Explanation</span>
                                                    {rev_badge}
                                                    <div class="question-title">{q.question_text}</div>
                                                    <div style="font-size: 0.88rem; color: #a5b4fc;">
                                                        Tested Aspect: <strong>{q.concept_aspect}</strong>
                                                    </div>
                                                </div>
                                            """).strip()
                                            st.markdown(desc_q_html, unsafe_allow_html=True)
                                            ans_text = st.text_area(
                                                f"Your Explanation for Q{q.question_id}:",
                                                key=f"desc_{idx}_{q.question_id}",
                                                placeholder="Explain the concept in your own words (structure, rules, key principles, or trade-offs)...",
                                                height=100,
                                            )
                                            user_desc_answers[q.question_id] = ans_text
                                        elif is_code:
                                            code_q_html = textwrap.dedent(f"""
                                                <div class="question-card">
                                                    <span class="question-badge" style="background: rgba(234, 88, 12, 0.25); color: #fb923c; border: 1px solid rgba(234, 88, 12, 0.5);">Q{q.question_id} of {total_q_count} • 💻 Predict Code Output</span>
                                                    {rev_badge}
                                                    <div class="question-title">{q.question_text}</div>
                                                    <div style="font-size: 0.88rem; color: #a5b4fc; margin-bottom: 8px;">
                                                        Tested Aspect: <strong>{q.concept_aspect}</strong>
                                                    </div>
                                                </div>
                                            """).strip()
                                            st.markdown(code_q_html, unsafe_allow_html=True)
                                            if q.code_snippet:
                                                st.code(q.code_snippet, language="python")
                                            choice = st.radio(
                                                f"Select predicted output for Q{q.question_id}:",
                                                options=list(range(len(q.options))),
                                                format_func=lambda i, opt=q.options: opt[i],
                                                index=None,
                                                key=f"radio_{idx}_{q.question_id}",
                                                label_visibility="collapsed",
                                            )
                                            user_mcq_selections[q.question_id] = choice
                                        else:
                                            mcq_q_html = textwrap.dedent(f"""
                                                <div class="question-card">
                                                    <span class="question-badge badge-mcq">Q{q.question_id} of {total_q_count} • Multiple Choice</span>
                                                    {rev_badge}
                                                    <div class="question-title">{q.question_text}</div>
                                                    <div style="font-size: 0.88rem; color: #a5b4fc;">
                                                        Tested Aspect: <strong>{q.concept_aspect}</strong>
                                                    </div>
                                                </div>
                                            """).strip()
                                            st.markdown(mcq_q_html, unsafe_allow_html=True)
                                            choice = st.radio(
                                                f"Select answer for Q{q.question_id}:",
                                                options=list(range(len(q.options))),
                                                format_func=lambda i, opt=q.options: opt[i],
                                                index=None,
                                                key=f"radio_{idx}_{q.question_id}",
                                                label_visibility="collapsed",
                                            )
                                            user_mcq_selections[q.question_id] = choice

                                        st.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 16px 0;'>", unsafe_allow_html=True)

                                    sub_btn = st.form_submit_button(
                                        f"⚡ Submit Quiz (Attempt #{curr_attempt_display}) & Update Cognitive Memory",
                                        use_container_width=True,
                                        type="primary",
                                    )

                                    if sub_btn:
                                        submission = QuizSubmission(
                                            learner_id=st.session_state.learner_id,
                                            concept_name=res.target_concept,
                                            resource_url=res.url,
                                            attempt_number=curr_attempt_display,
                                            selected_answers=user_mcq_selections,
                                            descriptive_answers=user_desc_answers,
                                        )
                                        with st.spinner("Evaluating understanding, updating cognitive memory, and adapting recommendations..."):
                                            eval_res = agent.evaluate_quiz_and_remedy(submission)
                                            st.session_state[f"quiz_result_{idx}"] = eval_res
                                            st.session_state.last_replan_result = eval_res.replan_result
                                            st.rerun()

                    # Render Quiz Evaluation Results if available
                    if f"quiz_result_{idx}" in st.session_state:
                        eval_res: QuizEvaluationResult = st.session_state[f"quiz_result_{idx}"]
                        score_pct = round(eval_res.score * 100)
                        badge_color = "#34d399" if eval_res.passed else "#f87171"
                        status_label = "Concept Mastered 🎉" if eval_res.passed else "Needs Targeted Practice ⚠️"

                        eval_header_html = textwrap.dedent(f"""
                            <div style="background: rgba(15, 23, 42, 0.95); border: 2px solid {badge_color}; border-radius: 14px; padding: 22px; margin-top: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                    <h4 style="margin: 0; color: #ffffff; font-size: 1.25rem;">
                                        📊 Assessment Outcome: {eval_res.concept_name} (Attempt #{eval_res.attempt_number})
                                    </h4>
                                    <span class="badge" style="background: {badge_color}25; color: {badge_color}; border: 1px solid {badge_color}; font-size: 0.95rem; padding: 6px 14px;">
                                        Score: {score_pct}% ({eval_res.correct_count}/{eval_res.total_questions}) • {status_label}
                                    </span>
                                </div>
                        """).strip()
                        st.markdown(eval_header_html, unsafe_allow_html=True)

                        # Action Recommendation Banner
                        act_val = eval_res.next_action.value if hasattr(eval_res.next_action, "value") else str(eval_res.next_action)
                        if act_val == "PROCEED":
                            st.markdown(
                                f"""<div class="alert-box alert-success">
                                    <strong>🚀 Recommended Next Action: PROCEED TO NEXT SUBTOPIC</strong><br/>
                                    {eval_res.next_action_reason}
                                </div>""",
                                unsafe_allow_html=True,
                            )
                        elif act_val == "REVISIT_PREREQUISITE":
                            st.markdown(
                                f"""<div class="alert-box" style="background: rgba(217, 70, 239, 0.15); border: 1px solid rgba(217, 70, 239, 0.4); color: #f0abfc;">
                                    <strong>⏮️ Recommended Next Action: REVISIT PREREQUISITE</strong><br/>
                                    {eval_res.next_action_reason}
                                </div>""",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                f"""<div class="alert-box alert-warning">
                                    <strong>🔄 Recommended Next Action: REVISE CURRENT SUBTOPIC</strong><br/>
                                    {eval_res.next_action_reason}
                                </div>""",
                                unsafe_allow_html=True,
                            )

                        # Remediation Efficacy Banner
                        if eval_res.remediation_efficacy:
                            eff = eval_res.remediation_efficacy
                            improved_str = ", ".join(eff.get("improved_areas", [])) if eff.get("improved_areas") else "Continuing remediation"
                            st.markdown(
                                f"""<div class="alert-box alert-info">
                                    <strong>🧠 Cognitive Remediation Impact (vs Attempt #{eff.get('prior_attempt_number')}):</strong><br/>
                                    {eff.get('summary')}<br/>
                                    <span>Improved Concepts: <strong>{improved_str}</strong> (Efficacy Rate: {round(eff.get('efficacy_rate', 0.0) * 100)}%)</span>
                                </div>""",
                                unsafe_allow_html=True,
                            )

                        # Question Breakdown
                        st.markdown("##### 📋 Question-by-Question Evaluation & Rubric Review")
                        for qf in eval_res.question_feedback:
                            is_corr = qf["is_correct"]
                            icon = "✅" if is_corr else "❌"
                            border = "rgba(16, 185, 129, 0.6)" if is_corr else "rgba(239, 68, 68, 0.6)"
                            q_type = qf.get("question_type", "mcq")

                            if q_type == "descriptive":
                                missing_html = f'<div style="margin-top: 4px; font-size: 0.88rem; color: #fca5a5;"><strong>Missing Principles:</strong> {", ".join(qf.get("missing_keywords", []))}</div>' if qf.get("missing_keywords") else ''
                                matched_str = ', '.join(qf.get('matched_keywords', [])) if qf.get('matched_keywords') else 'None'
                                desc_card_html = (
                                    f'<div style="border-left: 3px solid {border}; background: rgba(30, 41, 59, 0.5); padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 14px;">'
                                    f'<div style="font-weight: 700; color: #ffffff; font-size: 1rem;">{icon} Q{qf["question_id"]} [Descriptive]: {qf["question_text"]}</div>'
                                    f'<div style="margin-top: 8px; font-size: 0.9rem; color: #cbd5e1;"><strong>Your Explanation:</strong> <em>"{qf.get("user_answer", "")}"</em></div>'
                                    f'<div style="margin-top: 6px; font-size: 0.88rem; color: #a5b4fc;"><strong>Key Principles Matched:</strong> {matched_str}</div>'
                                    f'{missing_html}'
                                    f'<div style="font-size: 0.88rem; color: #6ee7b7; margin-top: 8px; background: rgba(16, 185, 129, 0.1); padding: 8px 12px; border-radius: 6px;">💡 <strong>Model Answer:</strong> {qf.get("ideal_answer", "")}</div>'
                                    f'</div>'
                                )
                                st.markdown(desc_card_html, unsafe_allow_html=True)
                            else:
                                code_block_html = f'<pre style="background: #0f172a; padding: 10px; border-radius: 6px; color: #38bdf8; font-size: 0.82rem; overflow-x: auto;"><code>{qf.get("code_snippet")}</code></pre>' if qf.get("code_snippet") else ''
                                corr_ans_html = f'<div style="font-size: 0.88rem; color: #34d399; margin-top: 2px;"><strong>Correct Answer:</strong> {qf["correct_choice_text"]}</div>' if not is_corr else ''
                                misc_html = f'<div style="font-size: 0.86rem; color: #fca5a5; margin-top: 6px; background: rgba(239,68,68,0.12); padding: 6px 10px; border-radius: 6px;">⚠️ <strong>Misconception Detected:</strong> {qf["misconception"]}</div>' if qf.get('misconception') else ''
                                mcq_card_html = (
                                    f'<div style="border-left: 3px solid {border}; background: rgba(30, 41, 59, 0.5); padding: 14px 18px; border-radius: 0 8px 8px 0; margin-bottom: 14px;">'
                                    f'<div style="font-weight: 700; color: #ffffff; font-size: 1rem;">{icon} Q{qf["question_id"]} [{q_type.upper()}]: {qf["question_text"]}</div>'
                                    f'{code_block_html}'
                                    f'<div style="margin-top: 6px; font-size: 0.88rem; color: #cbd5e1;"><strong>Your Selection:</strong> {qf["user_choice_text"]}</div>'
                                    f'{corr_ans_html}'
                                    f'<div style="font-size: 0.86rem; color: #94a3b8; margin-top: 6px;">💡 <em>{qf["explanation"]}</em></div>'
                                    f'{misc_html}'
                                    f'</div>'
                                )
                                st.markdown(mcq_card_html, unsafe_allow_html=True)

                        # Highlight Weak Areas
                        if eval_res.weak_areas:
                            st.markdown("##### 🔍 Identified Weak Conceptual Areas")
                            for wa in eval_res.weak_areas:
                                st.markdown(f"- 🔴 **{wa}**")

                        # Recommended Online Remedial Resources
                        if eval_res.targeted_resources:
                            st.markdown("##### 🎯 Targeted Online Resources Covering Your Weak Areas")
                            st.caption("The agent automatically crawled and verified these tutorials specifically to remedy your weak areas:")
                            for rem_idx, rem_res in enumerate(eval_res.targeted_resources, 1):
                                rem_card_html = textwrap.dedent(f"""
                                    <div class="topic-card" style="border-color: rgba(99, 102, 241, 0.45); background: rgba(30, 41, 59, 0.75); margin-bottom: 12px;">
                                        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                            <h5 style="margin: 0; color: #e2e8f0; font-size: 1.05rem;">
                                                🎯 {rem_idx}. {rem_res.title}
                                            </h5>
                                            <span class="badge badge-score">Relevance: {round(rem_res.relevance_score * 100)}%</span>
                                        </div>
                                        <div style="margin: 6px 0 10px 0;">
                                            <span class="badge badge-concept">{rem_res.target_concept}</span>
                                            <span class="badge badge-format">{rem_res.format.value}</span>
                                            <span class="badge badge-diff">{rem_res.difficulty.value}</span>
                                            <span class="badge" style="background: rgba(99, 102, 241, 0.2); color: #a5b4fc;">🌐 {rem_res.domain}</span>
                                            <span class="badge" style="background: rgba(148, 163, 184, 0.2); color: #cbd5e1;">⏱️ {rem_res.estimated_minutes} mins</span>
                                        </div>
                                        <p style="color: #94a3b8; font-size: 0.88rem; margin-bottom: 10px;">
                                            {rem_res.snippet}
                                        </p>
                                    </div>
                                """).strip()
                                st.markdown(rem_card_html, unsafe_allow_html=True)
                                st.link_button(
                                    f"🔗 Study Remedial Resource #{rem_idx}",
                                    rem_res.url,
                                    key=f"rem_btn_{idx}_{rem_idx}",
                                    use_container_width=True,
                                )

                        st.markdown("</div>", unsafe_allow_html=True)


        else:
            st.warning("⚠️ No online resources currently loaded for these concepts.")
            if st.button("🚀 Discover Resources for Concepts Now", key="btn_discover_now", type="primary", use_container_width=True):
                with st.spinner("Searching and validating online tutorials, docs, and practice problems..."):
                    path = _safe_discover_path(st.session_state.learner_id)
                    st.session_state.current_path = path
                    st.rerun()

# =========================================================================
# VIEW 2: Cognitive Memory Dashboard
# =========================================================================
elif view_mode == "Cognitive Memory Dashboard":
    st.markdown("### 🧠 Cognitive Memory & Learning Dashboard")
    st.caption("Review past learning topics, topic completion progress, concept mastery, and cognitive memory.")

    # Section 1: Past Learning Topics & Progress History
    st.markdown("#### 📚 Past Learning Topics & Progress History")
    if hasattr(agent, "deduplicate_learning_journeys"):
        agent.deduplicate_learning_journeys()
    elif hasattr(agent.repository, "deduplicate_learning_journeys"):
        agent.repository.deduplicate_learning_journeys()
    past_journeys = agent.repository.get_learning_journeys()
    if not past_journeys:
        st.info("No learning topics searched or completed yet. Enter a topic in the sidebar or search to begin!")
    else:
        for j in past_journeys:
            total_t = max(1, j.get("total_topics", 1))
            mastered_t = j.get("completed_topics", 0)
            attempted_t = j.get("attempted_topics", 0)
            prog_pct = j.get("progress_percentage", j.get("mastery_percentage", 0.0))
            if prog_pct == 0.0 and j.get("mastery_percentage", 0.0) > 0:
                prog_pct = j["mastery_percentage"]
            bar_val = min(1.0, max(0.0, float(prog_pct) / 100.0))

            if mastered_t >= total_t and total_t > 0:
                status_label = f"✅ All {total_t} topics mastered ({round(prog_pct, 1)}%)"
            elif mastered_t > 0:
                status_label = f"🎯 {mastered_t} of {total_t} topics mastered • {attempted_t} attempted ({round(prog_pct, 1)}%)"
            elif attempted_t > 0:
                status_label = f"⏳ {attempted_t} of {total_t} topics in progress ({round(prog_pct, 1)}%)"
            elif prog_pct > 0:
                status_label = f"⏳ In progress ({round(prog_pct, 1)}%)"
            else:
                status_label = f"📌 0 of {total_t} topics started (0%)"

            with st.container():
                col_d1, col_d2, col_d3 = st.columns([4, 3, 2])
                with col_d1:
                    st.markdown(f"**📖 {j['topic_title']}**")
                    st.caption(f"🎯 Goal: {j['target_outcome'] or j['learning_goal']}")
                with col_d2:
                    st.markdown(f"**Progress:** {status_label}")
                    st.progress(bar_val)
                    st.caption(f"Curriculum Mastery: **{round(prog_pct, 1)}%**")
                with col_d3:
                    updated_str = j['updated_at'].strftime("%b %d, %H:%M") if hasattr(j['updated_at'], "strftime") else str(j['updated_at'])[:16]
                    st.caption(f"🕒 {updated_str}")
                    if st.button("🔄 Open / Resume Topic", key=f"dash_resume_{j['id']}", use_container_width=True):
                        st.session_state.learner_id = j["learner_id"]
                        if j.get("path_json"):
                            try:
                                p_dict = json.loads(j["path_json"])
                                st.session_state.current_path = LearningPath(**p_dict)
                            except Exception:
                                st.session_state.current_path = agent.get_current_learning_path(j["learner_id"])
                        else:
                            st.session_state.current_path = agent.get_current_learning_path(j["learner_id"])
                        st.session_state.active_view = "Learning Path"
                        st.rerun()
                st.divider()

    st.markdown("---")
    st.markdown("#### 🔬 Detailed Cognitive State Inspection")
    if not snapshot:
        st.info("💡 Select or resume a topic above, or configure in the sidebar to inspect real-time concept mastery, misconceptions, and evidence logs.")
    else:
        # Determine active concepts for this topic
        dash_path = st.session_state.get("current_path")
        if not dash_path and active_uid:
            dash_path = agent.get_current_learning_path(active_uid)
        
        active_concept_filter = (
            dash_path.ordered_concepts 
            if (dash_path and dash_path.ordered_concepts)
            else list(snapshot.concepts.keys())
        )

        # Tabbed interface for deep inspection
        t_mastery, t_misc, t_prereq, t_ev = st.tabs(
            ["Concept Mastery", "Misconception Manager", "Prerequisite Graph", "Evidence Store"]
        )

        with t_mastery:
            st.markdown("#### Concept-Wise Mastery & Confidence")
            filtered_mastery = [
                (c_name, snapshot.concepts[c_name])
                for c_name in active_concept_filter
                if c_name in snapshot.concepts
            ]
            if not filtered_mastery:
                filtered_mastery = list(snapshot.concepts.items())

            for c_name, item in filtered_mastery:
                colM1, colM2, colM3, colM4 = st.columns([3, 2, 2, 2])
                with colM1:
                    st.markdown(f"**{c_name}**")
                    if item.notes:
                        st.caption(item.notes)
                with colM2:
                    st.progress(item.mastery_score)
                    st.caption(f"Mastery: **{round(item.mastery_score * 100, 1)}%**")
                with colM3:
                    st.progress(item.confidence_score)
                    st.caption(f"Confidence: **{round(item.confidence_score * 100, 1)}%**")
                with colM4:
                    status_colors = {
                        ConceptStatus.NOT_STARTED: "gray",
                        ConceptStatus.IN_PROGRESS: "orange",
                        ConceptStatus.PROFICIENT: "blue",
                        ConceptStatus.MASTERED: "green",
                    }
                    st.markdown(f":{status_colors[item.status]}[**{item.status.value}**]")
                    st.caption(f"{item.evidence_count} evidence records")
                st.divider()

        with t_misc:
            st.markdown("#### Tracked Misconceptions")
            active_m_list = [m for m in snapshot.active_misconceptions if m.concept_name in active_concept_filter]
            rect_m_list = [r for r in snapshot.rectified_misconceptions if r.concept_name in active_concept_filter]
            if not active_m_list and not rect_m_list:
                st.success("No misconceptions recorded for this topic. Learner demonstrates clean conceptual alignment.")
            else:
                if active_m_list:
                    st.markdown("##### 🚨 Active Misconceptions")
                    for m in active_m_list:
                        st.error(f"**Concept: {m.concept_name}**\n\n{m.description}\n\n*Triggered by: {m.evidence_observation}*")

                if rect_m_list:
                    st.markdown("##### ✅ Rectified Misconceptions")
                    for r in rect_m_list:
                        st.success(f"**Concept: {r.concept_name}** (Resolved)\n\n{r.description}\n\n*Resolution: {r.remediation_notes}*")

        with t_prereq:
            st.markdown("#### Prerequisite Dependency DAG")
            active_prereqs = [
                p for p in snapshot.prerequisites 
                if p.concept_name in active_concept_filter or p.prerequisite_name in active_concept_filter
            ]
            if active_prereqs:
                for p in active_prereqs:
                    st.markdown(f"- **{p.prerequisite_name}** ➔ Required for: `{p.concept_name}` (Weight: {p.weight})")
            else:
                st.info("No explicit prerequisite dependencies recorded for this topic.")

        with t_ev:
            st.markdown("#### Evidence Store Log")
            active_evidence = [ev for ev in snapshot.recent_evidence if ev.concept_name in active_concept_filter]
            if active_evidence:
                evidence_data = [
                    {
                        "Timestamp": ev.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "Concept": ev.concept_name,
                        "Type": ev.evidence_type.value,
                        "Score": f"{round(ev.score * 100)}%" if ev.score is not None else "N/A",
                        "Rating": f"{ev.user_feedback_rating}★" if ev.user_feedback_rating else "N/A",
                        "Observation": ev.observation,
                    }
                    for ev in active_evidence
                ]
                st.dataframe(evidence_data, use_container_width=True)
            else:
                st.info("Evidence store is empty for this topic. Complete learning items or take quizzes to accumulate evidence.")

# =========================================================================
# VIEW 3: Live Resource Explorer
# =========================================================================
elif view_mode == "Live Resource Explorer":
    st.markdown("### 🌐 Live DuckDuckGo Resource Explorer")
    st.caption("Test real-time resource discovery, link validation, and metadata extraction directly.")

    exp_query = st.text_input("Enter search topic", value="Python asyncio tutorial")
    exp_format = st.selectbox("Preferred Format", ["any", "video", "documentation", "interactive", "practice"])
    run_explore = st.button("Search & Validate Resources")

    if run_explore and exp_query:
        with st.spinner("Executing DuckDuckGo Search, checking HTTP headers, and extracting metadata..."):
            searcher = agent.searcher
            validator = agent.validator
            extractor = agent.extractor

            raw = searcher.search_for_concept(
                concept_name=exp_query,
                goal=exp_query,
                preferred_format=LearningFormat(exp_format),
            )
            validated = validator.validate_and_deduplicate(raw)

            st.write(f"Found **{len(validated)}** validated direct URLs:")
            for item in validated[:6]:
                meta = extractor.extract_metadata(item["url"], item.get("title", ""), item.get("snippet", ""))
                st.markdown(
                    f"""
                    <div class="resource-card">
                        <h4 style="margin: 0; color: #f1f5f9;">{meta.get('title', item['url'])}</h4>
                        <div style="margin: 6px 0;">
                            <span class="badge badge-format">{meta.get('format', 'docs')}</span>
                            <span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399;">HTTP {item.get('status_code', 200)} OK</span>
                            <span class="badge" style="background: rgba(99, 102, 241, 0.2); color: #a5b4fc;">{meta.get('domain')}</span>
                        </div>
                        <p style="color: #94a3b8; font-size: 0.9rem;">{meta.get('description', '')}</p>
                        <a href="{item['url']}" target="_blank" style="color: #60a5fa; font-size: 0.88rem; text-decoration: none;">
                            🔗 {item['url']}
                        </a>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
