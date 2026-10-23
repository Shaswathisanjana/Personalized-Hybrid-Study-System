import streamlit as st
from app.persistence.streamlit_state import (
    checkpoint_page, begin_assessment, finish_assessment, checkpoint,
)

from app.coding_agent.integrated_workflow import IntegratedCodingWorkflow
from app.coding_agent.verified_exercises import get_verified_exercise, VERIFIED_CONCEPTS
from app.coding_agent.submission_controller import CodingSubmissionController
from app.coding_agent.adaptive_hint_coordinator import MisconceptionAwareHintCoordinator
from app.orchestrator.student_journey import StudentJourneyService
from app.coding_agent.open_topic import OpenTopicGenerator, GeneratedExercise, normalize_topic, observe_action
from app.coding_agent.guided_review_coordinator import GuidedCodeReviewCoordinator
from copy import deepcopy


CONCEPTS = list(VERIFIED_CONCEPTS)


@checkpoint_page
def display_personalized_practice(student, orchestrator, *, auto_load=False, student_workspace=False):
    # Detach drafts from widget cleanup when another topic/language hides the editor.
    for key in ("advanced_coding_editor", "advanced_coding_generation_attempts"):
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]
    st.session_state.setdefault("advanced_coding_generation_attempts", 2)
    if student_workspace:
        st.write("Solve the Python exercise below. Practice difficulty uses your assessed progress; hints are available while you work.")
    else:
        st.write(
        "Practice Python through verified coding exercises. "
        "Your Coding Agent reads the same cognitive model used "
        "by the Learning and Research Agents."
        )

    workflow = StudentJourneyService(student, orchestrator).coding_workflow()

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

    free_topic = st.text_input("What coding topic would you like to practise?",
        key="advanced_coding_free_topic", max_chars=160,
        help="Optional: overrides the curated selection. Examples: binary search trees, Python decorators, merge sort.")
    language = st.selectbox("Execution language", ["Python", "SQL", "JavaScript", "Java", "C++"],
                            key="advanced_coding_language")
    if language != "Python":
        st.warning(f"{language} execution is not supported. No code will be generated, run or assessed here. "
                   "Python is the only supported execution environment.")
        return
    if free_topic.strip():
        concept = normalize_topic(free_topic)
    # Read-only observation: generation and hints cannot add cognitive evidence.
    state = deepcopy(student).get_concept(concept)

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

    action = observe_action(workflow, concept)

    if student_workspace:
        st.info(f"Recommended practice: {action.action_type.replace('_', ' ')} | Difficulty: {action.difficulty}")
    else:
        st.info(f"Coding Agent decision: {action.action_type} | Recommended difficulty: {action.difficulty}")

    st.caption(action.reason)

    st.divider()

    st.subheader("2. Verified coding exercise")

    st.caption(
        "Curated concepts have distinct easy, medium and hard exercises with predefined behavioral tests. "
        "Custom Python topics require a generated package to pass behavioral validation before loading. "
        "Load an exercise to apply the current recommendation. Your current exercise stays fixed while you work."
    )
    generation_attempts = st.number_input("Maximum generation attempts", min_value=1, max_value=3, value=None,
                                          step=1, key="advanced_coding_generation_attempts")
    st.caption("Curated topics load locally. Other topics use Gemini: up to 3 attempts, 30 seconds per provider "
               "request, 3–8 tests and a 5-second subprocess timeout per validation test. "
               "Generated code uses the same local runner and is not securely sandboxed.")
    generation_status = st.session_state.get("advanced_coding_generation_status")
    if generation_status:
        st.info(generation_status)
    st.caption("Submitted code runs locally in Python subprocesses with a five-second wall-clock timeout per test, "
               "including process startup. A timeout may reflect a slow machine or non-terminating code. "
               "This is not a security sandbox: code can access files, network and other resources with your permissions. "
               "Use trusted code on your own machine. Passing these tests does not prove all inputs, "
               "algorithmic complexity or required techniques are correct; semantic review also contributes to evaluation.")

    if st.button(
        "Load Coding Exercise",
        key="advanced_coding_load",
    ) or auto_load:
        if concept in CONCEPTS:
            exercise = get_verified_exercise(concept_name=concept, difficulty=action.difficulty)
        else:
            st.session_state.advanced_coding_generation_status = (
                f"Generation requested for {concept} ({action.difficulty}). "
                "If interrupted, the previous exercise remains; use Load Coding Exercise to retry explicitly.")
            checkpoint()
            try:
                with st.spinner("Generating and executing package validation tests..."):
                    exercise = OpenTopicGenerator(max_attempts=int(generation_attempts)).generate(
                        concept, action.difficulty, language)
            except Exception:
                st.session_state.advanced_coding_generation_status = (
                    "Generation failed or no candidate passed validation. The previous exercise and CACM "
                    "state are preserved. Retry explicitly or clear the free-text topic to use the curated bank.")
                st.warning(st.session_state.advanced_coding_generation_status)
                return
        st.session_state.advanced_coding_generation_status = "Exercise loaded. Generation did not update CACM."

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
        st.session_state.pop("advanced_coding_guided_result", None)
        st.session_state.pop("advanced_coding_guided_source", None)

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

    current_spec = get_verified_exercise(concept, task.difficulty) if concept in CONCEPTS else None
    if isinstance(exercise, GeneratedExercise):
        st.caption("AI-generated Python exercise. " + exercise.validation_summary)
    if current_spec is not None and task.title != current_spec.task.title:
        st.info("This saved exercise uses an earlier specification. Your code and results are retained. "
                "Load Coding Exercise to start the current task at the recommended difficulty.")
    elif task.difficulty != action.difficulty:
        st.caption("The recommendation has changed with your assessed evidence. Your loaded exercise remains "
                   "at its original difficulty; load another exercise when you are ready.")

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
                    begin_assessment("coding", {"code": code})
                    record, is_new = controller.submit(code)

                    st.session_state.advanced_coding_submission_record = (
                        record
                    )

                    st.session_state.advanced_coding_submission_source = (
                        code
                    )

                    finish_assessment()
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

    st.subheader("Review and test a suggested correction")
    st.caption("Optional AI feedback uses the assessed original code and this exercise's tests. "
               "Viewing or verifying a correction does not change CACM mastery.")
    if st.button("Get Guided Review and Verify Correction", key="advanced_coding_guided_review"):
        try:
            with st.spinner("Reviewing the original submission and checking the suggested correction..."):
                guided = GuidedCodeReviewCoordinator().review_submission(
                    code=assessed_code, problem_description=task.description,
                    concept_name=task.concept_name, test_cases=exercise.test_cases)
            st.session_state.advanced_coding_guided_result = guided
            st.session_state.advanced_coding_guided_source = record.submission_id
        except Exception:
            st.warning("Guided review unavailable. Your assessment and cognitive state are preserved; retry explicitly.")
    guided = st.session_state.get("advanced_coding_guided_result")
    if guided is not None and st.session_state.get("advanced_coding_guided_source") == record.submission_id:
        st.write(guided.educational_feedback)
        st.write("Correction status:", guided.correction_status)
        st.write(guided.review.summary)
        for issue in guided.review.issues:
            st.write(issue.explanation)
            st.write(issue.hint)
        if guided.review.corrected_code:
            st.code(guided.review.corrected_code, language="python")

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

    if student_workspace:
        st.info(f"Next practice: {next_action.action_type.replace('_', ' ')} | Difficulty: {next_action.difficulty}")
    else:
        st.info(f"Next Coding Agent action: {next_action.action_type} | Recommended difficulty: {next_action.difficulty}")

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

    concepts = list(CONCEPTS)
    for evidence in orchestrator.cognitive_engine.evidence_store.get_all_evidence():
        if evidence.source_agent == "coding" and evidence.concept_name not in concepts:
            concepts.append(evidence.concept_name)
    for concept in concepts:
        st.markdown(f"### {concept}")

        state = deepcopy(student).get_concept(concept)

        col1, col2, col3 = st.columns(3)

        col1.metric("Mastery", f"{state.mastery:.0%}")
        col2.metric("Confidence", f"{state.confidence:.0%}")
        col3.metric("Attempts", state.attempts)

        action = observe_action(workflow, concept)

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
