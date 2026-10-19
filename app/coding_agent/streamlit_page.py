import streamlit as st

from app.coding_agent.integrated_workflow import IntegratedCodingWorkflow
from app.coding_agent.verified_exercises import get_verified_exercise
from app.coding_agent.submission_controller import CodingSubmissionController
from app.coding_agent.adaptive_hint_coordinator import MisconceptionAwareHintCoordinator


CONCEPTS = [
    "Recursion",
    "Prime Numbers",
    "Arrays",
]


def display_personalized_practice(student, orchestrator):
    st.write(
        "Practice Python through verified coding exercises. "
        "Your Coding Agent reads the same cognitive model used "
        "by the Learning and Research Agents."
    )

    workflow = IntegratedCodingWorkflow(
        student=student,
        cognitive_engine=orchestrator.cognitive_engine,
    )

    st.subheader("1. Choose a concept")

    # Apply a concept transferred from the AI Review tab.
    transferred_concept = st.session_state.pop(
        "advanced_coding_target_concept",
        None,
    )

    if transferred_concept in CONCEPTS:
        st.session_state["advanced_coding_concept"] = transferred_concept

    concept = st.selectbox(
        "What would you like to practice?",
        CONCEPTS,
        key="advanced_coding_concept",
    )

    state = student.get_concept(concept)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Current Mastery",
        f"{state.mastery:.0%}",
    )

    col2.metric(
        "Evidence Confidence",
        f"{state.confidence:.0%}",
    )

    col3.metric(
        "Previous Attempts",
        state.attempts,
    )

    action = workflow.choose_action(concept)

    st.info(
        f"Coding Agent decision: {action.action_type} "
        f"| Recommended difficulty: {action.difficulty}"
    )

    st.caption(action.reason)

    st.divider()

    st.subheader("2. Verified coding exercise")

    st.caption(
        "These introductory exercises have predefined behavioral "
        "tests. The Coding Agent's recommendation is adaptive, "
        "but the current exercise questions are fixed."
    )

    if st.button(
        "Load Coding Exercise",
        key="advanced_coding_load",
    ):
        exercise = get_verified_exercise(
            concept_name=concept,
            difficulty="easy",
        )

        st.session_state.advanced_coding_exercise = exercise
        st.session_state.advanced_coding_loaded_concept = concept

        # Each loaded exercise starts a fresh hint progression.
        st.session_state.advanced_coding_hint_engine = (
            MisconceptionAwareHintCoordinator()
        )
        st.session_state.advanced_coding_hint_history = []
        st.session_state.advanced_coding_editor = (
            exercise.task.starter_code
        )

        st.session_state.advanced_coding_controller = (
            CodingSubmissionController(
                workflow=workflow,
                exercise=exercise,
            )
        )

        st.session_state.pop(
            "advanced_coding_submission_record",
            None,
        )

        st.session_state.pop(
            "advanced_coding_submission_source",
            None,
        )

        st.rerun()

    exercise = st.session_state.get(
        "advanced_coding_exercise"
    )

    loaded_concept = st.session_state.get(
        "advanced_coding_loaded_concept"
    )

    if exercise is None or loaded_concept != concept:
        st.info(
            "Click 'Load Coding Exercise' to begin."
        )
        return

    task = exercise.task

    st.markdown(f"### {task.title}")

    st.write(task.description)

    st.caption(
        f"Exercise level: {task.difficulty.title()} "
        f"| Verified tests: {len(exercise.test_cases)}"
    )

    st.markdown("**Expected behavior**")
    st.write(task.expected_behavior)

    st.subheader("3. Write your Python solution")

    code = st.text_area(
        "Python code",
        height=260,
        key="advanced_coding_editor",
    )

    st.subheader("4. Progressive Learning Assistance")

    st.caption(
        "Request increasingly specific guidance without immediately "
        "revealing the complete solution. Hint requests do not "
        "update CACM mastery or assessment attempts."
    )

    hint_engine = st.session_state.get(
        "advanced_coding_hint_engine"
    )

    if hint_engine is None:
        hint_engine = MisconceptionAwareHintCoordinator()
        st.session_state.advanced_coding_hint_engine = hint_engine

    hint_history = st.session_state.get(
        "advanced_coding_hint_history",
        [],
    )

    st.progress(
        min(len(hint_history), 3) / 3,
        text=f"Hints requested: {min(len(hint_history), 3)} / 3",
    )

    if st.button(
        "Get Next Hint",
        key="advanced_coding_next_hint",
        disabled=len(hint_history) >= 3,
    ):
        adaptive_result = hint_engine.get_next_hint(
            task=task,
            code=code,
            session_id=student.user_id,
        )

        hint = adaptive_result.hint
        hint_history = [*hint_history, hint]
        st.session_state.advanced_coding_hint_history = hint_history
        st.rerun()

    for hint in hint_history:
        with st.expander(
            f"Hint {hint.level}: {hint.title}",
            expanded=True,
        ):
            st.write(hint.message)

    if len(hint_history) >= 3:
        st.info(
            "All three hints have been provided. "
            "Try completing the exercise using this guidance."
        )

    st.divider()


    controller = st.session_state.get(
        "advanced_coding_controller"
    )

    if controller is None:
        st.warning(
            "Please click Load Coding Exercise again "
            "to initialize the submission controller."
        )
        return

    if st.button(
        "Submit & Evaluate",
        key="advanced_coding_submit",
        type="primary",
    ):
        if not code.strip():
            st.warning("Please write your solution first.")
        else:
            with st.spinner(
                "Executing tests and evaluating your submission..."
            ):
                try:
                    record, is_new = controller.submit(code)

                    st.session_state.advanced_coding_submission_record = (
                        record
                    )

                    st.session_state.advanced_coding_submission_source = (
                        code
                    )

                    if is_new:
                        st.success(
                            "Submission evaluated and sent to CACM."
                        )
                    else:
                        st.info(
                            "This exact code was already assessed. "
                            "Showing the previous result without "
                            "updating CACM again."
                        )

                except Exception as exc:
                    st.error(
                        f"Submission could not be completed: {exc}"
                    )

    record = st.session_state.get(
        "advanced_coding_submission_record"
    )

    assessed_code = st.session_state.get(
        "advanced_coding_submission_source"
    )

    if record is None:
        return

    if assessed_code != code:
        st.info(
            "Your code has changed since the previous assessment. "
            "Submit again to evaluate the updated solution."
        )
        return

    result = record.result
    evaluation = result.evaluation

    st.divider()
    st.subheader("Assessment Results")

    col1, col2 = st.columns(2)

    col1.metric(
        "Performance",
        f"{evaluation.performance:.0%}",
    )

    col2.metric(
        "Evaluation Confidence",
        f"{evaluation.confidence:.0%}",
    )

    st.write(
        "**Assessment:**",
        "Correct" if evaluation.is_correct else "Needs improvement",
    )

    st.write("**Feedback:**", evaluation.feedback)

    if evaluation.test_results:
        st.markdown("### Behavioral Test Results")

        for test in evaluation.test_results:
            if test.passed:
                st.success(f"PASS: {test.test_name}")
            else:
                st.error(f"FAIL: {test.test_name}")

                if test.error:
                    st.write(test.error)

                st.write(
                    f"Expected: {test.expected_output}"
                )

                st.write(
                    f"Actual: {test.actual_output}"
                )

    if evaluation.detected_misconceptions:
        st.markdown("### Detected Misconceptions")

        for misconception in evaluation.detected_misconceptions:
            st.write(f"- {misconception}")

    st.divider()
    st.subheader("Updated Shared Cognitive State")

    updated = student.get_concept(task.concept_name)

    c1, c2, c3 = st.columns(3)

    c1.metric("Mastery", f"{updated.mastery:.0%}")
    c2.metric("Confidence", f"{updated.confidence:.0%}")
    c3.metric("Attempts", updated.attempts)

    next_action = workflow.choose_action(
        task.concept_name
    )

    st.info(
        f"Next Coding Agent action: {next_action.action_type} "
        f"| Recommended difficulty: {next_action.difficulty}"
    )

    st.caption(next_action.reason)




def display_cognitive_progress(student, orchestrator):
    st.subheader("Shared Cognitive Progress")

    st.write(
        "The Coding Agent uses the same student cognitive model "
        "as the Learning and Research Agents."
    )

    workflow = IntegratedCodingWorkflow(
        student=student,
        cognitive_engine=orchestrator.cognitive_engine,
    )

    for concept in CONCEPTS:
        st.markdown(f"### {concept}")

        state = student.get_concept(concept)

        col1, col2, col3 = st.columns(3)

        col1.metric("Mastery", f"{state.mastery:.0%}")
        col2.metric("Confidence", f"{state.confidence:.0%}")
        col3.metric("Attempts", state.attempts)

        action = workflow.choose_action(concept)

        st.write(f"**Next action:** {action.action_type}")
        st.write(f"**Recommended difficulty:** {action.difficulty}")
        st.caption(action.reason)

        st.divider()

    st.info(
        "These recommendations are generated from the shared "
        "cognitive state. A general AI code review does not "
        "automatically change mastery."
    )


def display_advanced_coding_page(student, orchestrator):
    from app.coding_agent.streamlit_review import (
        display_code_review_tab,
    )
    from app.coding_agent.streamlit_diagnostic import (
        display_coding_diagnostic,
    )

    st.title("Advanced Coding Agent")

    st.write(
        "An adaptive Coding Agent connected to the shared "
        "CACM cognitive system."
    )

    practice_tab, review_tab, diagnostic_tab, progress_tab = st.tabs(
        [
            "Personalized Practice",
            "Paste Code & AI Review",
            "Cross-Agent Diagnostic",
            "Cognitive Progress",
        ]
    )

    with practice_tab:
        display_personalized_practice(
            student=student,
            orchestrator=orchestrator,
        )

    with review_tab:
        display_code_review_tab(
            student=student,
            orchestrator=orchestrator,
        )

    with diagnostic_tab:
        display_coding_diagnostic(
            student=student,
            orchestrator=orchestrator,
        )

    with progress_tab:
        display_cognitive_progress(
            student=student,
            orchestrator=orchestrator,
        )
