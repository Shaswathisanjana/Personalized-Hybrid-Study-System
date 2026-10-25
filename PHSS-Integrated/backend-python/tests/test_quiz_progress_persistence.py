"""A failed snapshot must not prevent recording an already graded quiz."""
import ast,logging,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from typing import Optional,Any
from datetime import datetime,timezone
SOURCE=Path(__file__).parents[1]/"app/agents/learning/service.py"

class PersistenceTests(unittest.TestCase):
    def run_submission(self,fail_insert=False):
        stored=[]
        def insert(row):
            if fail_insert:raise RuntimeError("database offline")
            stored.append(row)
        result=NS(attempt_number=1,quiz_type="initial",score=.5,passed=False,total_questions=2,correct_count=1,next_action="revise",
                  next_action_reason="Review",weak_areas=[],detected_misconceptions=[],remediation_efficacy=None,
                  model_dump=lambda:{"score":.5,"passed":False})
        def snapshot(*args):raise RuntimeError("snapshot unavailable")
        agent=NS(evaluate_quiz_and_remedy=lambda sub:result,get_cognitive_state=snapshot)
        db=NS(quiz_attempts=NS(insert_one=insert))
        scope=dict(Optional=Optional,Any=Any,QuizSubmission=NS,datetime=datetime,timezone=timezone,
                   get_learning_agent=lambda:agent,get_db=lambda:db,logger=logging.getLogger("test"))
        tree=ast.parse(SOURCE.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="submit_concept_quiz")
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),"exec"),scope)
        response=scope["submit_concept_quiz"]("student","Variables","",course_topic="Python",lesson_key="1:Variables")
        return stored,response
    def test_snapshot_failure_does_not_lose_attempt(self):
        stored,result=self.run_submission()
        self.assertEqual(stored[0]["courseTopic"],"Python")
        self.assertEqual(stored[0]["score"],.5)
        self.assertTrue(result["progressSaved"])
    def test_failed_save_is_visible(self):
        stored,result=self.run_submission(True)
        self.assertFalse(result["progressSaved"])
        self.assertIn("saving course progress failed",result["progressWarning"])
if __name__=="__main__":unittest.main()
