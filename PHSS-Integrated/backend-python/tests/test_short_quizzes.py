"""Run actual generation methods with a fake provider and no external services."""
import ast, logging, unittest
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace as NS
from typing import List, Optional, Any
SOURCE=Path(__file__).parents[1]/"vendor/cognitive_learning_agent/llm/client.py"
class ShortQuizTests(unittest.TestCase):
    def test_initial_and_retake_keep_short_response(self):
        tree=ast.parse(SOURCE.read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef))
        for name in ["generate_concept_quiz","generate_adaptive_quiz"]:
            with self.subTest(name=name):
                method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
                scope=dict(List=List,Optional=Optional,Any=Any,ConceptQuiz=NS,QuizQuestion=NS,QuizAttemptRecord=NS,
                    QuestionType=NS(MCQ="mcq",DESCRIPTIVE="descriptive",PREDICT_OUTPUT="predict_output"),
                    settings=NS(DEFAULT_GROQ_MODEL="fixture"),QUIZ_GENERATION_PROMPT="",ADAPTIVE_QUIZ_PROMPT="",logger=logging.getLogger("test"))
                exec(compile(ast.Module(body=[method],type_ignores=[]),str(SOURCE),"exec"),scope)
                def fallback(*a,**k):raise AssertionError("Valid partial quiz must not use fallback")
                response={"questions":[{"question_text":"What is a variable?","options":["A name","An HTTP request","A browser","A paper"],"correct_option_index":0,"explanation":"A variable is a name."}]}
                fake=NS(_groq_client=NS(chat=NS(completions=NS(create=lambda **k:NS(choices=[NS(message=NS(content="fixture"))])))),
                    _extract_json=lambda text:response,_heuristic_quiz_generation=fallback,_heuristic_adaptive_quiz=fallback)
                kwargs={"concept_name":"Variables"}
                if name=="generate_adaptive_quiz":kwargs["previous_attempts"]=[NS(weak_areas=[],misconceptions=[])]
                fake._groq_client=None
                bridge=NS(generate=lambda prompt:response,safe_error=lambda provider,error:provider+": "+str(error))
                with patch.dict("sys.modules",{"app.orchestrator.intelligence":bridge}):
                    quiz=scope[name](fake,**kwargs)
                self.assertEqual(len(quiz.questions),1)
                self.assertEqual(quiz.questions[0].question_id,1)
if __name__=="__main__":unittest.main()
