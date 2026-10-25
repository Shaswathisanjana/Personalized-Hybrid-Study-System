import os
import unittest
from unittest.mock import patch
from app.agents.coding.debugging import looks_like_code,extract_code,diagnose
from app.orchestrator.routing import route
from app.orchestrator.intelligence import safe_error,generate

class DebuggingTests(unittest.TestCase):
    def test_raw_even_odd_code_detected(self):
        code='n = int(input("Enter a number: ")) if n % 2 == 0: print("Even") else: print("Odd)'
        self.assertTrue(looks_like_code(code))
        with patch('app.orchestrator.routing.generate',side_effect=AssertionError('Router should not call AI')):
            self.assertEqual(route(code)['selected_agents'],['coding'])
    def test_fenced_indentation_preserved(self):
        code='if True:\n    print("hello")'
        self.assertEqual(extract_code('Find this error\n```python\n'+code+'\n```'),code)
    def test_missing_quote_is_reported(self):
        result=diagnose('n = 2\nprint("Odd)')
        self.assertFalse(result['valid_syntax']);self.assertIn('line 2',result['message'])
    def test_code_is_never_executed(self):
        result=diagnose('print("hello")\nraise Exception("do not execute")')
        self.assertTrue(result['valid_syntax']);self.assertIn('not been tested',result['message'])
    def test_prose_does_not_become_debugging(self):
        self.assertFalse(looks_like_code('Explain recursion using a simple story'))
    def test_errors_redact_keys(self):
        with patch.dict(os.environ,{'GEMINI_API_KEY':'private-value'},clear=True):
            message=safe_error('gemini',RuntimeError('bad key private-value https://host/?key=another-secret&x=1'))
        self.assertNotIn('private-value',message);self.assertNotIn('another-secret',message)
    def test_missing_credentials_have_explicit_message(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(RuntimeError,'No AI provider key'):
                generate('hello')
if __name__=='__main__':unittest.main()
