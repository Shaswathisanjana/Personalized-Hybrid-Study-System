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


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="CACM-PHSS",
    page_icon="🎓",
    layout="wide",
)


# =========================================================
# SESSION STATE
# =========================================================

if "student" not in st.session_state:
    st.session_state.student = StudentCognitiveModel(
        user_id="student_001"
    )

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = OrchestratorRuntime()

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
    """
    Reset both the student cognitive state and UI state.
    """

    st.session_state.student = StudentCognitiveModel(
        user_id="student_001"
    )

    st.session_state.orchestrator = OrchestratorRuntime()

    st.session_state.last_result = None
    st.session_state.last_query = ""

    reset_practice_state()

    st.session_state.demo_resolved = False


# =========================================================
# RESOURCE DISPLAY
# =========================================================

def display_resource_recommendations(recommendation):
    """
    Display ranked real learning resources returned by
    the resource recommendation subsystem.
    """

    if recommendation is None:
        return

    resources = getattr(
        recommendation,
        "resources",
        [],
    )

    if not resources:
        return

    st.markdown(
        "### Recommended Learning Resources"
    )

    target_level = getattr(
        recommendation,
        "student_level",
        None,
    )

    if target_level:
        st.caption(
            "CACM target resource level: "
            f"{clean_label(target_level)}"
        )

    for index, ranked_resource in enumerate(
        resources,
        start=1,
    ):

        resource = getattr(
            ranked_resource,
            "resource",
            ranked_resource,
        )

        title = getattr(
            resource,
            "title",
            f"Resource {index}",
        )

        url = getattr(
            resource,
            "url",
            "",
        )

        source = getattr(
            resource,
            "source",
            "",
        )

        difficulty = getattr(
            resource,
            "difficulty",
            "unknown",
        )

        description = getattr(
            resource,
            "description",
            "",
        )

        reason = getattr(
            ranked_resource,
            "reason",
            "",
        )

        with st.container(border=True):

            st.markdown(
                f"#### {index}. {title}"
            )

            col1, col2 = st.columns(2)

            with col1:
                st.write(
                    "**Estimated difficulty:**",
                    clean_label(difficulty),
                )

            with col2:
                if source:
                    st.write(
                        "**Source:**",
                        source,
                    )

            if description:
                st.write(description)

            if reason:
                st.caption(
                    f"Why recommended: {reason}"
                )

            if url:
                st.link_button(
                    "Open Resource",
                    url,
                )


# =========================================================
# COGNITIVE STATE DISPLAY
# =========================================================

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
                        max_questions=3,
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

                st.rerun()

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

        st.info(
            "Ready for a short 3-question adaptive "
            "practice session."
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
                            max_questions=3,
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

                    st.rerun()

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

                st.rerun()

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

            st.rerun()

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

                outcome = (
                    learning_runtime
                    .submit_practice_session_answer(
                        student=student,
                        session=session,
                        answer=student_answer,
                    )
                )

                st.session_state.practice_last_outcome = (
                    outcome
                )

                st.session_state.practice_feedback = (
                    outcome.assessment
                )

                st.session_state.last_answered_question = (
                    answered_question
                )

                st.session_state.last_student_answer = (
                    student_answer
                )

                if outcome.summary is not None:

                    st.session_state.practice_summary = (
                        outcome.summary
                    )

                # The backend has already:
                #
                # 1. evaluated the answer
                # 2. created LearningEvidence
                # 3. updated CACM
                # 4. replanned
                # 5. possibly generated the next question
                #
                # But the UI deliberately hides the next
                # question until the student clicks
                # "Next Question".
                st.session_state.waiting_for_next_question = (
                    True
                )

                st.rerun()

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
        "### Learning Agent"
    )

    st.caption(
        "The Learning Agent chooses its pedagogical "
        "action using the student's current CACM state."
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

    page = st.radio(
        "Navigation",
        [
            "Student View",
            "CACM Professor Demo",
            "System Architecture",
        ],
    )

    st.divider()

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
        "Reset Student Session",
        use_container_width=True,
    ):

        reset_everything()

        st.rerun()


# =========================================================
# STUDENT VIEW
# =========================================================

if page == "Student View":

    st.title(
        "Personalized Study Assistant"
    )

    st.write(
        "Ask naturally. CACM-PHSS identifies what "
        "you need and activates the appropriate "
        "specialized AI agent."
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

    query = st.text_input(
        "What would you like help with?",
        placeholder=(
            "Example: Teach me recursion in Python "
            "from basics"
        ),
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

            # A new request starts a new short-term
            # practice session.
            #
            # The student's CACM cognitive state is
            # intentionally preserved.
            reset_practice_state()

            st.session_state.last_query = (
                query.strip()
            )

            with st.spinner(
                "Understanding your request and "
                "activating the appropriate agents..."
            ):

                try:

                    result = (
                        orchestrator.handle_query(
                            student,
                            query.strip(),
                        )
                    )

                    st.session_state.last_result = (
                        result
                    )

                    st.rerun()

                except Exception as exc:

                    st.error(
                        "The system could not process "
                        "the request."
                    )

                    with st.expander(
                        "Technical details"
                    ):

                        st.exception(
                            exc
                        )

    result = (
        st.session_state.last_result
    )

    if result is not None:

        st.divider()

        # =================================================
        # ROUTER RESULT
        # =================================================

        st.markdown(
            "## System Understanding"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Detected Topic",
                result.route.concept.title(),
            )

        with col2:

            agent_names = [
                agent.title()
                for agent
                in result.route.selected_agents
            ]

            st.metric(
                "Activated Agents",
                len(agent_names),
            )

        with col3:

            tracking_text = (
                "Active"
                if result.route.needs_cognitive_tracking
                else "Not Required"
            )

            st.metric(
                "Cognitive Tracking",
                tracking_text,
            )

        st.markdown(
            "#### Activated Specialized Agents"
        )

        agent_labels = {
            "learning": "Learning Agent",
            "research": "Research Agent",
            "coding": "Coding Agent",
        }

        activated = [
            agent_labels.get(
                agent,
                agent.title(),
            )
            for agent
            in result.route.selected_agents
        ]

        st.success(
            " + ".join(
                activated
            )
        )

        with st.expander(
            "Why were these agents selected?"
        ):

            st.write(
                result.route.reason
            )

        st.divider()

        # =================================================
        # AGENT OUTPUTS
        # =================================================

        st.markdown(
            "## Personalized Agent Response"
        )

        for agent_result in (
            result.agent_results
        ):

            if not agent_result.success:

                st.warning(
                    f"{agent_result.agent.title()} "
                    "Agent could not complete its task."
                )

                if agent_result.message:

                    st.caption(
                        agent_result.message
                    )

                continue

            if (
                agent_result.agent
                == "learning"
            ):

                display_learning_output(
                    output=agent_result.output,
                    concept_name=(
                        result.route.concept
                    ),
                    learning_context=(
                        st.session_state.last_query
                    ),
                )

            elif (
                agent_result.agent
                == "research"
            ):

                display_research_output(
                    agent_result.output
                )

            elif (
                agent_result.agent
                == "coding"
            ):

                display_coding_output(
                    agent_result.output
                )

            st.divider()

        # =================================================
        # COGNITIVE STATE
        # =================================================

        if (
            result.route
            .needs_cognitive_tracking
        ):

            display_cognitive_state(
                result.route.concept
            )

        else:

            st.info(
                "This request only retrieves "
                "information, so simply viewing the "
                "result does not change the student's "
                "cognitive model."
            )


# =========================================================
# CACM PROFESSOR DEMO
# =========================================================

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

↓

### 2. Query Router

The router identifies the concept and determines
which specialized agents are required.

↓

### 3. Specialized Agents

**Learning Agent**  
Personalized teaching, resource recommendation,
adaptive assessment and replanning.

**Research Agent**  
Academic paper retrieval and grounded synthesis.

**Coding Agent**  
Programming activities and practical assessment.

↓

### 4. CACM Cognitive Core

Cognitive evidence from the different agents is
integrated into a shared student model.

↓

### 5. Conflict Detection

Strong disagreement between agents about the same
concept can be explicitly detected.

↓

### 6. Diagnostic Resolution

Additional targeted evidence can be requested to
resolve contradictory cognitive evidence.

↓

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