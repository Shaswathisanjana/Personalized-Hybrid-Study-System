from unittest.mock import patch
from backend.tests.test_api import client,post
from app.coding_agent.verified_exercises import VERIFIED_CONCEPTS
from test_verified_coding_catalog import SOLUTIONS
import test_verified_coding_catalog as catalog


def exercise(c,topic='Arrays'):
    return post(c,'/query',{'text':'Give me a coding problem on '+topic})['exercise']


def test_verified_topic_catalog_and_switch_keeps_edited_draft(client):
    c=client;assert c.get('/api/coding/topics').json()==list(VERIFIED_CONCEPTS)
    a=exercise(c);draft='def find_max(nums):\n    return max(nums)\n'
    assert c.put(c.base+'/draft',json={'code':draft}).status_code==200
    b=exercise(c,'Strings');assert b['task']['concept_name']=='Strings'
    s=c.get(c.base).json();assert s['coding_saved_drafts']['arrays']['code']==draft
    assert not s['evidence']
    assert not c.get('/api/students/'+c.other).json()['coding_saved_drafts']


def test_original_code_submission_runs_tests_once_and_recovers_after_refresh(client):
    c=client;e=exercise(c);code=SOLUTIONS[('Arrays',e['task']['difficulty'])]
    s=post(c,'/code',{'code':code});assert s['coding_result']['result']['evaluation']['test_results']
    assert all(t['passed'] for t in s['coding_result']['result']['evaluation']['test_results'])
    assert len(s['evidence'])==1 and not s['pending']
    assert c.get(c.base).json()['code']==code
    assert len(post(c,'/code',{'code':code})['evidence'])==1


def test_provider_failure_keeps_draft_local_tests_and_recoverable_assessment(client):
    c=client;e=exercise(c);code=SOLUTIONS[('Arrays',e['task']['difficulty'])]
    evaluator=catalog.EvaluationGuardrailTests().evaluator()
    evaluator.client.models.generate_content=lambda **kwargs:(_ for _ in ()).throw(RuntimeError('offline provider'))
    with patch('app.coding_agent.integrated_workflow.CodingEvaluator',return_value=evaluator):
        response=c.post(c.base+'/code',json={'code':code})
    assert response.status_code==503,response.text
    s=c.get(c.base).json();assert s['code']==code and s['pending']['kind']=='coding'
    assert s['coding_execution']['execution']['test_results'] and not s['evidence']
    s=post(c,'/resume');assert s['coding_execution'] is None and not s['pending'] and len(s['evidence'])==1


def test_review_failure_does_not_remove_assessed_results_or_add_evidence(client):
    c=client;e=exercise(c);code=SOLUTIONS[('Arrays',e['task']['difficulty'])];post(c,'/code',{'code':code})
    with patch('app.coding_agent.guided_review_coordinator.GuidedCodeReviewCoordinator.review_submission',side_effect=RuntimeError('offline review')):
        s=post(c,'/review')
    assert s['coding_review_error'] and s['coding_result'] and len(s['evidence'])==1
    assert c.get(c.base).json()['coding_review_error']
