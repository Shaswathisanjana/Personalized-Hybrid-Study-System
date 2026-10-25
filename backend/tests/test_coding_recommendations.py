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


def test_reopening_solved_topic_does_not_reload_completed_catalogue_task(client):
    c=client;s=assessed(c);s=start(c,s)
    s=post(c,'/code',{'code':SOLUTIONS[('Arrays',s['exercise']['task']['difficulty'])]})
    title=s['exercise']['task']['title']
    # The default offline provider cannot supply an Arrays variant. This must
    # fail honestly, preserving the completed task, rather than return it as new.
    response=c.post(c.base+'/query',json={'text':'Give me a coding problem on Arrays'})
    assert response.status_code!=200, 'Solved catalogue exercise was silently reloaded as new'
    restored=c.get(c.base).json()
    assert restored['exercise']['task']['title']==title
    assert restored['coding_result']==s['coding_result']


def sum_package(difficulty):
    package=linked_list_package()
    package.update(title='Sum of Array Values',difficulty=difficulty,function_name='total_values',
        description='Return the sum of all integer array values.',input_output='Integer list in, integer sum out.',
        expected_behavior='Return zero for an empty list, otherwise the sum including negative values.',
        starter_code='def total_values(nums):\n    pass\n',
        reference_code='def total_values(nums):\n    total = 0\n    for value in nums:\n        total += value\n    return total\n',
        tests=[dict(name='empty',args=[[]],expected_output=0),dict(name='positive',args=[[1,2]],expected_output=3),
               dict(name='negative',args=[[-2,1]],expected_output=-1)])
    return package


def test_completed_catalogue_is_not_suggested_again_after_variant_and_restart(client):
    c=client;s=start(c,assessed(c));s=post(c,'/code',{'code':SOLUTIONS[('Arrays',s['exercise']['task']['difficulty'])]})
    package=sum_package(s['coding_recommendation']['difficulty'])
    with patch('app.coding_agent.open_topic.OpenTopicGenerator',lambda **kw:OpenTopicGenerator(provider=lambda **_:package,**kw)):
        s=start(c,s)
    s=post(c,'/code',{'code':package['reference_code']})
    assert s['coding_recommendation']['mode']=='variant', 'Must not cycle back to the solved catalogue task'
    fresh=Application(c.service.store.path,factory=Runtime);state=fresh.load(c.student)
    assert len(state['advanced_coding_completed_tasks'])==3
    assert fresh.view(state)['coding_recommendation']['mode']=='variant'
    with patch('app.coding_agent.open_topic.OpenTopicGenerator',lambda **kw:OpenTopicGenerator(provider=lambda **_:package,**kw)):
        response=c.post(c.base+'/coding/recommended-practice',json={'recommendation_id':s['coding_recommendation']['id']})
    assert response.status_code==400
    assert c.get(c.base).json()['exercise']==s['exercise']


def test_typed_next_uses_saved_recommendation_and_preserves_plan_and_draft(client):
    c=client;s=assessed(c);draft=s['code']+'# my saved notes\n'
    result=post(c,'/query',{'text':'Give me the next problem','coding_draft':draft})
    assert result['exercise']['task']['title']!=s['exercise']['task']['title']
    assert result['plan']['request_id']==s['plan']['request_id']
    assert result['plan']['index']==s['plan']['index']
    assert result['coding_saved_drafts']['arrays']['code']==draft
    assert result['student']==s['student'] and result['evidence']==s['evidence']
    assert result['coding_practice_focus']['source_submission_id']==s['coding_result']['submission_id']


def test_typed_next_requires_assessment_and_leaves_original_activity(client):
    c=client;s=post(c,'/query',{'text':'Give me a coding problem on Arrays'})
    response=c.post(c.base+'/query',json={'text':'Give me the next problem'})
    assert response.status_code==400 and 'Submit and evaluate' in response.json()['detail']
    restored=c.get(c.base).json()
    assert restored['exercise']==s['exercise'] and not restored['evidence']


def test_completed_history_does_not_affect_another_student(client):
    c=client;assessed(c)
    s=c.post('/api/students/'+c.other+'/query',json={'text':'Give me a coding problem on Arrays'}).json()
    assert s['exercise']['task']['difficulty']=='easy'
    assert not c.service.load(c.other).get('advanced_coding_completed_tasks')


def test_duplicate_contract_ignores_function_rename_and_test_order():
    package=linked_list_package();first=OpenTopicGenerator(provider=lambda **_:package).generate('linked lists','easy')
    renamed=deepcopy(package);renamed['title']='Traverse differently';renamed['function_name']='walk_nodes'
    renamed['starter_code']=renamed['starter_code'].replace('node_values','walk_nodes')
    renamed['reference_code']=renamed['reference_code'].replace('node_values','walk_nodes')
    renamed['tests'].reverse()
    with pytest.raises(PackageGenerationError):
        OpenTopicGenerator(provider=lambda **_:renamed,max_attempts=1).generate('linked lists','easy',avoid_signatures=[exercise_signature(first)])


def test_explicit_followup_fallback_uses_saved_context_without_changing_topic(client):
    from backend.coding_history import routing_request
    from app.orchestrator.query_router import QueryRouter
    c=client;assessed(c)
    query=routing_request(c.service.load(c.student),'Give me the next problem')
    route=QueryRouter.__new__(QueryRouter)._fallback_route(query)
    assert route.concept=='Arrays' and route.coding_mode=='next_practice'


def test_successful_reopening_uses_a_new_validated_package(client):
    c=client;s=start(c,assessed(c));s=post(c,'/code',{'code':SOLUTIONS[('Arrays',s['exercise']['task']['difficulty'])]})
    package=sum_package(s['coding_recommendation']['difficulty'])
    with patch('app.coding_agent.open_topic.OpenTopicGenerator',lambda **kw:OpenTopicGenerator(provider=lambda **_:package,**kw)):
        result=post(c,'/query',{'text':'Give me a coding problem on Arrays'})
    assert result['exercise']['task']['title']==package['title']
    assert result['student']==s['student'] and result['evidence']==s['evidence']


def test_old_profile_completed_tasks_recover_from_committed_receipts(client):
    from app.persistence.streamlit_state import save_state
    from backend.coding_history import completed_tasks
    c=client;s=start(c,assessed(c));s=post(c,'/code',{'code':SOLUTIONS[('Arrays',s['exercise']['task']['difficulty'])]})
    state=c.service.load(c.student);state.pop('advanced_coding_completed_tasks',None);save_state(state)
    fresh=Application(c.service.store.path,factory=Runtime);restored=fresh.load(c.student)
    history=completed_tasks(restored,'Arrays')
    assert len(history)==2
    assert {item['difficulty'] for item in history}=={'easy','hard'}
    assert fresh.view(restored)['student']==s['student']
    assert fresh.view(restored)['evidence']==s['evidence']


def test_completed_history_rejects_foreign_profile_receipts(client):
    from app.persistence.session_recovery import capture
    c=client;assessed(c);state=c.service.load(c.student)
    state['advanced_coding_completed_tasks'][0]['user_id']=c.other
    with pytest.raises(ValueError,match='completed coding history'):
        capture(state)
