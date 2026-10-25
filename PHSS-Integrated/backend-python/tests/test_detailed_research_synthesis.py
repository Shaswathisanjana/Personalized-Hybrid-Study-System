import unittest
from app.agents.research.synthesis import detailed_synthesis
from app.agents.research.evolution import checked_synthesis
class DetailedTests(unittest.TestCase):
    def test_separate_sections_and_experiment_survive(self):
        prompts=[]
        def provider(prompt):
            prompts.append(prompt)
            return {"items":[{"title":"Finding","description":"Evidence-based account.","source_ids":["S1"],"period":"2025",
                "existing_work":"Previous method","unresolved_limitation":"Untested condition","why_it_matters":"Reliability", "experiment":{"research_question":"Does it help?","hypothesis":"It improves robustness","implementation":"Build a prototype","data":"Proposed test set","baselines":"Compare a single agent","metrics":"Proposed task success","validation":"Holdout test","risks":"Limited data"}}]}
        result=detailed_synthesis("Test topic","2026-10-25",[{"source_id":"S1"}],provider)
        self.assertEqual(len(prompts),5)
        checked=checked_synthesis(result,{"S1"})
        self.assertIn("comparisons",checked)
        self.assertEqual(checked["future_work"][0]["experiment"]["baselines"],"Compare a single agent")
    def test_bad_gap_does_not_discard_valid_findings(self):
        def provider(prompt):
            return {"items":[{"title":"Result","description":"Supported account","source_ids":["S1"]}]}
        result=detailed_synthesis("Test","2026-10-25",[{"source_id":"S1"}],provider)
        self.assertTrue(result["current_state"])
        self.assertEqual(result["gaps"],[])
        self.assertEqual(result["future_work"],[])
        self.assertTrue(result["section_warnings"])
if __name__=="__main__":unittest.main()
