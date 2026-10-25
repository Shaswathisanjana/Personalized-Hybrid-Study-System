import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location("modules",Path(__file__).parents[1]/"app/agents/learning/modules.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CurriculumTests(unittest.TestCase):
    def test_sparse_search_keeps_all_modules(self):
        names=["Complexity","Arrays","Strings","Recursion","Trees","Graphs","Sorting","Dynamic programming"]
        steps=m.build_modules(names,[{"target_concept":"Arrays","title":"Array guide","url":"https://example.com/arrays"}],"intermediate")
        self.assertEqual(len(steps),8)
        self.assertEqual(steps[0]["title"],"Complexity")
        self.assertFalse(steps[0]["materials_available"])
        self.assertEqual(steps[1]["url"],"https://example.com/arrays")
        self.assertEqual(steps[0]["difficulty"],"intermediate")
    def test_many_resources_do_not_duplicate_modules(self):
        resources=[{"target_concept":"Trees","url":"a"},{"target_concept":"Trees","url":"b"}]
        self.assertEqual(len(m.build_modules(["Trees"],resources,"beginner")),1)
if __name__=="__main__":unittest.main()
