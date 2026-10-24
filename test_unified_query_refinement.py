"""Real semantic-router response parsing and actual unified activities, offline."""
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.orchestrator.query_router import QueryRouter, QueryRoute, ClarificationRequired, clarified_request
from app.persistence.state_codec import encode, decode
from app.persistence.session_recovery import capture, restore
from test_student_persistence import student_state
from test_persistence_streamlit import OfflineOrchestrator
import test_student_journey_streamlit as existing_ui
from test_research_search_collection import PagedFixture, synthetic_paper
from app.coding_agent.open_topic import OpenTopicGenerator


def route_payload(query):
    if query.startswith("Resolve this student request"):
        context = json.loads(query.split("\n", 1)[1])
        query = context["student_clarification"]
    fixtures = {
        "Give me a coding problem on Arrays": ("Arrays", ["coding"], "search"),
        "Give me a coding problem on Strings": ("Strings", ["coding"], "search"),
        "Teach me recursion": ("Recursion", ["learning"], "search"),
        "Teach me arrays": ("Arrays", ["learning"], "search"),
        "Give me a coding problem on linked lists": ("linked lists", ["coding"], "search"),
        "Find research papers about agentic AI": ("agentic AI", ["research"], "search"),
        "Compare my uploaded research papers": ("Your research collection", ["research"], "collection"),
        "Teach me recursion and then give me coding practice": ("Recursion", ["learning", "coding"], "search"),
    }
    if query == "Can you improve this?":
        return dict(needs_clarification=True, clarification_question="Which saved work should we improve, and what would you like to change?", selected_agents=[])
    concept, agents, mode = fixtures[query]
    return dict(concept=concept, selected_agents=agents, intents=[], needs_cognitive_tracking=True,
                reason="Recorded semantic response fixture", research_mode=mode, needs_clarification=False)


def real_router(query):
    router = QueryRouter.__new__(QueryRouter)
    router.max_retries, router.retry_delay, router.model_name = 0, 0, "offline-fixture"
    router.client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw:
        SimpleNamespace(text=json.dumps(route_payload(query)))))
    return router.route(query)


def linked_list_package():
    from test_open_topic_coding import package
    p = package()
    p.update(title="Read a Serialized Linked List", description="Return node values in head-to-tail order.",
        function_name="node_values", input_output="A node is null or [value,next_node]; return a list of values.",
        constraints="Acyclic lists of at most 20 integer-valued nodes.",
        expected_behavior="Traverse every node exactly once; preserve order and repeated values.",
        starter_code="def node_values(node):\n    pass\n",
        reference_code="def node_values(node):\n    out = []\n    while node is not None:\n        out.append(node[0])\n        node = node[1]\n    return out\n",
        tests=[dict(name="empty", args=[None], expected_output=[]),
               dict(name="single node", args=[[2,None]], expected_output=[2]),
               dict(name="several nodes", args=[[1,[2,[1,None]]]], expected_output=[1,2,1])],
        hints=["Keep a pointer to the current node.", "An empty link is represented by None.", "Append the value before moving to the next link."])
    return p


class RouterRefinementTests(unittest.TestCase):
    def test_semantic_responses_preserve_real_workflow_and_collection_mode(self):
        for query in ("Teach me recursion", "Give me a coding problem on linked lists", "Find research papers about agentic AI", "Compare my uploaded research papers"):
            result = real_router(query)
            self.assertEqual(result.selected_agents, route_payload(query)["selected_agents"])
            self.assertEqual(result.research_mode, route_payload(query)["research_mode"])

    def test_semantic_ambiguity_does_not_fall_back_to_unrelated_learning(self):
        with self.assertRaisesRegex(ClarificationRequired, "Which saved work"):
            real_router("Can you improve this?")

    def test_fallback_ambiguity_and_collection_are_explicit(self):
        router = QueryRouter.__new__(QueryRouter)
        with self.assertRaises(ClarificationRequired):
            router._fallback_route("something please")
        route = router._fallback_route("Compare my uploaded research papers")
        self.assertEqual(route.selected_agents, ["research"])
        self.assertEqual(route.research_mode, "collection")

    def test_old_saved_routes_decode_with_search_default(self):
        raw = encode(QueryRoute("old", "Recursion", [], ["learning"]))
        raw["fields"].pop("research_mode")
        self.assertEqual(decode(raw).research_mode, "search")

    def test_clarification_restores_without_mastery_and_rejects_wrong_owner(self):
        state = student_state("alice")
        state["journey_clarification"] = dict(user_id="alice", query="help", question="Which topic?", topic="")
        restored = restore(capture(state), "alice", OfflineOrchestrator)
        self.assertEqual(restored["journey_clarification"], state["journey_clarification"])
        self.assertEqual(state["student"].concepts, {})
        with self.assertRaises(ValueError):
            clarified_request("coding", restored["journey_clarification"], "bob")
        state["journey_clarification"]["user_id"] = "bob"
        with self.assertRaises(ValueError):
            capture(state)


class UnifiedQueryUITests(unittest.TestCase):
    app = existing_ui.StudentJourneyUITests.app
    healthy = existing_ui.StudentJourneyUITests.healthy
    button = staticmethod(existing_ui.StudentJourneyUITests.button)

    def setUp(self):
        existing_ui.StudentJourneyUITests.setUp(self)
        self.routes, self.generations = [], []
        def route(query):
            self.routes.append(query)
            return real_router(query)
        self.provider = PagedFixture([[synthetic_paper(i) for i in range(7)]])
        def generate(**kw):
            self.generations.append(kw)
            return linked_list_package()
        for target, replacement in (
            ("app.research_agent.search_session.AcademicPaperSearch", lambda: self.provider),
            ("app.coding_agent.streamlit_page.OpenTopicGenerator", lambda **kw: OpenTopicGenerator(provider=generate, **kw)),
        ):
            patcher = patch(target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(existing_ui.RoutedOfflineOrchestrator, "route", staticmethod(route))
        patcher.start()
        self.addCleanup(patcher.stop)

    def request(self, app, query):
        app.text_input(key="learning_request_input").set_value(query)
        self.button(app, "Start").click().run(timeout=90)
        self.healthy(app)
        self.assertEqual(app.radio[0].value, "Student View")

    def assert_active_agent(self, app, name=None):
        labels = [c.value for c in app.caption if c.value.startswith("Handling this activity:")]
        self.assertEqual(labels, [f"Handling this activity: {name} Agent"] if name else [])

    def test_landing_and_learning_enter_real_adaptive_practice_without_agent_selection(self):
        app = self.app()
        self.assertEqual(app.text_input(key="learning_request_input").label, "What would you like help with today?")
        self.assert_active_agent(app)
        debug = next(e for e in app.sidebar.expander if e.label == "Professor/Developer Debug")
        self.assertFalse(debug.proto.expanded)
        self.assertTrue(any(r.label == "Navigation" for r in debug.radio))
        self.request(app, "Teach me recursion")
        self.assert_active_agent(app, "Learning")
        self.assertFalse(any(m.value == "### Learning Agent" for m in app.markdown))
        self.assertTrue(any(m.value == "### Personalized Explanation" for m in app.markdown))
        self.button(app, "Start Adaptive Practice").click().run()
        self.healthy(app)
        next(t for t in app.text_area if t.label == "Your answer").set_value("answer")
        self.button(app, "Submit Answer").click().run()
        self.healthy(app)
        self.assertEqual(app.session_state.student.find_concept("Recursion").attempts, 1)
        refreshed = self.app()
        self.assertEqual(len(self.routes), 1)
        self.assertEqual(refreshed.session_state.student.find_concept("Recursion").attempts, 1)
        self.assert_active_agent(refreshed, "Learning")

    def test_arbitrary_linked_list_exercise_editor_and_hints_recover(self):
        app = self.app()
        self.request(app, "Give me a coding problem on linked lists")
        self.assert_active_agent(app, "Coding")
        self.assertEqual(len(self.generations), 1)
        self.assertEqual(app.session_state.advanced_coding_exercise.task.concept_name, "linked lists")
        self.assertIn("node_values", app.text_area(key="advanced_coding_editor").value)
        app.text_area(key="advanced_coding_editor").set_value("# my linked-list draft").run()
        app.button(key="advanced_coding_next_hint").click().run()
        self.healthy(app)
        refreshed = self.app()
        self.assertEqual(refreshed.text_area(key="advanced_coding_editor").value, "# my linked-list draft")
        self.assert_active_agent(refreshed, "Coding")
        self.assertEqual(len(refreshed.session_state.advanced_coding_hint_history), 1)
        self.assertEqual(len(self.generations), 1)
        self.assertEqual(refreshed.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), [])

    def test_research_query_runs_actual_search_and_recovers_results(self):
        app = self.app()
        self.request(app, "Find research papers about agentic AI")
        self.assert_active_agent(app, "Research")
        self.assertEqual(self.provider.calls[0][0], "agentic AI")
        self.assertEqual(len([c for c in app.checkbox if c.label == "Select search result"]), 7)
        self.assert_active_agent(self.app(), "Research")
        self.assertEqual(len(self.provider.calls), 1)

    def test_uploaded_paper_comparison_opens_collection_without_search(self):
        from app.research_agent.collection_service import ResearchCollectionService
        from pdf_collection_test_fixtures import make_pdf, ExtractiveAnalyzer
        service = ResearchCollectionService(self.store, self.alice)
        for i in range(2):
            service.add(f"saved-paper-{i}.pdf", make_pdf(i))
        app = self.app()
        self.request(app, "Compare my uploaded research papers")
        self.assert_active_agent(app, "Research")
        self.assertTrue(any(b.label == "Analyze / retry mixed collection batch" for b in app.button))
        self.assertTrue(any(b.label == "Analyze / retry next selected chunk batch" for b in app.button))
        self.assertFalse(any(b.label == "Search academic papers" for b in app.button))
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(app.session_state.journey_workspace["research_mode"], "collection")
        self.button(app, "Extract / retry next PDF batch").click().run(timeout=90)
        with patch("app.research_agent.collection_service.GroundedChunkAnalyzer", return_value=ExtractiveAnalyzer()):
            self.button(app, "Analyze / retry next selected chunk batch").click().run(timeout=90)
        self.healthy(app)
        self.assertTrue(all(len(d["record"]["analysis"]) == 2 for d in service.list()))
        self.assertTrue(any(s.value == "Collection comparison and evidence synthesis" for s in app.subheader))
        self.assertEqual(self.provider.calls, [])
        self.assertEqual(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), [])

    def test_contextual_clarification_refresh_and_reply_do_not_execute_early(self):
        app = self.app()
        self.request(app, "Can you improve this?")
        self.assert_active_agent(app)
        self.assertNotIn("journey_workspace", app.session_state)
        refreshed = self.app()
        self.assertEqual(len(self.routes), 1)
        self.assertTrue(any("Which saved work" in i.value for i in refreshed.info))
        self.assert_active_agent(refreshed)
        self.request(refreshed, "Teach me recursion")
        self.assertNotIn("journey_clarification", refreshed.session_state)
        self.assertIn("student_clarification", self.routes[-1])
        self.assertTrue(any(b.label == "Start Adaptive Practice" for b in refreshed.button))
        self.assertEqual(refreshed.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), [])

    def test_bounded_learning_then_coding_plan_stays_inline(self):
        app = self.app()
        self.request(app, "Teach me recursion and then give me coding practice")
        self.assert_active_agent(app, "Learning")
        self.assertEqual([s["agent"] for s in app.session_state.journey_workspace["steps"]], ["learning", "coding"])
        app.button(key="journey_next_activity").click().run()
        self.healthy(app)
        self.assertEqual(app.radio[0].value, "Student View")
        self.assertTrue(any(t.key == "advanced_coding_editor" for t in app.text_area))
        self.assert_active_agent(app, "Coding")
        refreshed = self.app()
        self.assert_active_agent(refreshed, "Coding")
        refreshed.button(key="journey_next_activity").click().run()
        self.healthy(refreshed)
        self.assert_active_agent(refreshed)
        self.assertEqual(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), [])


if __name__ == "__main__":
    unittest.main()
