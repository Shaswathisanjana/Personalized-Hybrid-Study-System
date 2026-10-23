"""Sequencing, real learning evidence, policy propagation and recovery, offline."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

from app.orchestrator.orchestrator_runtime import AgentExecutionResult, OrchestratorResult
from app.orchestrator.query_router import QueryRoute
from app.orchestrator.study_workspace import (
    start_workspace, validate_workspace, prepare_active, ensure_learning, advance_workspace,
)
from app.orchestrator.student_journey import StudentJourneyService
from app.persistence.session_recovery import capture, restore
from app.cognitive.models import StudentCognitiveModel
from app.coding_agent.open_topic import observe_action
from test_student_persistence import student_state
from test_student_journey import orchestrator
from test_persistence_streamlit import OfflineOrchestrator


def request(agents, concept="Recursion"):
    query = "Study " + concept
    return OrchestratorResult(query, QueryRoute(query, concept, [], agents, True, "Offline ordered route"),
        [AgentExecutionResult(a, True, dict(kind="study_workflow", agent=a, user_id="alice", concept=concept)) for a in agents])


class WorkspaceTests(unittest.TestCase):
    def state(self, agents, concept="Recursion"):
        state = student_state("alice")
        state["last_result"] = request(agents, concept)
        start_workspace(state, state["last_result"])
        return state

    def test_deferred_route_does_not_execute_any_provider(self):
        runtime = orchestrator()
        runtime.query_router = SimpleNamespace(route=lambda q: QueryRoute(q, "linked lists", [], ["learning", "coding", "research"], True, "fixture"))
        runtime._run_learning = lambda *args: self.fail("Content executed before active step")
        student = StudentCognitiveModel("alice")
        result = StudentJourneyService(student, runtime).handle_request("Teach linked lists then code then research", defer_workflows=True)
        self.assertEqual([r.agent for r in result.agent_results], ["learning", "coding", "research"])
        self.assertTrue(all(r.output["kind"] == "study_workflow" for r in result.agent_results))
        self.assertEqual(student.concepts, {})

    def test_arbitrary_coding_step_and_research_binding_preserve_draft(self):
        state = self.state(["coding", "research"], "Linked Lists")
        state["advanced_coding_editor"] = "# retained draft"
        before = deepcopy(state["student"])
        prepare_active(state)
        self.assertEqual(state["advanced_coding_free_topic"], "linked lists")
        advance_workspace(state)
        self.assertEqual(state["journey_workspace"]["steps"][0]["status"], "visited_without_assessment")
        prepare_active(state)
        self.assertEqual(state["research_search_alice_topic"], "Linked Lists")
        self.assertEqual(state["advanced_coding_editor"], "# retained draft")
        self.assertEqual(state["student"], before)

    def test_saved_sequence_restore_and_owner_guard(self):
        state = self.state(["coding", "research"])
        prepare_active(state)
        advance_workspace(state)
        loaded = restore(capture(state), "alice", OfflineOrchestrator)
        self.assertEqual(loaded["journey_workspace"]["index"], 1)
        self.assertEqual(prepare_active(loaded)["agent"], "research")
        loaded["student"] = StudentCognitiveModel("bob")
        with self.assertRaisesRegex(ValueError, "another student"):
            advance_workspace(loaded)

    def test_learning_failure_requires_explicit_retry_and_checkpoint(self):
        state = self.state(["learning", "coding"])
        calls, saved = [], []
        def run(*args):
            calls.append(True)
            raise RuntimeError("private provider detail")
        state["orchestrator"]._run_learning = run
        ensure_learning(state, lambda: saved.append(deepcopy(state["journey_workspace"])))
        self.assertEqual(saved[0]["steps"][0]["status"], "running")
        self.assertEqual(saved[-1]["steps"][0]["status"], "error")
        self.assertNotIn("private", saved[-1]["steps"][0]["error"])
        ensure_learning(state)
        self.assertEqual(len(calls), 1)
        ensure_learning(state, retry=True)
        self.assertEqual(len(calls), 2)
        self.assertEqual(state["student"].concepts, {})

    def test_interrupted_learning_does_not_restart_automatically(self):
        state = self.state(["learning"])
        prepare_active(state)["status"] = "running"
        state["orchestrator"]._run_learning = lambda *args: self.fail("Automatic replay")
        ensure_learning(state)
        self.assertEqual(state["journey_workspace"]["steps"][0]["status"], "running")

    def test_actual_learning_assessment_changes_later_coding_recommendation(self):
        state = self.state(["learning", "coding"])
        state["orchestrator"] = orchestrator()
        prepare_active(state)
        service = StudentJourneyService(state["student"], state["orchestrator"])
        before = observe_action(service.coding_workflow(), "Recursion").difficulty
        runtime = state["orchestrator"].learning_runtime
        session = runtime.start_practice_session(state["student"], "Python Recursion", max_questions=5).session
        for _ in range(5):
            runtime.submit_practice_session_answer(state["student"], session, "A base case")
        advance_workspace(state)
        prepare_active(state)
        after = observe_action(service.coding_workflow(), "Recursion").difficulty
        self.assertEqual(state["journey_workspace"]["steps"][0]["status"], "assessed")
        self.assertNotEqual(before, after)
        self.assertEqual(state["student"].find_concept("recursion").attempts, 5)

    def test_genuine_conflict_blocks_sequence_advancement(self):
        from app.cognitive.evidence import LearningEvidence
        state = self.state(["coding", "research"])
        prepare_active(state)
        for agent, score in (("learning", .95), ("coding", .05)):
            state["orchestrator"].cognitive_engine.process_evidence(state["student"],
                LearningEvidence("alice", "Recursion", agent, "controlled_test_observation", score, .6, .9))
        with self.assertRaisesRegex(ValueError, "conflict"):
            advance_workspace(state)
        self.assertEqual(state["journey_workspace"]["index"], 0)

    def test_finish_is_idempotent_and_adds_no_evidence(self):
        state = self.state(["research"])
        advance_workspace(state)
        advance_workspace(state)
        self.assertEqual(state["journey_workspace"]["index"], 1)
        self.assertEqual(state["student"].concepts, {})

    def test_snapshot_rejects_cross_owner_or_invalid_sequence(self):
        state = self.state(["coding"])
        state["journey_workspace"]["user_id"] = "bob"
        with self.assertRaisesRegex(ValueError, "another student"):
            capture(state)
        state["journey_workspace"]["user_id"] = "alice"
        state["journey_workspace"]["steps"][0]["status"] = "fabricated_completion"
        with self.assertRaises(ValueError):
            capture(state)

    def test_fallback_preserves_common_then_order(self):
        from app.orchestrator.query_router import QueryRouter
        router = QueryRouter.__new__(QueryRouter)
        route = router._fallback_route("Teach me recursion then give me coding practice then find research papers")
        self.assertEqual(route.selected_agents, ["learning", "coding", "research"])


if __name__ == "__main__":
    unittest.main()
