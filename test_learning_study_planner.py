"""Offline assessment-driven planning and misconception regression checks."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
from app.cognitive.models import StudentCognitiveModel
from app.learning_agent.study_planner import LearningStudyPlanner
from app.learning_agent.topic_bank import LearningTopic, LearningTopicBank
from app.learning_agent.practice_session import PracticeSession
from app.learning_agent.quiz_models import QuizQuestion
from app.learning_agent.runtime import LearningAgentRuntime
from test_persistence_streamlit import OfflineQuiz, OfflineEvaluator, OfflineMisconceptions


class OfflineResources:
    def recommend(self, **kwargs):
        self.request = kwargs
        return None


def runtime(engine):
    return LearningAgentRuntime(engine, quiz_generator=OfflineQuiz(), answer_evaluator=OfflineEvaluator(),
                                misconception_analyzer=OfflineMisconceptions(),
                                resource_recommender=OfflineResources())


class StudyPlannerTests(unittest.TestCase):
    def setUp(self):
        self.student = StudentCognitiveModel("alice")
        self.engine = CognitiveEngine()
        self.planner = LearningStudyPlanner()

    def ready(self, name):
        state = self.student.get_concept(name)
        state.mastery, state.confidence, state.attempts = .9, .8, 4
        return state

    def test_plan_is_read_only_and_orders_transitive_prerequisites(self):
        before = deepcopy(self.student)
        plan = self.planner.create_plan(self.student, self.engine, "recursion")
        self.assertEqual([s.topic_name for s in plan.goal_steps],
                         ["Python Basics", "Python Functions", "Python Recursion"])
        self.assertEqual(plan.recommended.topic_name, "Python Basics")
        self.assertEqual(plan.goal_steps[-1].blocked_by, ("Python Functions",))
        self.assertEqual(self.student, before)
        self.assertEqual(self.engine.evidence_store.get_all_evidence(), [])
        self.assertEqual(len(LearningTopicBank().all_topics()), 50)

    def test_replans_from_shared_state_without_merging_different_topics(self):
        self.ready("Python Basics")
        plan = self.planner.create_plan(self.student, self.engine, "Python Recursion")
        self.assertEqual(plan.recommended.topic_name, "Python Functions")
        self.ready("Python Functions")
        plan = self.planner.create_plan(self.student, self.engine, "recursion")
        self.assertEqual(plan.recommended.topic_name, "Python Recursion")
        self.assertIsNone(self.student.find_concept("Arrays"))

    def test_neutral_prior_is_not_prerequisite_readiness(self):
        self.student.get_concept("Python Basics").mastery = 1
        self.student.get_concept("Python Basics").confidence = 1
        self.assertFalse(self.planner.ready(self.student, self.engine, "Python Basics"))
        self.assertEqual(self.planner.create_plan(self.student, self.engine, "Python Recursion").recommended.purpose, "learn")

    def test_custom_topic_has_no_invented_prerequisites(self):
        plan = self.planner.create_plan(self.student, self.engine, "  Compiler Design ")
        self.assertTrue(plan.custom_goal)
        self.assertEqual(plan.goal_steps[0].blocked_by, ())
        self.assertEqual(plan.recommended.topic_name, "Compiler Design")

    def test_revision_uses_actual_evidence_date_not_view_date(self):
        now = datetime(2026, 10, 20, tzinfo=timezone.utc)
        state = self.ready("Python Basics")
        state.last_updated = now
        evidence = LearningEvidence("alice", "Python Basics", "coding", "code", 1, .5, .9,
                                   timestamp=now - timedelta(days=8))
        self.engine.evidence_store.add_evidence(evidence)
        plan = self.planner.create_plan(self.student, self.engine, "Python Basics", now=now)
        self.assertEqual(plan.revisions[0].purpose, "revise")
        evidence.timestamp = now - timedelta(days=6)
        self.assertEqual(self.planner.create_plan(self.student, self.engine, "Python Basics", now=now).revisions, ())

    def test_global_conflict_has_priority_and_view_does_not_normalize_map(self):
        self.ready("Arrays")
        self.engine.active_conflicts[("alice", "ARRAYS")] = [object()]
        before = dict(self.engine.active_conflicts)
        plan = self.planner.create_plan(self.student, self.engine, "Python Basics")
        self.assertEqual((plan.recommended.topic_name, plan.recommended.purpose), ("Arrays", "diagnostic"))
        self.assertEqual(self.engine.active_conflicts, before)

    def test_cycles_are_reported(self):
        topics = {"A": LearningTopic("A", "test", "easy", ("B",)),
                  "B": LearningTopic("B", "test", "easy", ("A",))}
        bank = SimpleNamespace(get=lambda name: topics.get(name), all_topics=lambda: list(topics.values()))
        with self.assertRaisesRegex(ValueError, "Circular"):
            LearningStudyPlanner(bank).create_plan(self.student, self.engine, "A")

    def test_planned_content_preserves_resource_pipeline_and_does_not_assess(self):
        service = runtime(self.engine)
        step = self.planner.create_plan(self.student, self.engine, "Python Recursion").recommended
        experience = service.get_planned_learning_experience(self.student, step)
        self.assertIsNotNone(experience.activity.content)
        self.assertEqual(service.resource_recommender.request["top_k"], 10)
        self.assertEqual(self.student.get_concept("Python Basics").attempts, 0)
        self.assertEqual(self.engine.evidence_store.get_all_evidence(), [])
        blocked = self.planner.describe(self.student, self.engine, "Python Recursion")
        with self.assertRaisesRegex(ValueError, "prerequisites"):
            service.get_planned_learning_experience(self.student, blocked)

    def test_completed_history_is_deduplicated_persistable_and_scoped(self):
        from app.persistence.session_recovery import capture, restore
        from test_student_persistence import student_state
        from test_persistence_streamlit import OfflineOrchestrator
        state = student_state("alice")
        engine = state["orchestrator"].cognitive_engine
        service = runtime(engine)
        session = service.start_practice_session(state["student"], "Python Basics", max_questions=1).session
        outcome = service.submit_practice_session_answer(state["student"], session, "answer")
        self.assertIsNotNone(outcome.summary)
        history = self.planner.completed_sessions(state["student"], engine)
        self.assertEqual(len(history), 1)
        loaded = restore(capture(state), "alice", OfflineOrchestrator)
        self.assertEqual(len(self.planner.completed_sessions(loaded["student"], loaded["orchestrator"].cognitive_engine)), 1)
        self.assertEqual(self.planner.completed_sessions(StudentCognitiveModel("bob"), engine), [])

    def test_all_four_assessment_lengths_complete_sequentially(self):
        for count in (5, 10, 15, 20):
            with self.subTest(count=count):
                student, engine = StudentCognitiveModel("alice"), CognitiveEngine()
                service = runtime(engine)
                session = service.start_practice_session(student, "Python Basics", max_questions=count).session
                for index in range(count):
                    question = session.current_question
                    outcome = service.submit_practice_session_answer(student, session, "answer",
                                                                      question_id=question.question_id)
                    self.assertEqual(session.questions_completed, index + 1)
                    self.assertEqual(student.get_concept("Python Basics").attempts, index + 1)
                    self.assertEqual(outcome.summary is not None, index == count - 1)
                self.assertTrue(session.is_complete)
                self.assertEqual(len(engine.evidence_store.get_all_evidence()), count)

    def test_existing_weak_topic_can_be_remediated_before_unknown_prerequisites(self):
        self.ready("Python Recursion").mastery = .2
        service = runtime(self.engine)
        step = self.planner.create_plan(self.student, self.engine, "Python Basics").recommended
        self.assertEqual(step.purpose, "remediate")
        self.assertIsNotNone(service.get_planned_learning_experience(self.student, step))


class RemediationTests(unittest.TestCase):
    def setUp(self):
        self.student = StudentCognitiveModel("alice")
        self.engine = CognitiveEngine()
        self.service = runtime(self.engine)
        self.hypothesis = self.engine.misconception_manager.record_support(
            self.student, "Python Basics", "Variables cannot change", "learning")
        self.name = self.hypothesis.description

    def question(self, targets=None):
        return QuizQuestion("Python Basics", "easy", "Controlled target question", correct_answer="answer",
                            misconception_targets=targets or [])

    def submit(self, question, answer="answer"):
        return self.service.submit_practice_answer(self.student, question, answer, generate_next_activity=False)

    def test_correct_targeted_reassessment_reduces_hypothesis_only_once(self):
        before = self.hypothesis.confidence
        question = self.question([self.name])
        self.submit(question)
        confidence = self.hypothesis.confidence
        self.assertLess(confidence, before)
        self.submit(question)
        self.assertEqual(self.hypothesis.confidence, confidence)
        self.assertEqual(self.student.get_concept("Python Basics").attempts, 1)
        self.assertEqual(len(self.engine.evidence_store.get_all_evidence()), 1)

    def test_generic_or_unrecognized_target_is_not_contradiction(self):
        before = self.hypothesis.confidence
        self.submit(self.question())
        self.submit(self.question(["arbitrary generated label"]))
        self.assertEqual(self.hypothesis.confidence, before)

    def test_wrong_answer_does_not_contradict_target(self):
        before = self.hypothesis.confidence
        self.submit(self.question([self.name]), "wrong")
        self.assertEqual(self.hypothesis.confidence, before)

    def test_persistence_failure_rolls_back_then_retries_once(self):
        before = self.hypothesis.confidence
        def fail_after_evidence():
            if self.engine.evidence_store.get_all_evidence():
                raise OSError("Controlled storage failure")
        self.engine.persist_state = fail_after_evidence
        question = self.question([self.name])
        with self.assertRaisesRegex(OSError, "Controlled"):
            self.submit(question)
        state = self.student.get_concept("Python Basics")
        self.assertEqual(state.misconception_hypotheses[self.name].confidence, before)
        self.assertEqual(state.attempts, 0)
        self.engine.persist_state = None
        self.submit(question)
        self.assertAlmostEqual(state.misconception_hypotheses[self.name].confidence, before - .2)
        self.assertEqual(state.attempts, 1)

    def test_new_session_targets_prior_hypothesis_and_stops_when_resolved(self):
        session = PracticeSession("alice", "Python Basics")
        policy = self.service.practice_policy
        self.assertIn(self.name, policy.decide_next_question(self.student, session).target_misconceptions)
        self.submit(self.question([self.name]))
        self.submit(self.question([self.name]))
        self.assertEqual(self.student.get_concept("Python Basics").misconception_hypotheses[self.name].status, "resolved")
        self.assertNotIn(self.name, policy.decide_next_question(self.student, session).target_misconceptions)

    def test_generated_labels_are_restricted_to_requested_hypotheses(self):
        from app.learning_agent.practice_policy import PracticeDecision
        self.service.quiz_generator = SimpleNamespace(generate=lambda **kwargs:
            self.question([self.name, "made up target"]))
        question = self.service._generate_session_question(
            self.student, PracticeSession("alice", "Python Basics"), PracticeDecision("easy", [self.name], "Test"))
        self.assertEqual(question.misconception_targets, [self.name])

    def test_remediation_starts_easy_even_with_high_prior_mastery(self):
        state = self.student.get_concept("Python Basics")
        state.mastery, state.confidence, state.attempts = .95, .9, 4
        session = PracticeSession("alice", "Python Basics")
        self.assertEqual(self.service.practice_policy.decide_next_question(self.student, session).difficulty, "easy")
        self.submit(self.question([self.name]))
        # The existing tracker keeps confidence == .40 active.
        self.assertEqual(state.misconception_hypotheses[self.name].status, "active")
        self.assertEqual(self.service.practice_policy.decide_next_question(self.student, session).difficulty, "easy")

    def test_uncertain_hypothesis_starts_at_verification_difficulty(self):
        state = self.student.get_concept("Python Basics")
        state.mastery, state.confidence, state.attempts = .95, .9, 4
        # Controlled interior value for the existing (.25, .40) uncertain band.
        self.hypothesis.confidence = .55
        self.submit(self.question([self.name]))
        session = PracticeSession("alice", "Python Basics")
        self.assertEqual(state.misconception_hypotheses[self.name].status, "uncertain")
        self.assertEqual(self.service.practice_policy.decide_next_question(self.student, session).difficulty, "medium")


if __name__ == "__main__":
    unittest.main()
