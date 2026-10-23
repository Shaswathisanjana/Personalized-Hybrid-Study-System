"""Persist a content-analysis job without creating cognitive assessment evidence."""


def run_analysis_job(state, coordinator, save):
    job = state["advanced_research_job"]
    job["complete"] = False
    job.pop("error", None)
    save()

    def checkpoint(outcome):
        job["outcome"] = outcome
        state["advanced_research_result"] = outcome.research
        state["advanced_research_action"] = outcome.action
        state["advanced_research_plan"] = outcome.plan
        state["advanced_research_concept"] = job["request"]["concept_name"]
        if not job.get("applied"):
            state["research_assessment_service"] = None
            state["research_assessment_question"] = None
            state["research_assessment_completed"] = False
            state["research_assessment_feedback"] = None
            job["applied"] = True
        save()

    try:
        outcome = coordinator.conduct_research(**job["request"],
                    resume_result=job.get("outcome"), on_checkpoint=checkpoint)
        checkpoint(outcome)
        job["complete"] = not outcome.research.stage_errors
    except Exception as exc:
        job["error"] = f"{type(exc).__name__}: {exc}"
        save()
        raise
    save()
    return outcome
