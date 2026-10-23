"""Standalone review uses semantic routing and actual review/verification services offline."""
import json
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from backend.tests.test_api import client,post,Runtime
from backend.service import Application
from app.orchestrator.query_router import QueryRouter,QueryRoute
from app.persistence.state_codec import encode,decode
from app.coding_agent.review_request import extract_review_code,fallback_review_request
from app.coding_agent.ai_code_reviewer import AICodeReviewer
from test_unified_query_refinement import real_router

SOURCE='def fibonacci(n):\n    return n + 1\n'
REQUEST='Please check this code and suggest a correction.\n```python\n'+SOURCE+'```'
CORRECTION='def fibonacci(n):\n    if n < 2:\n        return n\n    return fibonacci(n - 1) + fibonacci(n - 2)\n'

def semantic_route(query):
    router=QueryRouter.__new__(QueryRouter)
    router.max_retries,router.retry_delay,router.model_name=0,0,'offline semantic fixture'
    payload=dict(concept='Fibonacci',intents=['code'],selected_agents=['coding'],
        coding_mode='review',needs_cognitive_tracking=False,reason='Review the supplied program, not new practice')
    router.client=SimpleNamespace(models=SimpleNamespace(generate_content=lambda **_:SimpleNamespace(text=json.dumps(payload))))
    return router.route(query)

def review_payload():
    return dict(summary='The function returns n + 1 rather than the intended Fibonacci number.',
        issues=[dict(category='logical_error',explanation='The recurrence is not implemented.',hint='Consider the base cases.',suggested_fix='Add base cases and the recurrence.',line_number=2)],
        corrected_code=CORRECTION,learning_concept='Recursion',correction_verified=True)

@pytest.fixture
def review_client(client):
    calls=[]
    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text=json.dumps(review_payload()))
    def reviewer():return AICodeReviewer(client=SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    with patch.object(Runtime,'route',staticmethod(semantic_route)),patch('app.coding_agent.guided_review_coordinator.AICodeReviewer',side_effect=reviewer),patch.object(Application,'coding_load',side_effect=AssertionError('Review must not generate an exercise')),patch('app.coding_agent.code_runner.ControlledCodeRunner.run_tests',side_effect=AssertionError('Standalone review must not execute code')):
        client.review_calls=calls
        yield client

def test_semantic_review_preserves_original_and_no_exercise_or_mastery(review_client):
    c=review_client;s=post(c,'/query',{'text':REQUEST})
    assert s['plan']['coding_mode']=='review'
    assert s['code_review']['code']==SOURCE.rstrip('\n')
    assert s['exercise'] is None and s['code_review']['status']=='ready'
    result=s['code_review']['result']
    assert result['review']['corrected_code']==CORRECTION
    assert result['review']['correction_verified'] is False
    assert result['correction_status']=='no_tests' and not result['verification']['all_tests_passed']
    assert not s['evidence'] and not s['student']['concepts']
    assert 'return n + 1' in c.review_calls[0]['contents']

def test_unfenced_request_does_not_put_question_into_python(review_client):
    c=review_client;query='num_terms = 5\nprint(num_terms)\n\nis this code correct'
    s=post(c,'/query',{'text':query})
    assert s['code_review']['code']=='num_terms = 5\nprint(num_terms)'
    assert s['code_review']['structural']['syntax_valid'] is True

def test_review_draft_refresh_restart_and_profile_isolation(review_client):
    c=review_client;post(c,'/query',{'text':REQUEST})
    draft={'code':'print(42)','context':'Print exactly 42.'}
    response=c.put(c.base+'/code-review/draft',json=draft)
    assert response.status_code==200,response.text
    s=c.get(c.base).json();assert s['code_review']['code']=='print(42)'
    assert s['code_review']['result'] is None and s['code_review']['status']=='draft'
    fresh=Application(c.service.store.path,factory=Runtime)
    assert fresh.view(fresh.load(c.student))['code_review']['context']==draft['context']
    assert c.get('/api/students/'+c.other).json()['code_review'] is None
    assert len(c.review_calls)==1

def test_success_reused_but_edit_is_reviewed_again(review_client):
    c=review_client;s=post(c,'/query',{'text':REQUEST})
    draft=dict(code=s['code_review']['code'],context='')
    post(c,'/code-review/check',draft);assert len(c.review_calls)==1
    draft['context']='Return the nth Fibonacci number, with F(0)=0 and F(1)=1.'
    s=post(c,'/code-review/check',draft)
    assert len(c.review_calls)==2 and draft['context'] in c.review_calls[1]['contents']
    assert not s['evidence']

def test_provider_failure_keeps_code_and_retries_explicitly(review_client):
    c=review_client
    with patch('app.coding_agent.guided_review_coordinator.AICodeReviewer',side_effect=RuntimeError('Provider offline')):
        s=post(c,'/query',{'text':REQUEST})
    assert s['code_review']['status']=='error' and s['code_review']['code']==SOURCE.rstrip('\n')
    assert s['code_review']['structural']['syntax_valid']
    c.get(c.base);assert len(c.review_calls)==0
    s=post(c,'/code-review/check',dict(code=s['code_review']['code'],context=''))
    assert s['code_review']['status']=='ready' and not s['evidence']

def test_syntax_errors_are_reported_without_executing(review_client):
    c=review_client;s=post(c,'/query',{'text':'Check this code.\n```python\ndef broken(:\n    pass\n```'})
    assert s['code_review']['structural']['syntax_valid'] is False
    assert s['code_review']['structural']['issues'][0]['category']=='syntax_error'
    assert not s['evidence']

def test_multiple_snippets_ask_for_one_instead_of_new_exercise(review_client):
    c=review_client;s=post(c,'/query',{'text':'Check these snippets\n```python\nprint(1)\n```\n```python\nprint(2)\n```'})
    assert s['code_review']['status']=='draft' and not s['code_review']['code']
    assert 'choose one' in s['code_review']['error'] and c.review_calls==[]
    assert s['exercise'] is None

def test_old_routes_default_to_practice_and_invalid_mode_rejected():
    raw=encode(QueryRoute('old','Recursion',[],['coding']))
    raw['fields'].pop('coding_mode')
    assert decode(raw).coding_mode=='practice'
    router=QueryRouter.__new__(QueryRouter)
    with pytest.raises(ValueError,match='coding workflow'):
        router._build_route('request',dict(concept='Python',selected_agents=['coding'],coding_mode='invented'))
    fallback=router._fallback_route('print(1)\n\nis this code correct')
    assert fallback.coding_mode=='review' and fallback.selected_agents==['coding']

def test_fenced_source_preserves_indentation_and_review_words_inside_strings():
    code='def f():\n    return "is this code correct"\n'
    assert extract_review_code('Review this\n```python\n'+code+'```')==code.rstrip('\n')
    assert not fallback_review_request('print("check my code")')

def test_practice_can_open_review_without_overwriting_exercise(client):
    c=client;s=post(c,'/query',{'text':'Give me a coding problem on linked lists'})
    exercise=s['exercise'];draft=s['code']
    s=post(c,'/code-review/open')
    assert s['plan']['coding_mode']=='review' and s['exercise']==exercise and s['code']==draft
    assert s['code_review']['code']=='' and not s['evidence']
