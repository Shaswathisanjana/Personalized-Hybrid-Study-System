from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
from app.cognitive.diagnostic_intervention import DiagnosticIntervention
from app.cognitive.cross_agent_runtime import CrossAgentRuntime

from app.learning_agent.quiz_models import QuizQuestion
from app.learning_agent.agent import LearningAgent

from app.research_agent.agent import ResearchAgent
from app.research_agent.cacm_runtime import ResearchCACMRuntime
from app.research_agent.models import (
    ResearchComprehensionQuestion,
    ResearchComprehensionEvaluation,
)

from app.coding_agent.agent import CodingAgent
from app.coding_agent.cacm_runtime import CodingCACMRuntime
from app.coding_agent.models import CodingEvaluation


# ==========================================================
# DETERMINISTIC DIAGNOSTIC GENERATOR
# ==========================================================

class FakeDiagnosticQuizGenerator:
    """
    Deterministic diagnostic generator used for this
    integration test.

    Gemini generation has already been tested separately.
    Using a fixed question here makes the CACM integration
    test reproducible.
    """

    def generate(
        self,
        concept_name: str,
        difficulty: str,
        mastery: float,
        confidence: float,
        quiz_type: str = "practice_quiz",
    ) -> QuizQuestion:

        return QuizQuestion(
            concept_name=concept_name,
            difficulty=difficulty,
            question=(
                "What is the purpose of a base case "
                "in recursion?"
            ),
            question_type="short_answer",
            correct_answer="It stops the recursive calls.",
            explanation=(
                "A base case provides the stopping "
                "condition for recursion."
            ),
            misconception_targets=[
                (
                    "Recursion does not require a "
                    "stopping condition."
                )
            ],
        )


# ==========================================================
# 1. CREATE SHARED CACM STATE
# ==========================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

engine = CognitiveEngine()

concept_name = "recursion"


print("\n==========================================")
print("THREE-AGENT CACM INTEGRATION TEST")
print("==========================================")

print(
    "\nLearning, Research, and Coding operate "
    "on the SAME StudentCognitiveModel."
)


# ==========================================================
# 2. LEARNING AGENT EVIDENCE
# ==========================================================

learning_evidence = LearningEvidence(
    user_id="student_001",
    concept_name=concept_name,
    source_agent="learning",
    evidence_type="practice_quiz",
    performance=0.90,
    difficulty=0.60,
    reliability=0.90,
    detected_misconceptions=[],
)

engine.process_evidence(
    student,
    learning_evidence,
)

state = student.get_concept(
    concept_name
)


print("\n--- AFTER LEARNING EVIDENCE ---")

print(
    "Learning performance:",
    0.90,
)

print(
    "Shared mastery:",
    state.mastery,
)

print(
    "Shared confidence:",
    state.confidence,
)


# ==========================================================
# 3. RESEARCH AGENT EVIDENCE
# ==========================================================

research_question = ResearchComprehensionQuestion(
    concept_name=concept_name,
    question=(
        "Why does a recursive algorithm "
        "require a base case?"
    ),
    correct_answer=(
        "A base case stops the recursive calls."
    ),
    explanation=(
        "Without a stopping condition, recursion "
        "continues indefinitely."
    ),
    difficulty="medium",
    misconception_targets=[
        (
            "Recursion does not require "
            "a stopping condition."
        )
    ],
)


research_evaluation = ResearchComprehensionEvaluation(
    is_correct=False,
    performance=0.20,
    confidence=1.0,
    feedback=(
        "The student shows weak understanding "
        "of the recursion stopping condition."
    ),
    detected_misconceptions=[
        (
            "Unclear understanding of "
            "recursion base case."
        )
    ],
)


research_runtime = ResearchCACMRuntime(
    cognitive_engine=engine,
    student=student,
)


research_outcome = (
    research_runtime.process_comprehension(
        user_id="student_001",
        question=research_question,
        evaluation=research_evaluation,
    )
)


state = student.get_concept(
    concept_name
)


print("\n--- AFTER RESEARCH EVIDENCE ---")

print(
    "Research performance:",
    research_evaluation.performance,
)

print(
    "Shared mastery:",
    state.mastery,
)

print(
    "Shared confidence:",
    state.confidence,
)

print(
    "Conflict active:",
    research_outcome.has_active_conflict,
)


# ==========================================================
# 4. CODING AGENT EVIDENCE
# ==========================================================

coding_evaluation = CodingEvaluation(
    is_correct=False,
    performance=0.25,
    confidence=1.0,
    feedback=(
        "The recursive argument does not progress "
        "toward the base case."
    ),
    detected_misconceptions=[
        (
            "Recursive argument does not move "
            "toward base case."
        )
    ],
)


coding_runtime = CodingCACMRuntime(
    cognitive_engine=engine,
    student=student,
)


coding_outcome = (
    coding_runtime.submit_evaluation(
        user_id="student_001",
        concept_name=concept_name,
        difficulty="medium",
        evaluation=coding_evaluation,
    )
)


state = student.get_concept(
    concept_name
)


print("\n--- AFTER CODING EVIDENCE ---")

print(
    "Coding performance:",
    coding_evaluation.performance,
)

print(
    "Shared mastery:",
    state.mastery,
)

print(
    "Shared confidence:",
    state.confidence,
)

print(
    "Conflict active:",
    coding_outcome.has_active_conflict,
)


# ==========================================================
# 5. DISPLAY CROSS-AGENT CONFLICTS
# ==========================================================

conflicts = engine.get_conflicts(
    "student_001",
    concept_name,
)


print("\n--- CACM CONFLICTS ---")


for conflict in conflicts:

    print(
        conflict.first_agent,
        "vs",
        conflict.second_agent,
        "|",
        conflict.first_performance,
        "vs",
        conflict.second_performance,
        "| difference:",
        conflict.difference,
        "| severity:",
        conflict.severity,
    )


assert len(conflicts) > 0


assert engine.has_conflict(
    "student_001",
    concept_name,
)


# ==========================================================
# 6. CREATE THREE SPECIALIZED AGENTS
# ==========================================================

learning_agent = LearningAgent()
research_agent = ResearchAgent()
coding_agent = CodingAgent()


has_conflict = engine.has_conflict(
    "student_001",
    concept_name,
)


# ==========================================================
# 7. AGENT DECISIONS BEFORE CONFLICT RESOLUTION
# ==========================================================
#
# IMPORTANT:
#
# LearningAgent parameter:
#     has_conflict
#
# ResearchAgent / CodingAgent parameter:
#     has_active_conflict
#
# ==========================================================

learning_before = (
    learning_agent.choose_action(
        student,
        concept_name,
        has_conflict=has_conflict,
    )
)


research_before = (
    research_agent.choose_action(
        student,
        concept_name,
        has_active_conflict=has_conflict,
    )
)


coding_before = (
    coding_agent.choose_action(
        student,
        concept_name,
        has_active_conflict=has_conflict,
    )
)


print(
    "\n--- AGENT ACTIONS BEFORE RESOLUTION ---"
)


print(
    "Learning:",
    learning_before.action_type,
)

print(
    "Research:",
    research_before.action_type,
)

print(
    "Coding:",
    coding_before.action_type,
)


assert (
    learning_before.action_type
    == "diagnostic_quiz"
)

assert (
    research_before.action_type
    == "diagnostic_research"
)

assert (
    coding_before.action_type
    == "diagnostic_coding"
)


# ==========================================================
# 8. CREATE CACM DIAGNOSTIC INTERVENTION
# ==========================================================

diagnostic = DiagnosticIntervention(
    cognitive_engine=engine,
    quiz_generator=FakeDiagnosticQuizGenerator(),
)


cross_agent_runtime = CrossAgentRuntime(
    cognitive_engine=engine,
    diagnostic_intervention=diagnostic,
)


decision = cross_agent_runtime.decide(
    student,
    concept_name,
)


print("\n--- CACM DECISION ---")

print(
    "Action:",
    decision.action.action_type,
)

print(
    "Diagnostic question:",
    decision.diagnostic_session.question.question,
)


assert (
    decision.action.action_type
    == "diagnostic_quiz"
)

assert decision.diagnostic_session is not None


# ==========================================================
# 9. STUDENT ANSWERS DIAGNOSTIC
# ==========================================================
#
# The answer exactly matches the deterministic answer
# because the current Learning AnswerEvaluator performs
# exact-answer evaluation.
# ==========================================================

resolution = (
    cross_agent_runtime.submit_diagnostic_and_replan(
        student=student,
        session=decision.diagnostic_session,
        answer="It stops the recursive calls.",
    )
)


diagnostic_outcome = (
    resolution.diagnostic_outcome
)


print("\n--- DIAGNOSTIC RESULT ---")


print(
    "Performance:",
    diagnostic_outcome.evaluation.performance,
)

print(
    "Conflict resolved:",
    diagnostic_outcome.conflict_resolved,
)

print(
    "Still active conflict:",
    diagnostic_outcome.has_active_conflict,
)


print("\nResolution results:")


for result in diagnostic_outcome.resolution_results:

    print(
        result
    )


# ==========================================================
# 10. UPDATED SHARED COGNITIVE STATE
# ==========================================================

state = student.get_concept(
    concept_name
)


print(
    "\n--- SHARED STATE AFTER DIAGNOSTIC ---"
)


print(
    "Mastery:",
    state.mastery,
)

print(
    "Confidence:",
    state.confidence,
)

print(
    "Attempts:",
    state.attempts,
)


# ==========================================================
# 11. CHECK WHETHER ANY CONFLICT REMAINS
# ==========================================================

remaining_conflict = (
    engine.has_conflict(
        "student_001",
        concept_name,
    )
)


print(
    "Remaining active conflict:",
    remaining_conflict,
)


remaining_conflicts = engine.get_conflicts(
    "student_001",
    concept_name,
)


if remaining_conflicts:

    print(
        "\n--- REMAINING CONFLICTS ---"
    )

    for conflict in remaining_conflicts:

        print(
            conflict.first_agent,
            "vs",
            conflict.second_agent,
            "|",
            conflict.first_performance,
            "vs",
            conflict.second_performance,
            "| difference:",
            conflict.difference,
            "| severity:",
            conflict.severity,
        )


# ==========================================================
# 12. ALL THREE AGENTS RE-OBSERVE THE SAME UPDATED STATE
# ==========================================================

learning_after = (
    learning_agent.choose_action(
        student,
        concept_name,
        has_conflict=remaining_conflict,
    )
)


research_after = (
    research_agent.choose_action(
        student,
        concept_name,
        has_active_conflict=remaining_conflict,
    )
)


coding_after = (
    coding_agent.choose_action(
        student,
        concept_name,
        has_active_conflict=remaining_conflict,
    )
)


print(
    "\n--- AGENT ACTIONS AFTER CACM UPDATE ---"
)


print(
    "Learning:",
    learning_after.action_type,
)

print(
    "Research:",
    research_after.action_type,
)

print(
    "Coding:",
    coding_after.action_type,
)


# ==========================================================
# 13. DISPLAY CROSS-AGENT ADAPTATION
# ==========================================================

print(
    "\n--- CROSS-AGENT ADAPTATION ---"
)


print(
    "Learning:",
    learning_before.action_type,
    "->",
    learning_after.action_type,
)


print(
    "Research:",
    research_before.action_type,
    "->",
    research_after.action_type,
)


print(
    "Coding:",
    coding_before.action_type,
    "->",
    coding_after.action_type,
)


# ==========================================================
# 14. BASIC VALIDATION
# ==========================================================

assert (
    diagnostic_outcome.evaluation.performance
    == 1.0
)


# ==========================================================
# 15. FINAL RESULT
# ==========================================================

print("\n==========================================")
print("THREE-AGENT CACM LOOP EXECUTED")
print("==========================================")


if remaining_conflict:

    print(
        "\nRESULT:"
    )

    print(
        "CACM still has at least one active "
        "cross-agent conflict."
    )

    print(
        "The three-agent integration test has "
        "therefore exposed a multi-conflict "
        "resolution case."
    )

    print(
        "We should improve the CACM resolver "
        "before moving to the UI."
    )


else:

    print(
        "\nRESULT:"
    )

    print(
        "All active cross-agent conflicts "
        "were resolved."
    )

    assert (
        learning_after.action_type
        != learning_before.action_type
    )

    assert (
        research_after.action_type
        != research_before.action_type
    )

    assert (
        coding_after.action_type
        != coding_before.action_type
    )

    print(
        "\nTHREE-AGENT CACM INTEGRATION PASSED"
    )