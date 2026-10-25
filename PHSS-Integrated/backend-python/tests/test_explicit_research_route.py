import ast,importlib.util,re,unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]/"app"
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
class ResearchRouteTests(unittest.TestCase):
    def test_explicit_research_beats_wrong_model_classification(self):
        intents=load("intent",ROOT/"orchestrator/intents.py")
        debug=load("debug",ROOT/"agents/coding/debugging.py")
        called=[]
        def provider(prompt):
            called.append(prompt)
            return {"concept":"Wrong learning topic","selected_agents":["learning"]}
        namespace={"re":re,"VALID":{"learning","coding","research"},"explicit_intent":intents.explicit_intent,
                   "looks_like_code":debug.looks_like_code,"generate":provider}
        tree=ast.parse((ROOT/"orchestrator/routing.py").read_text())
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        exec(compile(ast.Module(body=funcs,type_ignores=[]),"routing.py","exec"),namespace)
        for text in ["research on agentic and multi agent","research on PCB defect detecton","find papers about reinforcement learning"]:
            self.assertEqual(namespace["route"](text)["selected_agents"],["research"])
        self.assertEqual(called,[])
        self.assertEqual(namespace["route"]("print('research on PCB')")["selected_agents"],["coding"])
        self.assertEqual(namespace["route"]("I want to learn PCB defect detection")["selected_agents"],["learning"])
if __name__=="__main__":unittest.main()
