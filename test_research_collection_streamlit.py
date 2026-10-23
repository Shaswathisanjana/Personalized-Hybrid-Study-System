"""Actual main-app PDF collection actions with offline providers and real PDFs."""
from io import BytesIO
from copy import deepcopy
from unittest.mock import patch
import unittest

import test_research_analysis_streamlit as existing
from app.research_agent.collection_service import ResearchCollectionService
from pdf_collection_test_fixtures import make_pdf, ExtractiveAnalyzer


class PDFCollectionStreamlitTests(unittest.TestCase):
    # Reuse the existing temporary-store, offline-orchestrator and network guard.
    setUp = existing.ResearchAnalysisUITests.setUp
    app = existing.ResearchAnalysisUITests.app
    healthy = existing.ResearchAnalysisUITests.healthy
    button = staticmethod(existing.ResearchAnalysisUITests.button)

    def service(self, owner=None):
        return ResearchCollectionService(self.store, owner or self.owner)

    def test_more_than_five_uploaded_pdfs_extract_analyze_refresh_and_no_mastery(self):
        existing.ResearchAnalysisUITests.seed_conflicts(self, ['Recursion'])
        uploads = []
        for index in range(7):
            content = make_pdf(index)
            uploaded = BytesIO(content)
            uploaded.name, uploaded.size = f'fixture-{index}.pdf', len(content)
            uploads.append(uploaded)
        analyzer = ExtractiveAnalyzer()
        # AppTest does not simulate the browser's native file picker. Supply real
        # PDF bytes at that boundary and exercise the actual Add/Extract/Analyze UI.
        with patch('app.research_agent.streamlit_collection.st.file_uploader', return_value=uploads), \
                patch('app.research_agent.collection_service.GroundedChunkAnalyzer', return_value=analyzer):
            app = self.app()
            prior_concepts = deepcopy(app.session_state.student.concepts)
            prior_evidence = deepcopy(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence())
            self.button(app, 'Add uploaded PDFs to collection').click().run()
            self.healthy(app)
            self.assertEqual(len(self.service().list()), 7)
            for _ in range(3):
                self.button(app, 'Extract / retry next PDF batch').click().run(timeout=30)
                self.healthy(app)
            for _ in range(3):
                self.button(app, 'Analyze / retry next selected chunk batch').click().run()
                self.healthy(app)
            self.assertTrue(all(len(d['record']['analysis']) == 2 for d in self.service().list()))
            self.assertEqual(len(analyzer.calls), 14)
            self.assertEqual(app.session_state.student.concepts, prior_concepts)
            self.assertEqual(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), prior_evidence)
            self.assertTrue(app.session_state.orchestrator.cognitive_engine.has_conflict(self.owner, 'Recursion'))
            refreshed = self.app()
            self.healthy(refreshed)
            self.assertEqual(len(analyzer.calls), 14)
            self.assertTrue(any('Collection comparison' in s.value for s in refreshed.subheader))
            self.assertEqual(refreshed.session_state.student.concepts, prior_concepts)
            self.assertEqual(refreshed.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), prior_evidence)

    def test_profile_switch_deselection_and_explicit_removal(self):
        first = self.service()
        identity, _ = first.add('owner-only.pdf', make_pdf(metadata=False))
        first.extract_batch()
        app = self.app()
        self.assertTrue(any('owner-only.pdf' in e.label for e in app.expander))
        checkbox = next(c for c in app.checkbox if c.label == 'Include in active analysis')
        checkbox.uncheck().run()
        self.healthy(app)
        self.assertFalse(self.service().list()[0]['record']['selected'])
        self.assertFalse(self.service().documents.get(self.owner, identity)['record']['analysis'])
        # Existing profile control opens the other saved student in the real UI.
        next(s for s in app.selectbox if s.label == 'Current student').set_value(self.bob).run()
        self.healthy(app)
        self.assertEqual(self.service(self.bob).list(), [])
        self.assertFalse(any('owner-only.pdf' in e.label for e in app.expander))
        next(s for s in app.selectbox if s.label == 'Current student').set_value(self.owner).run()
        self.healthy(app)
        self.button(app, 'Remove from active collection').click().run()
        self.healthy(app)
        self.assertEqual(self.service().list(), [])


if __name__ == '__main__':
    unittest.main()
