import sys
from pathlib import Path

import streamlit as st


# =========================================================
# PROJECT IMPORT PATH
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.cognitive.models import StudentCognitiveModel
from app.orchestrator.orchestrator_runtime import OrchestratorRuntime
from app.learning_agent.topic_bank import LearningTopicBank
from app.learning_agent.progress_tracker import LearningProgressTracker
from app.persistence.assessment_recovery import apply_learning_outcome
from app.persistence.streamlit_state import (
    initialize_profiles, checkpoint, persistence_rerun, checkpoint_page,
    begin_assessment, finish_assessment,
)


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="CACM-PHSS",
    page_icon="ðŸŽ“",
    layout="wide",
)


# =========================================================
# SESSION STATE
# =========================================================

initialize_profiles(lambda engine: OrchestratorRuntime(cognitive_engine=engine))
# Preserve coding drafts when another application page hides their widgets.
# Profile loading above removes the previous owner's values before this runs.
for coding_draft_key in ("advanced_coding_editor", "advanced_coding_free_topic",
                         "advanced_coding_concept", "advanced_coding_language",
                         "advanced_coding_generation_attempts"):
    if coding_draft_key in st.session_state:
        st.session_state[coding_draft_key] = st.session_state[coding_draft_key]
from app.orchestrator.student_journey import StudentJourneyService, apply_navigation
apply_navigation(st.session_state)

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "last_query" not in st.session_state:
    st.session_state.last_query = ""

if "practice_session" not in st.session_state:
    st.session_state.practice_session = None

if "practice_feedback" not in st.session_state:
    st.session_state.practice_feedback = None

if "practice_summary" not in st.session_state:
    st.session_state.practice_summary = None

if "practice_concept" not in st.session_state:
    st.session_state.practice_concept = None

if "practice_context" not in st.session_state:
    st.session_state.practice_context = None

if "practice_last_outcome" not in st.session_state:
    st.session_state.practice_last_outcome = None

if "waiting_for_next_question" not in st.session_state:
    st.session_state.waiting_for_next_question = False

if "last_answered_question" not in st.session_state:
    st.session_state.last_answered_question = None

if "last_student_answer" not in st.session_state:
    st.session_state.last_student_answer = None

if "demo_resolved" not in st.session_state:
    st.session_state.demo_resolved = False


student = st.session_state.student
orchestrator = st.session_state.orchestrator


# =========================================================
# GENERAL HELPERS
# =========================================================

def clean_label(value):
    if value is None:
        return "Unknown"

    return str(value).replace("_", " ").title()


def reset_practice_state():
    """
    Reset only the current short-term practice session.

    The student's CACM cognitive model is intentionally
    preserved.
    """

    st.session_state.practice_session = None
    st.session_state.practice_feedback = None
    st.session_state.practice_summary = None
    st.session_state.practice_concept = None
    st.session_state.practice_context = None
    st.session_state.practice_last_outcome = None

    st.session_state.waiting_for_next_question = False
    st.session_state.last_answered_question = None
    st.session_state.last_student_answer = None


def reset_everything():
    """Restart activity while preserving the selected student's saved history."""
    from app.persistence.session_recovery import UI_KEYS, SERVICE_KEYS
    for key in list(st.session_state):
        if key in UI_KEYS | SERVICE_KEYS and key not in {"learning_goal", "_app_page"}:
            del st.session_state[key]
    st.session_state.demo_resolved = False


def clear_saved_student_progress():
    """Called only by the explicit, confirmed clear action in the sidebar."""
    from app.cognitive.cognitive_engine import CognitiveEngine
    reset_everything()
    st.session_state.pop("learning_goal", None)
    st.session_state.pop("_concept_identity_archive", None)
    st.session_state.student = StudentCognitiveModel(st.session_state['_persistence_id'])
    st.session_state.orchestrator = OrchestratorRuntime(cognitive_engine=CognitiveEngine())
    st.session_state.learning_progress_tracker = LearningProgressTracker()


# =========================================================
# RESOURCE DISPLAY
# =========================================================

from app.learning_agent.resources.format_filter import (
    RESOURCE_FORMATS,
    filter_ranked_resources,
)

def display_resource_recommendations(recommendation):
    """
    Display CACM-personalized learning resources.

    Students can filter by resource format.
    Each format initially displays up to three resources.
    View More reveals the remaining matching resources.

    Filtering does not change the original ranking scores.
    """

    if recommendation is None:
        return

    resources = getattr(recommendation, "resources", [])

    if not resources:
        st.info("No suitable external learning resources were returned.")
        return

    st.markdown("### Recommended Learning Resources")

    target_level = getattr(recommendation, "student_level", None)

    if target_level:
        st.caption(
            "CACM target resource level: "
            f"{clean_label(target_level)}"
        )

    concept_name = getattr(
        recommendation,
        "concept_name",
        "general",
    )

    format_key = (
        "learning_resource_format_"
        + str(concept_name)
    )

    selected_format = st.selectbox(
        "Choose resource format",
        options=RESOURCE_FORMATS,
        key=format_key,
    )

    filtered_resources = filter_ranked_resources(
        ranked_resources=resources,
        selected_format=selected_format,
    )

    display_key = (
        "learning_resources_expanded_"
        + str(concept_name)
        + "_"
        + selected_format.replace(" ", "_")
    )

    if display_key not in st.session_state:
        st.session_state[display_key] = False

    expanded = st.session_state[display_key]

    if not filtered_resources:
        st.info(
            f"No suitable {selected_format.lower()} "
            "were returned for this topic."
        )
        return

    visible_count = (
        len(filtered_resources)
        if expanded
        else min(3, len(filtered_resources))
    )

    st.caption(
        f"Showing {visible_count} of "
        f"{len(filtered_resources)} resources "
        f"in {selected_format}."
    )

    for index, ranked_resource in enumerate(
        filtered_resources[:visible_count],
        start=1,
    ):
        resource = getattr(
            ranked_resource,
            "resource",
            ranked_resource,
        )

        title = getattr(resource, "title", f"Resource {index}")
        url = getattr(resource, "url", "")
        source = getattr(resource, "source", "")
        difficulty = getattr(resource, "difficulty", "unknown")
        description = getattr(resource, "description", "")
        reason = getattr(ranked_resource, "reason", "")

        with st.container(border=True):
            st.markdown(f"#### {index}. {title}")

            col1, col2 = st.columns(2)

            with col1:
                st.write(
                    "**Estimated difficulty:**",
                    clean_label(difficulty),
                )

            with col2:
                if source:
                    st.write("**Source:**", source)

            if description:
                st.write(description)

            if reason:
                st.caption(f"Why recommended: {reason}")

            if url:
                st.link_button("Open Resource", url)

    if len(filtered_resources) > 3:
        if expanded:
            if st.button(
                "Show Less",
                key=display_key + "_collapse",
            ):
                st.session_state[display_key] = False
                persistence_rerun()
        else:
            remaining = len(filtered_resources) - 3

            if st.button(
                f"View More Resources ({remaining} more)",
                key=display_key + "_expand",
            ):
                st.session_state[display_key] = True
                persistence_rerun()

def display_cognitive_state(concept_name):
    """
    Display the current shared CACM cognitive state.
    """

    if not concept_name:
        return

    state = student.get_concept(
        concept_name
    )

    st.markdown(
        "## Current Learning State"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Estimated Mastery",
            f"{state.mastery * 100:.1f}%",
        )

    with col2:
        st.metric(
            "Confidence",
            f"{state.confidence * 100:.1f}%",
        )

    with col3:
        st.metric(
            "Evidence / Attempts",
            str(state.attempts),
        )

    st.caption(
        "Mastery and confidence are prototype CACM "
        "estimates. Experimental calibration remains "
        "part of the later evaluation stage."
    )


# =========================================================
# PRACTICE SUMMARY
# =========================================================

def display_practice_summary(summary):
    """
    Display the final result of a completed adaptive
    practice session.
    """

    if summary is None:
        return

    st.markdown(
        "## Practice Session Complete"
    )

    st.success(
        "You completed the adaptive practice session."
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Questions",
            summary.questions_completed,
        )

    with col2:
        st.metric(
            "Correct",
            summary.correct_answers,
        )

    with col3:
        st.metric(
            "Partially Correct",
            summary.partial_answers,
        )

    with col4:
        st.metric(
            "Incorrect",
            summary.incorrect_answers,
        )

    st.markdown(
        "### Session Performance"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Average Performance",
            f"{summary.average_performance * 100:.1f}%",
        )

    with col2:
        st.metric(
            "Estimated Mastery",
            f"{summary.final_mastery * 100:.1f}%",
        )

    with col3:
        st.metric(
            "Confidence",
            f"{summary.final_confidence * 100:.1f}%",
        )

    st.caption(
        "Average performance describes this practice "
        "session. It is separate from the CACM mastery "
        "estimate."
    )

    if summary.misconception_hypotheses:

        st.markdown(
            "### Possible Areas to Review"
        )

        for misconception in (
            summary.misconception_hypotheses
        ):
            st.write(
                f"- {misconception}"
            )

        st.caption(
            "These are evidence-based misconception "
            "hypotheses, not permanent labels."
        )

    else:

        st.success(
            "No misconception hypotheses were detected "
            "during this session."
        )

    next_activity = summary.next_activity

    if next_activity is not None:

        st.markdown(
            "### Recommended Next Step"
        )

        activity_type = getattr(
            next_activity,
            "activity_type",
            "learning activity",
        )

        difficulty = getattr(
            next_activity,
            "difficulty",
            "medium",
        )

        st.info(
            f"{clean_label(activity_type)} "
            f"({clean_label(difficulty)})"
        )

        content = getattr(
            next_activity,
            "content",
            "",
        )

        if content:

            with st.expander(
                "View recommended next activity"
            ):
                st.write(content)

    st.divider()

    if st.button(
        "Practice Again",
        key="practice_again",
        use_container_width=True,
    ):

        concept = (
            st.session_state.practice_concept
        )

        context = (
            st.session_state.practice_context
        )

        # Clear the previous practice session while
        # keeping the CACM student state.
        reset_practice_state()

        learning_runtime = (
            orchestrator.learning_runtime
        )

        with st.spinner(
            "Preparing a new adaptive practice session..."
        ):

            try:

                start = (
                    learning_runtime
                    .start_practice_session(
                        student=student,
                        concept_name=concept,
                        learning_context=context,
                        max_questions=st.session_state.get(
                            "selected_practice_question_count",
                            10,
                        ),
                    )
                )

                st.session_state.practice_session = (
                    start.session
                )

                st.session_state.practice_concept = (
                    concept
                )

                st.session_state.practice_context = (
                    context
                )

                persistence_rerun()

            except Exception as exc:

                st.error(
                    "A new practice session could not "
                    "be started."
                )

                with st.expander(
                    "Technical details"
                ):
                    st.exception(exc)


# =========================================================
# ADAPTIVE PRACTICE
# =========================================================

@checkpoint_page
def display_adaptive_practice(
    concept_name,
    learning_context,
):
    """
    Student-facing adaptive practice.

    Flow:

    Question
        ->
    Submit answer
        ->
    Evaluate answer
        ->
    Update CACM
        ->
    Generate adapted next question internally
        ->
    Show feedback + correct answer
        ->
    Student clicks Next Question
        ->
    Reveal next adaptive question
    """

    st.markdown(
        "## Adaptive Practice"
    )

    st.write(
        "Practice questions adapt to your answers and "
        "your current learning state."
    )

    session = (
        st.session_state.practice_session
    )

    summary = (
        st.session_state.practice_summary
    )

    # =====================================================
    # PRACTICE HAS NOT STARTED
    # =====================================================

    if session is None and summary is None:

        selected_question_count = st.selectbox(
            "Number of practice questions",
            options=[5, 10, 15, 20],
            index=1,
            key="selected_practice_question_count",
            help=(
                "Questions are generated sequentially. "
                "Each answer updates CACM before the next "
                "question is generated."
            ),
        )

        st.info(
            f"Ready for a {selected_question_count}-question "
            "adaptive practice session."
        )

        if st.button(
            "Start Adaptive Practice",
            type="primary",
            key="start_adaptive_practice",
            use_container_width=True,
        ):

            learning_runtime = (
                orchestrator.learning_runtime
            )

            with st.spinner(
                "Preparing your first question..."
            ):

                try:

                    start = (
                        learning_runtime
                        .start_practice_session(
                            student=student,
                            concept_name=concept_name,
                            learning_context=(
                                learning_context
                            ),
                            max_questions=selected_question_count,
                        )
                    )

                    st.session_state.practice_session = (
                        start.session
                    )

                    st.session_state.practice_concept = (
                        concept_name
                    )

                    st.session_state.practice_context = (
                        learning_context
                    )

                    st.session_state.practice_feedback = (
                        None
                    )

                    st.session_state.practice_summary = (
                        None
                    )

                    st.session_state.waiting_for_next_question = (
                        False
                    )

                    st.session_state.last_answered_question = (
                        None
                    )

                    st.session_state.last_student_answer = (
                        None
                    )

                    persistence_rerun()

                except Exception as exc:

                    st.error(
                        "The practice session could not "
                        "be started."
                    )

                    with st.expander(
                        "Technical details"
                    ):
                        st.exception(exc)

        return

    # =====================================================
    # ANSWER HAS BEEN SUBMITTED
    #
    # Do NOT show the next question yet.
    # First show feedback and the correct answer.
    # =====================================================

    if st.session_state.waiting_for_next_question:

        assessment = (
            st.session_state.practice_feedback
        )

        answered_question = (
            st.session_state.last_answered_question
        )

        student_answer = (
            st.session_state.last_student_answer
        )

        if (
            assessment is None
            or answered_question is None
        ):

            st.error(
                "Practice feedback is unavailable."
            )

            return

        evaluation = assessment.evaluation

        performance = (
            evaluation.performance
        )

        st.markdown(
            "## Answer Feedback"
        )

        # -------------------------------------------------
        # CORRECT / INCORRECT
        # -------------------------------------------------

        if performance >= 1.0:

            st.success(
                "Correct!"
            )

        elif performance <= 0.0:

            st.error(
                "Incorrect"
            )

        else:

            st.warning(
                "Partially Correct"
            )

        # -------------------------------------------------
        # STUDENT ANSWER
        # -------------------------------------------------

        with st.container(border=True):

            st.markdown(
                "#### Your Answer"
            )

            st.write(
                student_answer
            )

        # -------------------------------------------------
        # CORRECT ANSWER
        # -------------------------------------------------

        with st.container(border=True):

            st.markdown(
                "#### Correct Answer"
            )

            correct_answer = getattr(
                answered_question,
                "correct_answer",
                "",
            )

            if correct_answer:

                st.success(
                    correct_answer
                )

            else:

                st.caption(
                    "A reference answer is not "
                    "available for this question."
                )

        # -------------------------------------------------
        # EXPLANATION
        # -------------------------------------------------

        st.markdown(
            "#### Explanation"
        )

        feedback_text = getattr(
            evaluation,
            "feedback",
            "",
        )

        if feedback_text:

            st.info(
                feedback_text
            )

        question_explanation = getattr(
            answered_question,
            "explanation",
            "",
        )

        if question_explanation:

            if (
                question_explanation.strip()
                != feedback_text.strip()
            ):

                with st.expander(
                    "More explanation"
                ):

                    st.write(
                        question_explanation
                    )

        # -------------------------------------------------
        # MISCONCEPTION HYPOTHESES
        # -------------------------------------------------

        misconceptions = getattr(
            evaluation,
            "detected_misconceptions",
            [],
        )

        if misconceptions:

            with st.expander(
                "Learning point detected"
            ):

                st.write(
                    "The system detected a possible "
                    "area that may need reinforcement:"
                )

                for misconception in misconceptions:

                    st.write(
                        f"- {misconception}"
                    )

                st.caption(
                    "This is treated as a hypothesis "
                    "based on the current evidence, "
                    "not as a permanent label."
                )

        # -------------------------------------------------
        # UPDATED CACM STATE
        # -------------------------------------------------

        st.markdown(
            "### Updated Learning State"
        )

        state = student.get_concept(
            concept_name
        )

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Estimated Mastery",
                f"{state.mastery * 100:.1f}%",
            )

        with col2:

            st.metric(
                "Confidence",
                f"{state.confidence * 100:.1f}%",
            )

        st.caption(
            "These are prototype CACM estimates and "
            "require experimental calibration."
        )

        st.divider()

        # =================================================
        # FINAL QUESTION WAS ANSWERED
        # =================================================

        if summary is not None:

            st.info(
                "All practice questions are complete."
            )

            if st.button(
                "View Session Summary",
                type="primary",
                key="view_practice_summary",
                use_container_width=True,
            ):

                st.session_state.waiting_for_next_question = (
                    False
                )

                persistence_rerun()

            return

        # =================================================
        # THERE IS ANOTHER ADAPTIVE QUESTION
        # =================================================

        session = (
            st.session_state.practice_session
        )

        completed = (
            session.questions_completed
        )

        next_number = (
            completed + 1
        )

        if performance < 1.0:

            st.info(
                "The Learning Agent has used this "
                "answer to adapt the next question. "
                "The next question may focus on the "
                "area that needs reinforcement."
            )

        else:

            st.info(
                "The Learning Agent has used your "
                "updated CACM state to prepare the "
                "next question."
            )

        if st.button(
            f"Next Question "
            f"({next_number} of "
            f"{session.max_questions})",
            type="primary",
            key=f"next_question_{completed}",
            use_container_width=True,
        ):

            st.session_state.waiting_for_next_question = (
                False
            )

            st.session_state.practice_feedback = (
                None
            )

            st.session_state.last_answered_question = (
                None
            )

            st.session_state.last_student_answer = (
                None
            )

            persistence_rerun()

        return

    # =====================================================
    # SESSION FINISHED - SHOW SUMMARY
    # =====================================================

    if summary is not None:

        display_practice_summary(
            summary
        )

        return

    # =====================================================
    # ACTIVE QUESTION
    # =====================================================

    if session is None:
        return

    question = (
        session.current_question
    )

    if question is None:

        st.warning(
            "The practice session does not currently "
            "have an active question."
        )

        return

    question_number = (
        session.questions_completed + 1
    )

    total_questions = (
        session.max_questions
    )

    progress = (
        session.questions_completed
        / total_questions
    )

    st.progress(
        progress
    )

    st.markdown(
        f"### Question {question_number} "
        f"of {total_questions}"
    )

    st.caption(
        f"Difficulty: "
        f"{clean_label(question.difficulty)}"
    )

    with st.container(border=True):

        st.markdown(
            question.question
        )

    answer_key = (
        f"practice_answer_"
        f"{question_number}_"
        f"{session.questions_completed}"
    )

    answer = st.text_area(
        "Your answer",
        key=answer_key,
        placeholder=(
            "Type your answer here..."
        ),
        height=120,
    )

    submit_button = st.button(
        "Submit Answer",
        type="primary",
        key=(
            f"submit_practice_"
            f"{question_number}"
        ),
        use_container_width=True,
    )

    if submit_button:

        if not answer.strip():

            st.warning(
                "Please enter an answer before "
                "submitting."
            )

            return

        # IMPORTANT:
        #
        # Save the question before submitting.
        #
        # The backend may immediately replace
        # session.current_question with the next
        # adaptive question.
        answered_question = question

        student_answer = (
            answer.strip()
        )

        learning_runtime = (
            orchestrator.learning_runtime
        )

        with st.spinner(
            "Evaluating your answer and updating "
            "your learning state..."
        ):

            try:

                begin_assessment("learning", {"answer": student_answer, "question_id": answered_question.question_id})
                outcome = (
                    learning_runtime
                    .submit_practice_session_answer(
                        student=student,
                        session=session,
                        answer=student_answer,
                        question_id=answered_question.question_id,
                    )
                )

                apply_learning_outcome(st.session_state, outcome, student_answer)

                finish_assessment()
                persistence_rerun()

            except Exception as exc:

                st.error(
                    "The answer could not be processed."
                )

                with st.expander(
                    "Technical details"
                ):
                    st.exception(exc)


# =========================================================
# LEARNING AGENT OUTPUT
# =========================================================

def display_learning_output(
    output,
    concept_name,
    learning_context,
):
    """
    Display personalized Learning Agent content,
    recommendations and adaptive practice.
    """

    st.markdown(
        "### Your lesson"
    )

    st.caption(
        "Study the explanation, explore the resources and practise at your current level."
    )

    activity = getattr(
        output,
        "activity",
        None,
    )

    recommendations = getattr(
        output,
        "recommendations",
        None,
    )

    if activity is None:
        activity = output

    activity_type = getattr(
        activity,
        "activity_type",
        getattr(
            activity,
            "content_type",
            "learning activity",
        ),
    )

    difficulty = getattr(
        activity,
        "difficulty",
        "medium",
    )

    content = getattr(
        activity,
        "content",
        getattr(
            activity,
            "text",
            str(activity),
        ),
    )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Current Activity",
            clean_label(activity_type),
        )

    with col2:

        st.metric(
            "Difficulty",
            clean_label(difficulty),
        )

    st.markdown(
        "### Personalized Explanation"
    )

    st.info(
        content
    )

    display_resource_recommendations(
        recommendations
    )

    st.divider()

    display_adaptive_practice(
        concept_name=concept_name,
        learning_context=learning_context,
    )


# =========================================================
# RESEARCH AGENT OUTPUT
# =========================================================

def display_research_output(output):
    """
    Flexible renderer for the current Research Agent.
    """

    st.markdown(
        "### Research Agent"
    )

    answer = getattr(
        output,
        "answer",
        None,
    )

    if answer is None:
        answer = getattr(
            output,
            "synthesis",
            None,
        )

    if answer is None:
        answer = getattr(
            output,
            "response",
            None,
        )

    if answer:
        st.write(answer)

    papers = getattr(
        output,
        "papers_used",
        None,
    )

    if papers is None:
        papers = getattr(
            output,
            "papers",
            [],
        )

    if papers:

        st.markdown(
            "### Retrieved Academic Papers"
        )

        for index, paper in enumerate(
            papers,
            start=1,
        ):

            title = getattr(
                paper,
                "title",
                f"Paper {index}",
            )

            url = getattr(
                paper,
                "url",
                "",
            )

            if not url:
                url = getattr(
                    paper,
                    "paper_url",
                    "",
                )

            year = getattr(
                paper,
                "year",
                "",
            )

            with st.container(border=True):

                st.markdown(
                    f"**{index}. {title}**"
                )

                if year:
                    st.caption(
                        f"Year: {year}"
                    )

                if url:
                    st.link_button(
                        "Open Paper",
                        url,
                    )

    if not answer and not papers:
        st.write(output)


# =========================================================
# CODING AGENT OUTPUT
# =========================================================

def display_coding_output(output):
    """
    Flexible renderer for the current Coding Agent.
    """

    st.markdown(
        "### Coding Agent"
    )

    task = getattr(
        output,
        "task",
        None,
    )

    if task is None:
        task = getattr(
            output,
            "coding_task",
            None,
        )

    if task is not None:

        title = getattr(
            task,
            "title",
            "Coding Task",
        )

        description = getattr(
            task,
            "description",
            str(task),
        )

        difficulty = getattr(
            task,
            "difficulty",
            None,
        )

        st.markdown(
            f"#### {title}"
        )

        if difficulty:

            st.caption(
                f"Difficulty: "
                f"{clean_label(difficulty)}"
            )

        st.write(
            description
        )

    else:

        st.write(
            output
        )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title(
        "CACM-PHSS"
    )

    st.caption(
        "Cross-Agent Cognitive Modeling for "
        "Personalized Hybrid Study Systems"
    )

    st.divider()

    with st.expander("Professor/Developer Debug", expanded=False):
        page = st.radio(
            "Navigation",
            ["Student View", "Advanced Research Agent", "Advanced Coding Agent",
             "CACM Professor Demo", "System Architecture"],
            key="_app_page",
        )

    st.divider()

    with st.expander("Professor/Developer Debug — status", expanded=False):
        st.markdown(
            "### Prototype Status"
        )

        st.success(
            "Learning Agent"
        )

        st.success(
            "Research Agent"
        )

        st.success(
            "Coding Agent"
        )

        st.success(
            "Query Router"
        )

        st.success(
            "Multi-Agent Orchestrator"
        )

        st.success(
            "Shared Cognitive Model"
        )

        st.success(
            "Conflict Detection"
        )

        st.success(
            "Diagnostic Resolution"
        )

        st.info(
            "Current version is a functional research "
            "prototype. Experimental evaluation and "
            "calibration remain ongoing."
        )

    st.divider()

    if st.button(
        "Restart Current Activity",
        use_container_width=True,
    ):

        reset_everything()

        persistence_rerun()

    with st.expander("Clear this student's saved progress"):
        st.caption("This resets current progress. Archived migration backups are retained for recovery.")
        confirm_clear = st.checkbox("I understand this clears this profile's learning history")
        if st.button("Clear saved progress", disabled=not confirm_clear):
            clear_saved_student_progress()
            persistence_rerun()


# =========================================================
# STUDENT VIEW
# =========================================================

if page == "Student View":

    st.title(
        "Personalized Study Assistant"
    )

    st.write(
        "Ask for a lesson, coding practice, research papers or a sequence of activities. "
        "Your assessed work personalizes what comes next."
    )

    st.markdown(
        """
**Example requests**

- Teach me recursion in Python from basics
- Find research papers about transformers
- Give me a Python coding problem on binary search
- Teach me linked lists and give me coding practice
        """
    )

    # =====================================================
    # STUDENT LEARNING PROGRESS
    # =====================================================

    query = st.text_input(
        "What would you like help with today?",
        placeholder=(
            "Example: Teach me recursion in Python "
            "from basics"
        ),
        key="learning_request_input",
        max_chars=2000,
    )

    start_button = st.button(
        "Start",
        type="primary",
        use_container_width=True,
    )

    if start_button:

        if not query.strip():

            st.warning(
                "Please enter what you would like "
                "to study."
            )

        else:

            with st.spinner(
                "Preparing your study activities..."
            ):

                try:
                    from app.orchestrator.query_router import clarified_request
                    routed_query = clarified_request(query, st.session_state.get("journey_clarification"), student.user_id)

                    result = (
                        StudentJourneyService(student, orchestrator).handle_request(
                            routed_query, defer_workflows=True,
                        )
                    )

                    from app.orchestrator.study_workspace import start_workspace
                    start_workspace(st.session_state, result)
                    st.session_state.pop("journey_clarification", None)
                    if "learning" in result.route.selected_agents:
                        reset_practice_state()
                    st.session_state.last_result = result
                    st.session_state.last_query = query.strip()
                    st.session_state.journey_topic = result.route.concept
                    st.session_state.journey_topic_draft = result.route.concept

                    # Record a learning topic only when the
                    # Learning Agent successfully produced
                    # its response. Merely browsing a topic
                    # does not count as starting learning.
                    learning_succeeded = any(
                        agent_result.agent == "learning"
                        and agent_result.success
                        and not (isinstance(agent_result.output, dict) and agent_result.output.get("kind") == "study_workflow")
                        for agent_result in result.agent_results
                    )

                    if learning_succeeded:
                        st.session_state.learning_progress_tracker.start_topic(
                            user_id=student.user_id,
                            topic_name=result.route.concept,
                        )

                    persistence_rerun()

                except Exception as exc:
                    from app.orchestrator.query_router import ClarificationRequired
                    if isinstance(exc, ClarificationRequired):
                        st.session_state.journey_clarification = dict(
                            user_id=student.user_id, query=routed_query[-8000:], question=exc.question,
                            topic=st.session_state.get("journey_topic") or "")
                        persistence_rerun()

                    st.error(
                        "The system could not process "
                        "the request."
                    )

                    with st.expander(
                        "Professor/Developer Debug — request error"
                    ):

                        st.exception(
                            exc
                        )

    result = (
        st.session_state.last_result
    )

    pending_clarification = st.session_state.get("journey_clarification")
    if pending_clarification:
        st.info(pending_clarification["question"])
        st.caption("Add the missing detail in the same input above, then click Start. Your previous work remains saved.")
        if st.button("Cancel clarification", key="journey_cancel_clarification"):
            st.session_state.pop("journey_clarification", None)
            persistence_rerun()

    if result is not None and not pending_clarification:
        from app.orchestrator.streamlit_workspace import render_workspace
        render_workspace(st.session_state, display_learning_output)


    from app.learning_agent.streamlit_study_plan import render_study_plan
    render_study_plan(student, orchestrator)

    with st.expander("My Learning Progress", expanded=False):

        progress_tracker = (
            st.session_state.learning_progress_tracker
        )

        progress_records = progress_tracker.list_progress(
            student.user_id
        )

        if not progress_records:
            st.info(
                "No learning activity recorded yet. "
                "Start a learning topic to see your progress here."
            )

        else:
            total_topics = len(progress_records)

            completed_sessions = sum(
                record.completed_practice_sessions
                for record in progress_records
            )

            answered_questions = sum(
                record.total_practice_questions
                for record in progress_records
            )

            metric_a, metric_b, metric_c = st.columns(3)

            metric_a.metric(
                "Topics Started",
                total_topics,
            )

            metric_b.metric(
                "Practice Sessions Completed",
                completed_sessions,
            )

            metric_c.metric(
                "Questions Answered",
                answered_questions,
            )

            st.caption(
                "Practice completion records activity, "
                "not proof of topic mastery. Cognitive estimates "
                "come from the existing CACM model."
            )

            for record in progress_records:

                snapshot = progress_tracker.snapshot(
                    student,
                    record.topic_name,
                )

                if snapshot is None:
                    continue

                st.divider()

                st.markdown(
                    f"#### {snapshot.topic_name}"
                )

                status_label = (
                    "Practice completed"
                    if snapshot.status == "practice_completed"
                    else "Started"
                )

                st.write(
                    f"**Activity status:** {status_label}"
                )

                st.write(
                    "**Started:** "
                    + snapshot.started_at.strftime(
                        "%d %b %Y, %I:%M %p"
                    )
                )

                st.write(
                    "**Last activity:** "
                    + snapshot.last_activity_at.strftime(
                        "%d %b %Y, %I:%M %p"
                    )
                )

                activity_a, activity_b = st.columns(2)

                activity_a.metric(
                    "Completed Practice Sessions",
                    snapshot.completed_practice_sessions,
                )

                activity_b.metric(
                    "Practice Questions Answered",
                    snapshot.total_practice_questions,
                )

                if (
                    snapshot.mastery is None
                    or snapshot.confidence is None
                ):
                    st.caption(
                        "No existing CACM estimate is available "
                        "for this topic yet."
                    )

                else:
                    cognitive_a, cognitive_b, cognitive_c = (
                        st.columns(3)
                    )

                    cognitive_a.metric(
                        "CACM Mastery Estimate",
                        f"{snapshot.mastery:.0%}",
                    )

                    cognitive_b.metric(
                        "CACM Confidence Estimate",
                        f"{snapshot.confidence:.0%}",
                    )

                    cognitive_c.metric(
                        "CACM Evidence Attempts",
                        snapshot.cognitive_attempts,
                    )

    with st.expander("Browse Learning Topics", expanded=False):
        topic_bank = LearningTopicBank()

        st.caption(
            "Choose a structured topic or enter your own. "
            "This prepares a request for the existing "
            "multi-agent assistant."
        )

        selected_category = st.selectbox(
            "Learning category",
            topic_bank.categories() + ["Custom Topic"],
            key="learning_topic_browser_category",
        )

        if selected_category == "Custom Topic":
            selected_topic_name = st.text_input(
                "Enter your own topic",
                placeholder="Example: Quantum Computing",
                key="learning_topic_browser_custom",
            ).strip()

            if selected_topic_name:
                st.info(
                    "Custom topics are supported. "
                    "Structured prerequisite guidance "
                    "is not available for this topic yet."
                )

        else:
            category_topics = topic_bank.by_category(
                selected_category
            )

            selected_topic_name = st.selectbox(
                "Choose a topic",
                [topic.name for topic in category_topics],
                key="learning_topic_browser_topic",
            )

            selected_topic = topic_bank.get(
                selected_topic_name
            )

            st.caption(
                f"Suggested starting difficulty: "
                f"{selected_topic.difficulty.title()}"
            )

            prerequisites = topic_bank.prerequisites_for(
                selected_topic_name
            )

            if prerequisites:
                st.info(
                    "Suggested prerequisites: "
                    + ", ".join(
                        topic.name for topic in prerequisites
                    )
                )
            else:
                st.success(
                    "No prerequisites are listed for this topic."
                )

        if st.button(
            "Use This Learning Topic",
            key="learning_topic_browser_use",
            disabled=not bool(selected_topic_name),
        ):
            st.session_state["learning_request_input"] = (
                f"Teach me {selected_topic_name} "
                "step by step, starting from my current level."
            )
            persistence_rerun()

elif page == "Advanced Research Agent":

    from app.research_agent.streamlit_page import (
        display_advanced_research_page,
    )

    display_advanced_research_page(
        student=student,
        orchestrator=orchestrator,
    )


elif page == "Advanced Coding Agent":

    from app.coding_agent.streamlit_page import (
        display_advanced_coding_page,
    )

    display_advanced_coding_page(
        student=student,
        orchestrator=orchestrator,
    )


elif page == "CACM Professor Demo":

    st.title(
        "CACM Cross-Agent Conflict Demo"
    )

    st.write(
        "This controlled demonstration illustrates "
        "how the current prototype handles "
        "contradictory cognitive evidence from "
        "different learning modalities."
    )

    st.info(
        "Controlled demonstration concept: "
        "**Recursion**"
    )

    st.caption(
        "The values below reproduce a previously "
        "tested prototype scenario. This page is a "
        "demonstration view rather than a live "
        "experiment."
    )

    # -----------------------------------------------------
    # STEP 1
    # -----------------------------------------------------

    st.markdown(
        "## 1. Evidence from Specialized Agents"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            "### Learning Agent"
        )

        st.metric(
            "Performance Evidence",
            "90%",
        )

        st.success(
            "Strong performance"
        )

    with col2:

        st.markdown(
            "### Research Agent"
        )

        st.metric(
            "Performance Evidence",
            "20%",
        )

        st.error(
            "Weak comprehension"
        )

    with col3:

        st.markdown(
            "### Coding Agent"
        )

        st.metric(
            "Performance Evidence",
            "25%",
        )

        st.error(
            "Weak coding performance"
        )

    st.warning(
        "CROSS-AGENT CONFLICT DETECTED\n\n"
        "Learning evidence indicates strong "
        "understanding, while Research and Coding "
        "evidence indicate substantially weaker "
        "understanding."
    )

    # -----------------------------------------------------
    # STEP 2
    # -----------------------------------------------------

    st.markdown(
        "## 2. CACM Diagnostic Intervention"
    )

    st.write(
        "Instead of blindly averaging contradictory "
        "evidence, CACM requests additional targeted "
        "evidence."
    )

    st.markdown(
        """
**Diagnostic Question**

What is the purpose of a **base case** in recursion?
        """
    )

    demo_answer = st.radio(
        "Select the student's diagnostic answer:",
        [
            "Choose an answer",
            "It stops the recursive calls.",
            "It makes every recursive call faster.",
            (
                "Recursion does not require a "
                "stopping condition."
            ),
        ],
    )

    run_diagnostic = st.button(
        "Run Diagnostic Resolution",
        type="primary",
    )

    if run_diagnostic:

        if (
            demo_answer
            == "Choose an answer"
        ):

            st.warning(
                "Select a diagnostic answer first."
            )

        elif demo_answer == (
            "It stops the recursive calls."
        ):

            st.session_state.demo_resolved = (
                True
            )

        else:

            st.session_state.demo_resolved = (
                False
            )

            st.info(
                "This answer provides different "
                "diagnostic evidence. In the full "
                "system, CACM would use that evidence "
                "when updating the shared model."
            )

    # -----------------------------------------------------
    # STEP 3 + 4
    # -----------------------------------------------------

    if st.session_state.demo_resolved:

        st.divider()

        st.markdown(
            "## 3. Conflict Resolution"
        )

        st.success(
            "Diagnostic evidence supports the "
            "stronger Learning Agent evidence in "
            "this controlled prototype scenario."
        )

        st.write(
            "The diagnostic performance is closer "
            "to the Learning Agent's earlier "
            "evidence than to the Research and "
            "Coding evidence."
        )

        st.markdown(
            "### Shared Cognitive State "
            "After Resolution"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Estimated Mastery",
                "83.4%",
            )

        with col2:

            st.metric(
                "Confidence",
                "28.4%",
            )

        with col3:

            st.metric(
                "Evidence / Attempts",
                "4",
            )

        st.caption(
            "These values reproduce the current "
            "prototype's tested weighted cognitive "
            "update scenario and require future "
            "experimental calibration."
        )

        st.divider()

        st.markdown(
            "## 4. Cross-Agent State Propagation"
        )

        st.write(
            "The resolved cognitive state is shared "
            "with all specialized agents. Each agent "
            "can now adapt its next action."
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.markdown(
                "### Learning Agent"
            )

            st.success(
                "Verification Quiz"
            )

        with col2:

            st.markdown(
                "### Research Agent"
            )

            st.success(
                "Verification Research"
            )

        with col3:

            st.markdown(
                "### Coding Agent"
            )

            st.success(
                "Verification Coding"
            )

        st.success(
            "Conflict resolved -> shared state "
            "updated -> all three agents replan."
        )

    st.divider()

    with st.expander(
        "What should I explain to the professor?"
    ):

        st.write(
            """
Each specialized agent observes the student through
a different learning modality.

The Learning Agent may observe quiz performance,
the Research Agent may observe research comprehension,
and the Coding Agent may observe practical coding
performance.

If these agents provide strongly contradictory
evidence about the same concept, CACM explicitly
detects the disagreement.

Instead of immediately averaging the scores, the
system can request targeted diagnostic evidence.

That diagnostic evidence is used to resolve the
conflict and update the shared student cognitive
model.

Because all agents use the same updated model,
the resolution can affect the next action selected
by every agent.
            """
        )


# =========================================================
# SYSTEM ARCHITECTURE
# =========================================================

elif page == "System Architecture":

    st.title(
        "CACM-PHSS System Architecture"
    )

    st.write(
        "The prototype combines specialized "
        "educational agents with a shared "
        "cross-agent cognitive model."
    )

    st.markdown(
        "## System Flow"
    )

    st.markdown(
        """
### 1. Student Query

The student asks naturally for learning, research,
coding help, or a combination of them.

â†“

### 2. Query Router

The router identifies the concept and determines
which specialized agents are required.

â†“

### 3. Specialized Agents

**Learning Agent**  
Personalized teaching, resource recommendation,
adaptive assessment and replanning.

**Research Agent**  
Academic paper retrieval and grounded synthesis.

**Coding Agent**  
Programming activities and practical assessment.

â†“

### 4. CACM Cognitive Core

Cognitive evidence from the different agents is
integrated into a shared student model.

â†“

### 5. Conflict Detection

Strong disagreement between agents about the same
concept can be explicitly detected.

â†“

### 6. Diagnostic Resolution

Additional targeted evidence can be requested to
resolve contradictory cognitive evidence.

â†“

### 7. Cross-Agent Adaptation

The resolved shared state is propagated back to
the agents so they can adapt their next actions.
        """
    )

    st.divider()

    st.markdown(
        "## Learning Agent Adaptive Loop"
    )

    st.code(
        """
Student request
      |
      v
Personalized lesson
      |
      v
Real learning resources
      |
      v
Adaptive Practice Q1
      |
      v
Student answer
      |
      v
Semantic evaluation
      |
      v
LearningEvidence
      |
      v
CACM update
      |
      v
Feedback + correct answer
      |
      v
Student chooses Next Question
      |
      v
Adapted Q2
      |
      v
Repeat -> Q3 -> Session Summary
        """,
        language="text",
    )

    st.divider()

    st.markdown(
        "## Current Research Focus"
    )

    st.info(
        "Cross-agent cognitive evidence fusion with "
        "explicit disagreement detection, diagnostic "
        "conflict resolution, and subsequent "
        "cross-agent adaptation."
    )

    st.markdown(
        "## Current Prototype Scope"
    )

    st.markdown(
        """
The current prototype demonstrates:

- Natural-language intent routing
- Specialized Learning, Research and Coding agents
- Multi-agent orchestration
- Personalized Learning Agent content generation
- Dynamic educational resource recommendation
- Sequential adaptive practice
- Semantic answer evaluation
- Student-facing answer feedback
- Reference correct-answer display
- Misconception hypothesis generation
- CACM cognitive-state updating
- Difficulty adaptation after each answer
- Misconception-targeted follow-up questions
- Student-controlled next-question progression
- Practice-session summaries
- Shared cross-agent cognitive state
- Cross-agent conflict detection
- Diagnostic conflict resolution
- Cross-agent state propagation and replanning

Systematic multi-domain evaluation and calibration
remain subsequent stages of the project.
        """
    )


# Save ordinary renders too (for example, editor changes without a rerun button).
if page in {"Student View", "Advanced Coding Agent", "Advanced Research Agent"}:
    from app.orchestrator.streamlit_journey import render_student_journey
    render_student_journey(st.session_state, student_workspace=page == "Student View")
checkpoint()
