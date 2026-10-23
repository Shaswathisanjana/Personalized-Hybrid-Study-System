"""Actual main-app topic search, source selection and DOCX form workflows."""
from copy import deepcopy
import json
import os
from unittest.mock import patch
import unittest

import test_research_analysis_streamlit as existing
from app.persistence.research_library_store import UnifiedResearchDocumentStore
from app.research_agent.collection_service import ResearchCollectionService
from app.research_agent.search_session import ResearchSearchSession
from pdf_collection_test_fixtures import ExtractiveAnalyzer
from test_research_search_collection import PagedFixture, synthetic_paper


class TopicSearchStreamlitTests(unittest.TestCase):
    setUp = existing.ResearchAnalysisUITests.setUp
    app = existing.ResearchAnalysisUITests.app
    healthy = existing.ResearchAnalysisUITests.healthy
    button = staticmethod(existing.ResearchAnalysisUITests.button)

    def test_search_select_analyze_export_and_refresh_preserve_profile_and_cacm(self):
        existing.ResearchAnalysisUITests.seed_conflicts(self, ['Recursion'])
        provider = PagedFixture([[synthetic_paper(i) for i in range(7)]])
        analyzer = ExtractiveAnalyzer()
        with patch('app.research_agent.search_session.AcademicPaperSearch', return_value=provider), \
                patch('app.research_agent.collection_service.GroundedChunkAnalyzer', return_value=analyzer):
            app = self.app()
            before = deepcopy(app.session_state.student.concepts)
            evidence = deepcopy(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence())
            next(t for t in app.text_input if t.label == 'Academic search topic').set_value('Agentic AI for Personalized Learning')
            next(t for t in app.number_input if t.label == 'Desired number of research papers').set_value(7)
            self.button(app, 'Search academic papers').click().run()
            self.healthy(app)
            self.assertEqual(len(provider.calls), 1)
            for box in [c for c in app.checkbox if c.label == 'Select search result']:
                box.check()
            app.run()
            self.button(app, 'Add selected search results to collection').click().run()
            self.healthy(app)
            library = UnifiedResearchDocumentStore(self.store)
            self.assertEqual(len(library.list(self.owner)), 7)
            self.button(app, 'Analyze / retry mixed collection batch').click().run()
            self.button(app, 'Analyze / retry mixed collection batch').click().run()
            self.healthy(app)
            self.assertEqual(len(analyzer.calls), 7)
            next(t for t in app.text_input if t.label == 'Word report research topic').set_value('Saved report topic')
            chosen = [d['document_id'] for d in library.list(self.owner)[:2]]
            next(s for s in app.multiselect if s.label == 'Papers to include in Word report').set_value(chosen)
            next(s for s in app.multiselect if s.label == 'Word report sections').set_value(['title', 'references', 'methods', 'limitations'])
            self.button(app, 'Generate Research Report (.docx)').click().run()
            self.healthy(app)
            self.assertTrue(any(b.label == 'Download Research Report (.docx)' for b in app.get('download_button')))
            with self.store._connection() as db:
                preferences = json.loads(db.execute('SELECT record FROM research_report_preferences WHERE student_id=?',
                                                    (self.owner,)).fetchone()[0])
            self.assertEqual(preferences['sources'], chosen)
            self.assertEqual(preferences['sections'], ['title', 'references', 'methods', 'limitations'])
            self.assertEqual(app.session_state.student.concepts, before)
            self.assertEqual(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), evidence)
            refreshed = self.app()
            self.healthy(refreshed)
            self.assertEqual(len(provider.calls), 1)
            self.assertEqual(len(analyzer.calls), 7)
            self.assertEqual(next(t for t in refreshed.text_input if t.label == 'Word report research topic').value,
                             'Saved report topic')
            self.assertEqual(refreshed.session_state.student.concepts, before)
            next(s for s in refreshed.selectbox if s.label == 'Current student').set_value(self.bob).run()
            self.healthy(refreshed)
            self.assertEqual(library.list(self.bob), [])
            self.assertFalse(any(t.label == 'Word report research topic' for t in refreshed.text_input))

    def test_failed_search_page_is_visible_and_retry_preserves_selected_results(self):
        provider = PagedFixture([[synthetic_paper(1)], RuntimeError('Injected retrieval failure')])
        with patch('app.research_agent.search_session.AcademicPaperSearch', return_value=provider):
            app = self.app()
            next(t for t in app.text_input if t.label == 'Academic search topic').set_value('Custom arbitrary topic')
            self.button(app, 'Search academic papers').click().run()
            next(c for c in app.checkbox if c.label == 'Select search result').check().run()
            self.button(app, 'Load more / retry academic search').click().run()
            self.healthy(app)
            self.assertTrue(any('Injected retrieval failure' in w.value for w in app.warning))
            record, _ = ResearchSearchSession(self.store, self.owner).load()
            self.assertTrue(record['results'][0]['selected'])
            self.assertEqual(len(record['results']), 1)
            provider.pages[1] = [synthetic_paper(2)]
            self.button(app, 'Load more / retry academic search').click().run()
            self.healthy(app)
            self.assertFalse(ResearchSearchSession(self.store, self.owner).load()[0]['error'])

    def test_configured_limits_replace_legacy_five_paper_slider_cap(self):
        app = self.app()
        slider = next(s for s in app.slider if s.label == 'Number of papers')
        slider.set_value(7).run()
        self.healthy(app)
        self.assertEqual(next(s for s in app.slider if s.label == 'Number of papers').value, 7)
        ResearchSearchSession(self.store, self.owner).start('Saved target before configuration change', 7)
        with patch.dict(os.environ, {'PHSS_RESEARCH_MAX_TARGET': '1'}):
            single_target = self.app()
            self.healthy(single_target)
            self.assertEqual(next(n for n in single_target.number_input if n.label == 'Desired number of research papers').value, 1)


if __name__ == '__main__':
    unittest.main()
