import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location("intents",Path(__file__).parents[1]/"app/orchestrator/intents.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class IntentTests(unittest.TestCase):
    def test_tree_topic_keeps_domain(self):
        self.assertEqual(module.normalize_learning_topic("I want to learn trees"),"Trees in Data Structures and Algorithms")
        self.assertEqual(module.normalize_learning_topic("trees"),"Trees in Data Structures and Algorithms")
        self.assertEqual(module.normalize_learning_topic("trees in biology"),"trees in biology")
    def test_explicit_examples(self):
        for message,expected in [
            ("I wanted to learn DSA","learning"),
            ("I want to learn English for communication purposes","learning"),
            ("I want to practice Amazon questions","coding"),
            ("practice Google medium array problems","coding"),
            ("teach me interview communication skills","learning"),
            ("I want to study history","learning"),
            ("find research papers on reinforcement learning",None),
            ("debug this Python code",None),
        ]:
            with self.subTest(message=message):
                self.assertEqual(module.explicit_intent(message),expected)
if __name__=="__main__": unittest.main()
