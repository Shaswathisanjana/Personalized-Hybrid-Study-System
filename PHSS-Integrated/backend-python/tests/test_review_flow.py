import json,os,sys,types,weakref,unittest
from unittest.mock import patch
from app.agents.coding.review_service import review_submission
from app.orchestrator.intelligence import generate

class ReviewFlowTests(unittest.TestCase):
    def test_smera_review_returns_precise_concept_and_corrected_code(self):
        reply={'summary':'Restore statement boundaries and indentation.','issues':[{'category':'formatting_error','explanation':'The pasted statements are flattened.','hint':'Use one statement per line.','suggested_fix':'Restore indentation.','line_number':1}], 'learning_concept':'Two pointers on sorted arrays','corrected_code':'arr = [1, 2, 4, 6, 8, 9]\ntarget = 10\nleft, right = 0, len(arr)-1\nwhile left < right:\n    total = arr[left] + arr[right]\n    if total == target:\n        print(arr[left], arr[right])\n        break\n    elif total < target:\n        left += 1\n    else:\n        right -= 1'}
        result=review_submission('arr = [1,2,4,6,8,9] target=10 while left < right: print(total)',lambda p:reply)
        self.assertEqual(result['learning_concept'],'Two pointers on sorted arrays');self.assertIn('right -= 1',result['corrected_code']);self.assertFalse(result['correction_verified']);self.assertTrue(result['correction_syntax_checked'])
    def test_invalid_generated_correction_is_not_presented(self):
        with self.assertRaisesRegex(ValueError,'syntax check'):
            review_submission('print("hi)',lambda p:{'summary':'Fix quote','learning_concept':'Strings','issues':[{'category':'syntax_error'}],'corrected_code':'print("hi)'})
    def test_gemini_client_stays_alive_until_response(self):
        created=[]
        class Models:
            def __init__(self,client):self.client=weakref.ref(client)
            def generate_content(self,**kwargs):
                c=self.client();assert c is not None and not c.closed,'Client closed before request'
                return types.SimpleNamespace(text=json.dumps({'ok':True}))
        class Client:
            def __init__(self,**kwargs):self.closed=False;self.models=Models(self);created.append(weakref.ref(self))
            def close(self):self.closed=True
        google=types.ModuleType('google');google.genai=types.SimpleNamespace(Client=Client)
        with patch.dict(sys.modules,{'google':google}),patch.dict(os.environ,{'GEMINI_API_KEY':'unit-test-key','PREFER_PROVIDER':'gemini'},clear=True):
            self.assertTrue(generate('test')['ok'])
    def test_provider_failure_does_not_become_fake_correction(self):
        def unavailable(prompt):raise RuntimeError('Service unavailable')
        with self.assertRaisesRegex(RuntimeError,'Service unavailable'):
            review_submission('print("hi)',unavailable)
if __name__=='__main__':unittest.main()
