"""Learning-page access to the existing genuine CACM diagnostic workflow."""
from app.cognitive.cross_agent_runtime import CrossAgentRuntime
from app.cognitive.diagnostic_intervention import DiagnosticIntervention


class LearningDiagnosticBridge:
    def __init__(self, student, cognitive_engine, learning_runtime=None):
        self.student = student
        self.cognitive_engine = cognitive_engine
        self.runtime = CrossAgentRuntime(cognitive_engine, DiagnosticIntervention(
            cognitive_engine,
            quiz_generator=getattr(learning_runtime, "quiz_generator", None),
            answer_evaluator=getattr(learning_runtime, "answer_evaluator", None)))

    def start(self, concept_name):
        if not self.cognitive_engine.has_conflict(self.student.user_id, concept_name):
            raise ValueError("A learning diagnostic requires a genuine unresolved CACM conflict.")
        return self.runtime.decide(self.student, concept_name).diagnostic_session

    def submit_answer(self, session, answer):
        if session.user_id != self.student.user_id:
            raise ValueError("This diagnostic belongs to another student.")
        return self.runtime.submit_diagnostic_and_replan(self.student, session, answer)
