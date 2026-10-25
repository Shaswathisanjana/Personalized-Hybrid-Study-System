import importlib.util
from pathlib import Path
from unittest.mock import patch
import unittest
spec=importlib.util.spec_from_file_location("intelligence",Path(__file__).parents[1]/"app/orchestrator/intelligence.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ProviderShapeTests(unittest.TestCase):
    def test_object_and_single_wrapper(self):
        self.assertEqual(module.parse_object('{"selected_ids":["S1"]}'),{"selected_ids":["S1"]})
        self.assertEqual(module.parse_object('[{"selected_ids":["S1"]}]'),{"selected_ids":["S1"]})
        self.assertEqual(module.parse_object('```json\n{"ok":true}\n```'),{"ok":True})
    def test_ambiguous_arrays_and_empty_rejected(self):
        for text in ['[{"a":1},{"a":2}]','null','[]','"hello"','{"broken":']:
            with self.subTest(text=text),self.assertRaises(module.JSONShapeError):
                module.parse_object(text)
    def test_bad_shape_retries_once(self):
        with patch.dict("os.environ",{"GEMINI_API_KEY":"fixture"},clear=True),patch.object(module,"request_text",side_effect=['["bad"]','{"selected_ids":["S1"]}']) as request:
            self.assertEqual(module.generate("Select papers.")["selected_ids"],["S1"])
            self.assertEqual(request.call_count,2)
    def test_auth_error_not_retried_and_secret_redacted(self):
        with patch.dict("os.environ",{"GEMINI_API_KEY":"fixture-secret"},clear=True),patch.object(module,"request_text",side_effect=RuntimeError("401 fixture-secret")) as request:
            with self.assertRaises(RuntimeError) as error:module.generate("Select papers.")
            self.assertEqual(request.call_count,1)
            self.assertNotIn("fixture-secret",str(error.exception))
if __name__=="__main__":unittest.main()
