"""Resume explicitly requested submissions and apply their saved UI outcomes."""


def apply_learning_outcome(state, outcome, answer):
    session = state["practice_session"]
    state["practice_last_outcome"] = outcome
    state["practice_feedback"] = outcome.assessment
    state["last_answered_question"] = outcome.assessment.question
    state["last_student_answer"] = answer.strip()
    state["waiting_for_next_question"] = True
    if outcome.summary is not None:
        state["practice_summary"] = outcome.summary
        completion_id = getattr(session, "_progress_completion_id", session.session_id)
        session._progress_completion_id = completion_id
        state["learning_progress_tracker"].complete_practice_session(
            state["student"].user_id, session.concept_name,
            outcome.summary.questions_completed, completion_id=completion_id)


def resume_assessment(state):
    pending = state.get("_assessment_pending")
    if not isinstance(pending, dict) or not isinstance(pending.get("request"), dict):
        raise ValueError("This legacy interruption has no saved request to resume safely.")
    kind, request = pending["kind"], pending["request"]
    student = state["student"]
    if kind == "learning":
        outcome = state["orchestrator"].learning_runtime.submit_practice_session_answer(
            student, state["practice_session"], request["answer"], question_id=request["question_id"])
        apply_learning_outcome(state, outcome, request["answer"])
    elif kind == "coding":
        record, _ = state["advanced_coding_controller"].submit(request["code"])
        state["advanced_coding_submission_record"] = record
        state["advanced_coding_submission_source"] = request["code"]
    elif kind == "research":
        outcome = state["research_assessment_service"].submit_answer(
            student.user_id, request["question"], request["answer"], resume=True)
        state["research_assessment_feedback"] = outcome
        state["research_assessment_completed"] = True
    elif kind == "coding_diagnostic":
        state["advanced_coding_diagnostic_result"] = state["advanced_coding_diagnostic_bridge"].submit_answer(
            request["session"], request["answer"])
    elif kind == "research_diagnostic":
        state["research_diagnostic_outcome"] = state["research_diagnostic_bridge"].submit_answer(
            request["session"], request["answer"])
        state["research_diagnostic_concept"] = request["session"].concept_name
        state["research_diagnostic_session"] = None
    elif kind == "learning_diagnostic":
        state["learning_diagnostic_outcome"] = state["learning_diagnostic_bridge"].submit_answer(
            request["session"], request["answer"])
        state["learning_diagnostic_concept"] = request["session"].concept_name
        state["learning_diagnostic_session"] = None
    else:
        raise ValueError("Unknown saved assessment type.")
    state.pop("_assessment_pending", None)
