import unittest
from app.agents.research.evidence_context import pack_evidence,validate_section
class ContextTests(unittest.TestCase):
    def test_later_fields_not_lost_after_long_methods(self):
        record={"source_id":"S41","retrieved_evidence":{"methodology":[{"text":"A"*9000}],"future_work":[{"text":"Test a broader dataset","pages":"8"}]}}
        packed=pack_evidence(record)
        self.assertEqual(packed["retrieved_evidence"]["future_work"][0]["pages"],"8")
        self.assertIn("broader",packed["retrieved_evidence"]["future_work"][0]["text"])
    def test_empty_experiment_rejected(self):
        with self.assertRaises(ValueError):
            validate_section("future_work",[{"description":"Existing achievement","source_ids":["S41"],"experiment":{}}])
    def test_achievement_alone_not_gap(self):
        with self.assertRaises(ValueError):
            validate_section("gaps",[{"description":"A new memory system","source_ids":["S15"]}])
if __name__=="__main__":unittest.main()
