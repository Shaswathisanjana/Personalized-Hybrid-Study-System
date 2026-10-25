"""Verify retrieval APIs and no pretrained-model loading."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
ROOT=Path(__file__).parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

class LightweightTests(unittest.TestCase):
    def test_research_api_and_relevance(self):
        module=load("vectors",ROOT/"vendor/phss_research_agent/src/embeddings.py")
        model=module.get_embedding_model()
        docs=model.embed_documents(["binary tree traversal algorithms","English conversation vocabulary"])
        query=model.embed_query("binary tree traversal")
        self.assertEqual(docs.shape,(2,2048))
        self.assertGreater(float(docs[0]@query),float(docs[1]@query))
        np.testing.assert_allclose(model.encode(["binary tree traversal"])[0],query)
        self.assertEqual(model.encode("binary tree traversal").shape,(2048,))
    def test_no_pretrained_loader(self):
        for path in [
            "vendor/phss_research_agent/src/embeddings.py",
            "vendor/cognitive_learning_agent/discovery/ranker.py",
            "vendor/cognitive_learning_agent/memory/similarity.py"
        ]:
            source=(ROOT/path).read_text()
            self.assertNotIn("from sentence_transformers import",source)
            self.assertNotIn("SentenceTransformer(",source)
    def test_assignment_routes_as_code(self):
        module=load("debugging",ROOT/"app/agents/coding/debugging.py")
        self.assertTrue(module.looks_like_code("x = [1,2,3]\nprint(x[4])"))
        self.assertTrue(module.looks_like_code("answer = 42"))
        self.assertFalse(module.looks_like_code("I want to practice Amazon questions"))

if __name__=="__main__":unittest.main()
