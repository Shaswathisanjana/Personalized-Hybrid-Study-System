"""Actual student-page workflows, not mocked activity renderers."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import unittest

import test_student_journey_streamlit as journey_ui
import test_verified_coding_catalog as catalog
from app.orchestrator.query_router import QueryRoute
from app.persistence.research_library_store import UnifiedResearchDocumentStore
from test_research_search_collection import PagedFixture, synthetic_paper


def route(query):
    if "then" in query:
        agents = ["learning", "coding", "research"]
    elif "research" in query:
        agents = ["research"]
    else:
        agents = ["coding"]
    return QueryRoute(query, "Recursion", [], agents, True, "Offline activity order")


class WorkspaceUITests(unittest.TestCase):
    setUp = journey_ui.StudentJourneyUITests.setUp
    app = journey_ui.StudentJourneyUITests.app
    healthy = journey_ui.StudentJourneyUITests.healthy
    button = staticmethod(journey_ui.StudentJourneyUITests.button)
    start = journey_ui.StudentJourneyUITests.start

    def routing(self):
        patcher = patch.object(journey_ui.RoutedOfflineOrchestrator, "route", staticmethod(route))
        patcher.start()
        self.addCleanup(patcher.stop)
        search_patcher = patch("app.research_agent.search_session.AcademicPaperSearch", return_value=PagedFixture([[]]))
        search_patcher.start()
        self.addCleanup(search_patcher.stop)

    def test_coding_runs_and_assesses_inline_without_advanced_navigation(self):
        self.routing()
        with patch("app.coding_agent.integrated_workflow.CodingEvaluator",
                   side_effect=catalog.EvaluationGuardrailTests().evaluator):
            app = self.app()
            self.start(app, "Give me coding practice")
            self.assertEqual(app.radio[0].value, "Student View")
            app.button(key="advanced_coding_load").click().run()
            self.healthy(app)
            app.text_area(key="advanced_coding_editor").set_value(catalog.SOLUTIONS[("Recursion", "easy")])
            app.button(key="advanced_coding_submit").click().run()
            self.healthy(app)
            self.assertEqual(app.session_state.student.find_concept("Recursion").attempts, 1)
            refreshed = self.app()
            refreshed.button(key="advanced_coding_submit").click().run()
            self.healthy(refreshed)
            self.assertEqual(refreshed.session_state.student.find_concept("Recursion").attempts, 1)
            refreshed.button(key="journey_next_activity").click().run()
            self.healthy(refreshed)
            self.assertEqual(refreshed.session_state.journey_workspace["steps"][0]["status"], "assessed")

    def test_research_search_and_persistent_selection_inline(self):
        self.routing()
        provider = PagedFixture([[synthetic_paper(i) for i in range(7)]])
        with patch("app.research_agent.search_session.AcademicPaperSearch", return_value=provider):
            app = self.app()
            self.start(app, "Find research papers")
            self.assertEqual(app.radio[0].value, "Student View")
            topic = next(t for t in app.text_input if t.label == "Academic search topic")
            self.assertEqual(topic.value, "Recursion")
            self.assertEqual(len(provider.calls), 1)  # Original query triggered one bounded page.
            self.healthy(app)
            for box in [c for c in app.checkbox if c.label == "Select search result"]:
                box.check()
            app.run()
            self.button(app, "Add selected search results to collection").click().run()
            self.healthy(app)
            self.assertEqual(len(UnifiedResearchDocumentStore(self.store).list(self.alice)), 7)
            self.assertEqual(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), [])
            refreshed = self.app()
            self.assertEqual(len(provider.calls), 1)
            self.assertEqual(refreshed.session_state.journey_workspace["index"], 0)
            refreshed.selectbox(key="_profile_selector").select(self.bob).run()
            self.healthy(refreshed)
            self.assertNotIn("journey_workspace", refreshed.session_state)
            self.assertEqual(UnifiedResearchDocumentStore(self.store).list(self.bob), [])

    def test_multi_step_sequence_survives_refresh_and_does_not_award_browsing(self):
        self.routing()
        app = self.app()
        self.start(app, "Teach recursion then code then papers")
        self.assertTrue(any(b.label == "Start Adaptive Practice" for b in app.button))
        self.assertFalse(any(b.key == "advanced_coding_load" for b in app.button))
        app.button(key="journey_next_activity").click().run()
        self.healthy(app)
        self.assertTrue(any(b.key == "advanced_coding_load" for b in app.button))
        self.assertEqual(app.session_state.journey_workspace["steps"][0]["status"], "visited_without_assessment")
        refreshed = self.app()
        self.assertEqual(refreshed.session_state.journey_workspace["index"], 1)
        refreshed.button(key="journey_next_activity").click().run()
        self.healthy(refreshed)
        self.assertTrue(any(t.label == "Academic search topic" for t in refreshed.text_input))
        self.assertEqual(refreshed.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), [])


if __name__ == "__main__":
    unittest.main()
