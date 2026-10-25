import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).parents[1]/"vendor/cognitive_learning_agent"
spec=importlib.util.spec_from_file_location("quiz_scope",ROOT/"llm/quiz_scope.py")
scope=importlib.util.module_from_spec(spec);spec.loader.exec_module(scope)

class QuizScopeTests(unittest.TestCase):
    def test_http_question_rejected(self):
        with self.assertRaises(ValueError):
            scope.validate_scope("Python Syntax and Variable Assignment",[SimpleNamespace(question_text="What does idempotency mean in RESTful HTTP APIs?")])
    def test_variables_question_allowed(self):
        scope.validate_scope("Python variables and assignments",[SimpleNamespace(question_text="After x = 3 and x = 5, what is x?",explanation="Assignment rebinds the name.")])
    def test_url_is_not_bank_selection_input(self):
        source=(ROOT/"llm/client.py").read_text()
        self.assertNotIn('(concept_name + " " + resource_title).lower()',source)
        self.assertIn('c_lower = concept_name.lower()',source)
        self.assertIn('No verified fallback quiz exists',source)
    def test_scope_versioned_for_generation_and_submission(self):
        source=(ROOT/"core/agent.py").read_text()
        self.assertEqual(source.count('f"scope-v2:'),4)
if __name__=="__main__":unittest.main()
