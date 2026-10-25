import ast,importlib.util,unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]/"vendor/phss_research_agent/src"
spec=importlib.util.spec_from_file_location("provenance",ROOT/"provenance.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class IdentityTests(unittest.TestCase):
    def test_canonical_arxiv_identity(self):
        self.assertEqual(module.source_key("http://arxiv.org/abs/2203.08975v2"),module.source_key("https://arxiv.org/pdf/2203.08975v2.pdf"))
    def test_wrong_pdf_rejected(self):
        with self.assertRaises(ValueError):
            module.validate_pdf_identity({"title":"Binary Tree Search Algorithms","url":"https://arxiv.org/abs/2203.08975"},"English pronunciation and conversational grammar")
    def test_matching_title_allowed(self):
        module.validate_pdf_identity({"title":"Binary Tree Search Algorithms"},"Binary Tree Search Algorithms\nAuthors\nAbstract")
    def test_foreign_quote_is_rejected(self):
        parsed={"supporting_quotes":{"dataset":["Another paper uses the CIFAR dataset."]}}
        self.assertFalse(module.supporting_quote_present(parsed,"dataset",[{"text":"This study analyzes English conversation."}]))
        self.assertTrue(module.supporting_quote_present(parsed,"dataset",[{"text":"Another paper uses the CIFAR dataset."}]))
    def test_excerpt_not_presented_as_summary(self):
        source=ast.parse((ROOT/"paper_analysis.py").read_text())
        cls=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=="PaperAnalyzer")
        fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=="_fallback_fields")
        fn.decorator_list=[]
        scope={"FIELD_CONFIG":{"methodology":{},"dataset":{}},"MISSING":"Not explicitly reported"}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),"analysis.py","exec"),scope)
        record={}
        scope["_fallback_fields"](record,{"dataset":[{"text":"A quoted discussion of other studies"}]})
        self.assertEqual(record["dataset"],"Not explicitly reported")
        self.assertEqual(record["analysis_status"],"summary_unavailable")
if __name__=="__main__":unittest.main()
