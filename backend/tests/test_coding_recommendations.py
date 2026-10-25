"""Offline integration of evidence-driven coding recommendations and recovery."""
from copy import deepcopy
from unittest.mock import patch
import pytest
from backend.tests.test_api import client, post, Runtime
from backend.service import Application
from test_verified_coding_catalog import SOLUTIONS
from test_unified_query_refinement import linked_list_package
from app.coding_agent.open_topic import OpenTopicGenerator, PackageGenerationError, exercise_signature


def assessed(c,correct=True,topic='Arrays'):
    s=post(c,'/query',{'text':'Give me a coding problem on '+topic})
    exercise=s['exercise']
    code=SOLUTIONS[(topic,exercise['task']['difficulty'])] if correct else exercise['task']['starter_code']
    return post(c,'/code',{'code':code})


def start(c,s,**extra):
    return post(c,'/coding/recommended-practice',dict(recommendation_id=s['coding_recommendation']['id'],**extra))


def test_only_evaluated_practice_gets_recommendation(client):
    c=client
    s=post(c,'/query',{'text':'Give me a coding problem on Arrays'})
    assert s['coding_recommendation'] is None and not s['evidence']
    assert c.get(c.base).json()['coding_recommendation'] is None
    assert c.post(c.base+'/coding/recommended-practice',json={'recommendation_id':'0'*64}).status_code==400


def test_success_starts_real_policy_selected_exercise_without_mastery(client):
    c=client;s=assessed(c);r=s['coding_recommendation']
    assert r['mode']=='catalogue' and r['can_start']
    assert r['passed_tests']==r['total_tests']
    previous=s['exercise']['task'];student=deepcopy(s['student']);evidence=deepcopy(s['evidence'])
    edited=s['code']+'# retain my draft\n'
    result=start(c,s,code=edited)
    assert result['exercise']['task']['title']!=previous['title']
    assert result['exercise']['task']['difficulty']==r['difficulty']
    assert result['coding_saved_drafts']['arrays']['code']==edited
    assert result['student']==student and result['evidence']==evidence
    assert result['coding_practice_focus']['source_submission_id']==s['coding_result']['submission_id']
    assert result['coding_recommendation'] is None
    assert c.post(c.base+'/coding/recommended-practice',json={'recommendation_id':r['id']}).status_code==400


def test_failure_targeted_retry_and_duplicate_assessment_guard(client):
    c=client;s=assessed(c,False);r=s['coding_recommendation']
    assert r['mode']=='retry' and r['difficulty']==s['exercise']['task']['difficulty']
    assert r['passed_tests']<r['total_tests'] and 'failing supplied cases' in r['focus'][0]
    result=start(c,s,code=s['code'])
    assert result['exercise']==s['exercise'] and result['code']==s['code']
    assert result['coding_result'] is None
    assert result['student']==s['student'] and result['evidence']==s['evidence']
    again=post(c,'/code',{'code':s['code']})
    assert again['evidence']==s['evidence']
    corrected=post(c,'/code',{'code':SOLUTIONS[('Arrays',s['exercise']['task']['difficulty'])]})
    assert len(corrected['evidence'])==len(s['evidence'])+1
    assert corrected['coding_recommendation']['passed_tests']==corrected['coding_recommendation']['total_tests']


def test_recommendation_and_focus_survive_process_restart(client):
    c=client;s=assessed(c)
    fresh=Application(c.service.store.path,factory=Runtime)
    restored=fresh.view(fresh.load(c.student))
    assert restored['coding_recommendation']==s['coding_recommendation']
    result=start(c,s)
    fresh=Application(c.service.store.path,factory=Runtime)
    restored=fresh.view(fresh.load(c.student))
    assert restored['coding_practice_focus']==result['coding_practice_focus']
    assert restored['exercise']==result['exercise'] and restored['evidence']==result['evidence']


def test_foreign_profile_and_changed_topic_reject_old_recommendation(client):
    c=client;s=assessed(c);body={'recommendation_id':s['coding_recommendation']['id']}
    assert c.post('/api/students/'+c.other+'/coding/recommended-practice',json=body).status_code==400
    post(c,'/query',{'text':'Give me a coding problem on Strings'})
    assert c.post(c.base+'/coding/recommended-practice',json=body).status_code==400
    assert c.get('/api/students/'+c.other).json()['evidence']==[]


def test_custom_variant_failure_preserves_previous_work(client):
    c=client
    s=post(c,'/query',{'text':'Give me a coding problem on linked lists'})
    assert 'reference_code' not in s['exercise']
    package=linked_list_package()
    # This is the controlled fixture reference solution, not an API-exposed answer.
    s=post(c,'/code',{'code':package['reference_code']})
    assert s['coding_recommendation']['mode']=='variant'
    with patch('app.coding_agent.open_topic.OpenTopicGenerator') as generator:
        generator.return_value.generate.side_effect=PackageGenerationError('No validated different exercise.')
        response=c.post(c.base+'/coding/recommended-practice',json={'recommendation_id':s['coding_recommendation']['id'],'code':s['code']})
    assert response.status_code==400
    restored=c.get(c.base).json()
    for key in ('exercise','code','coding_result','student','evidence','coding_recommendation'):
        assert restored[key]==s[key]


def test_generator_rejects_cosmetically_renamed_previous_contract():
    package=linked_list_package();calls=[]
    def provider(**kwargs):calls.append(kwargs);return deepcopy(package)
    exercise=OpenTopicGenerator(provider=provider).generate('linked lists','easy')
    renamed=deepcopy(package);renamed['title']='A cosmetic new title'
    def repeated(**kwargs):calls.append(kwargs);return deepcopy(renamed)
    generator=OpenTopicGenerator(provider=repeated,max_attempts=2)
    with pytest.raises(PackageGenerationError):
        generator.generate('linked lists','easy',context='Practise traversal',avoid_signature=exercise_signature(exercise),avoid_title=exercise.task.title)
    assert len(calls)==3

def test_conflict_requires_existing_diagnostic_before_next_practice(client):
    c=client
    post(c,'/query',{'text':'Teach me recursion and then give me coding practice'})
    s=post(c,'/practice',{'count':5})
    for _ in range(5):
        s=post(c,'/answer',{'answer':'answer','question_id':s['practice']['current_question']['question_id']})
    s=post(c,'/continue');s=post(c,'/code',{'code':s['exercise']['task']['starter_code']})
    r=s['coding_recommendation'];assert r['mode']=='diagnostic' and not r['can_start']
    assert c.post(c.base+'/coding/recommended-practice',json={'recommendation_id':r['id']}).status_code==400
    post(c,'/diagnostic');s=post(c,'/diagnostic/answer',{'answer':'answer'})
    assert s['coding_recommendation']['can_start']
    assert s['coding_recommendation']['id']!=r['id']


def test_new_generated_variant_is_validated_and_does_not_update_mastery(client):
    c=client;s=post(c,'/query',{'text':'Give me a coding problem on linked lists'})
    s=post(c,'/code',{'code':linked_list_package()['reference_code']});r=s['coding_recommendation']
    package=linked_list_package()
    package.update(title='Count Linked List Nodes',difficulty=r['difficulty'],function_name='count_nodes',
        description='Count the nodes in a serialized linked list.',input_output='A node is null or [value,next_node]; return its node count.',
        expected_behavior='Return zero for an empty list, otherwise the number of nodes.',
        starter_code='def count_nodes(node):\n    pass\n',
        reference_code='def count_nodes(node):\n    count = 0\n    while node is not None:\n        count += 1\n        node = node[1]\n    return count\n',
        tests=[dict(name='empty',args=[None],expected_output=0),dict(name='one',args=[[3,None]],expected_output=1),dict(name='two',args=[[3,[4,None]]],expected_output=2)])
    with patch('app.coding_agent.open_topic.OpenTopicGenerator',lambda **kw:OpenTopicGenerator(provider=lambda **_:package,**kw)):
        result=start(c,s)
    assert result['exercise']['task']['title']=='Count Linked List Nodes'
    assert 'reference_code' not in result['exercise']
    assert result['evidence']==s['evidence'] and result['student']==s['student']


def test_standalone_review_hides_practice_recommendation(client):
    c=client;s=assessed(c)
    s=post(c,'/code-review/open',{})
    assert s['coding_recommendation'] is None


def test_pending_assessment_hides_recommendation(client):
    from app.persistence.streamlit_state import save_state
    c=client;assessed(c)
    state=c.service.load(c.student)
    state['_assessment_pending']={'kind':'coding','request':{'code':state['advanced_coding_editor']}}
    save_state(state)
    s=c.get(c.base).json()
    assert s['coding_recommendation'] is None and s['pending']
