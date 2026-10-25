import io
import unittest
from datetime import datetime,timezone
from app.agents.research.evolution import deduplicate,checked_selection,checked_synthesis
from app.agents.research.evolution_export import export_progression
from docx import Document

class ProgressionTests(unittest.TestCase):
    def test_deduplicate_and_future_filter(self):
        records=[{"title":"Survey","url":"https://arxiv.org/abs/1v1","published":"2025-01-01","is_survey":True},
                 {"title":"Survey","url":"https://arxiv.org/abs/1v2","published":"2025-01-01"},
                 {"title":"Future","url":"https://example.com/future","published":"2099-01-01"}]
        found=deduplicate(records,datetime(2026,10,25,tzinfo=timezone.utc))
        self.assertEqual(len(found),1)
        self.assertTrue(found[0]["is_survey"])
    def test_auto_count_and_selection(self):
        candidates=[{"source_id":"S1"},{"source_id":"S2"}]
        self.assertEqual(len(checked_selection({"selected_ids":["S1"]},candidates)),1)
        with self.assertRaises(ValueError):checked_selection({"selected_ids":["made-up"]},candidates)
    def test_unknown_citation_rejected(self):
        with self.assertRaises(ValueError):
            checked_synthesis({"current_state":[{"title":"Claim","description":"Text","source_ids":["S9"]}]},{"S1"})
    def test_supported_summary(self):
        data=checked_synthesis({"current_state":[{"title":"Finding","description":"Supported result","source_ids":["S1"]}]},{"S1"})
        self.assertEqual(len(data["current_state"]),1)
    def test_word_uses_progression_not_paper_matrix(self):
        report={"topic":"Test","research_progression":{"timeline":[{"title":"Milestone","description":"New direction","source_ids":["S1"]}]},"papers":[{"title":"Survey","source_id":"S1","url":"https://example.com"}]}
        doc=Document(io.BytesIO(export_progression(report)))
        text=" ".join(p.text for p in doc.paragraphs)
        self.assertIn("Milestone",text);self.assertIn("S1",text)
        self.assertNotIn("Paper-wise comparison",text)
if __name__=="__main__":unittest.main()
