from copy import deepcopy
import pytest
from backend.tests.test_api import client,post,Runtime
from backend.service import Application
from app.persistence.streamlit_state import save_state


def test_new_topic_gets_own_question_and_resumes_old_topic_after_restart(client):
    c=client;post(c,'/query',{'text':'Teach me recursion'})
    a=post(c,'/practice',{'count':3})['practice'];qid=a['current_question']['question_id']
    assert a['current_question']['difficulty'] in {'easy','medium','hard'}
    b=post(c,'/query',{'text':'Teach me arrays'})
    assert b['practice'] is None and b['feedback'] is None and not b['evidence']
    b=post(c,'/practice',{'count':2})['practice']
    assert b['concept_name']=='Arrays' and b['current_question']['concept_name']=='Arrays'
    assert b['current_question']['question_id']!=qid
    assert c.get(c.base).json()['practice']['session_id']==b['session_id']
    fresh=Application(c.service.store.path,factory=Runtime);s=fresh.load(c.student)
    fresh.query(s,'Teach me recursion');view=fresh.view(s)
    assert view['practice']['session_id']==a['session_id']
    assert view['practice']['current_question']['question_id']==qid
    assert not view['evidence']
    fresh.query(s,'Teach me arrays');assert fresh.view(s)['practice']['session_id']==b['session_id']
    assert c.get('/api/students/'+c.other).json()['practice'] is None


def test_completed_feedback_stays_with_original_topic(client):
    c=client;post(c,'/query',{'text':'Teach me recursion'})
    q=post(c,'/practice',{'count':1})['practice']['current_question']
    a=post(c,'/answer',{'answer':'answer','question_id':q['question_id']});assert a['feedback']
    b=post(c,'/query',{'text':'Teach me arrays'});assert b['practice'] is None and b['feedback'] is None
    post(c,'/practice',{'count':1});a=post(c,'/query',{'text':'Teach me recursion'})
    assert a['feedback'] and a['practice']['current_question'] is None and len(a['evidence'])==1


def test_stale_old_topic_answer_rejected_without_pending_or_mastery(client):
    c=client;post(c,'/query',{'text':'Teach me recursion'})
    old=post(c,'/practice',{'count':2})['practice']['current_question']['question_id']
    post(c,'/query',{'text':'Teach me arrays'});post(c,'/practice',{'count':2})
    r=c.post(c.base+'/answer',json={'answer':'answer','question_id':old})
    assert r.status_code==400
    s=c.get(c.base).json();assert not s['pending'] and not s['evidence']
    assert s['practice']['current_question']['concept_name']=='Arrays'


def test_same_topic_keeps_unfinished_session(client):
    c=client;post(c,'/query',{'text':'Teach me recursion'})
    a=post(c,'/practice',{'count':3})['practice']
    b=post(c,'/query',{'text':'Teach me recursion'})['practice']
    assert a['session_id']==b['session_id'] and a['current_question']==b['current_question']
    assert c.post(c.base+'/practice',json={'count':3}).status_code==400


def test_legacy_stale_session_hidden_before_starting_current_topic(client):
    c=client;post(c,'/query',{'text':'Teach me recursion'});post(c,'/practice',{'count':3})
    s=c.service.load(c.student);s['journey_workspace']['concept']='Arrays';save_state(s)
    assert c.get(c.base).json()['practice'] is None
    b=post(c,'/practice',{'count':1})
    assert b['practice']['concept_name']=='Arrays'


def test_cached_session_rejects_cross_profile_ownership(client):
    c=client;post(c,'/query',{'text':'Teach me recursion'});post(c,'/practice',{'count':2})
    s=c.service.load(c.student);wrong=deepcopy(s['practice_session']);wrong.user_id=c.other
    s['practice_topic_sessions']={'recursion':{'session':wrong,'feedback':None}}
    with pytest.raises(ValueError,match='Cross-student'):save_state(s)
