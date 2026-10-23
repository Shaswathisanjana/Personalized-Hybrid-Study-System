"""Offline API integration: real services, controlled provider boundaries only."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile
import socket
import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.service import Application
from test_student_journey_streamlit import RoutedOfflineOrchestrator
from test_unified_query_refinement import real_router, linked_list_package
from test_research_search_collection import PagedFixture, synthetic_paper
from test_verified_coding_catalog import SOLUTIONS
import test_verified_coding_catalog as catalog
from app.coding_agent.open_topic import OpenTopicGenerator
from pdf_collection_test_fixtures import make_pdf, ExtractiveAnalyzer

class Runtime(RoutedOfflineOrchestrator):
    route=staticmethod(real_router)

@pytest.fixture
def client(tmp_path):
    original_connect=socket.socket.connect
    def denied(sock,address):
        if isinstance(address,tuple) and address[0] in ('127.0.0.1','::1'):return original_connect(sock,address)
        raise AssertionError('External network forbidden in offline API suite')
    with patch('socket.socket.connect',denied),patch('app.research_agent.search_session.AcademicPaperSearch',lambda: PagedFixture([[synthetic_paper(i) for i in range(7)]])),patch('app.coding_agent.integrated_workflow.CodingEvaluator',catalog.EvaluationGuardrailTests().evaluator),patch('app.coding_agent.open_topic.OpenTopicGenerator',lambda **kw:OpenTopicGenerator(provider=lambda **_:linked_list_package(),**kw)),patch('app.research_agent.collection_service.GroundedChunkAnalyzer',return_value=ExtractiveAnalyzer()):
        service=Application(tmp_path/'web.sqlite3',factory=Runtime)
        app=create_app(service)
        with TestClient(app,raise_server_exceptions=False) as c:
            c.student=c.post('/api/profiles',json={'name':'Alice'}).json()['id']
            c.other=c.post('/api/profiles',json={'name':'Bob'}).json()['id']
            c.base='/api/students/'+c.student
            c.service=service
            yield c

def post(c,path,body=None):
    response=c.post(c.base+path,json=body)
    assert response.status_code==200,response.text
    return response.json()

def test_profile_isolation_unknown_and_validation(client):
    c=client
    assert c.get(c.base).json()['student']['user_id']==c.student
    assert c.get('/api/students/absent').status_code==404
    assert c.post('/api/profiles',json={'name':''}).status_code==422
    post(c,'/query',{'text':'Teach me recursion'})
    assert c.get('/api/students/'+c.other).json()['plan'] is None

def test_real_learning_lesson_assessment_and_refresh(client):
    c=client;s=post(c,'/query',{'text':'Teach me recursion'})
    assert s['plan']['steps'][0]['agent']=='learning'
    assert s['lesson']['activity']['content']
    assert not s['evidence']
    s=post(c,'/practice',{'count':1});qid=s['practice']['current_question']['question_id']
    result=post(c,'/answer',{'answer':'answer','question_id':qid})
    assert result['student']['concepts']['Recursion']['attempts']==1
    again=post(c,'/answer',{'answer':'answer','question_id':qid})
    assert len(again['evidence'])==1
    restored=c.get(c.base).json();assert restored['student']['concepts']['Recursion']['attempts']==1
    # New Application instance simulates process restart using the same database.
    fresh=Application(c.service.store.path,factory=Runtime)
    assert len(fresh.view(fresh.load(c.student))['evidence'])==1

def test_custom_coding_enters_actual_editor_package_and_hint_recovery(client):
    c=client;s=post(c,'/query',{'text':'Give me a coding problem on linked lists'})
    assert s['exercise']['task']['concept_name']=='linked lists'
    code='def node_values(node):\n    return []\n'
    response=c.put(c.base+'/draft',json={'code':code});assert response.status_code==200
    s=post(c,'/hint',{'code':code});assert len(s['hints'])==1
    assert c.get(c.base).json()['code']==code
    assert not s['evidence']

def test_real_code_execution_submission_deduplication(client):
    c=client
    post(c,'/query',{'text':'Teach me recursion and then give me coding practice'})
    post(c,'/continue')
    exercise=c.get(c.base).json()['exercise'];level=exercise['task']['difficulty']
    code=SOLUTIONS[('Recursion',level)]
    s=post(c,'/code',{'code':code});assert s['coding_result']['result']['evaluation']['test_results']
    n=len(s['evidence']);assert n==1
    assert len(post(c,'/code',{'code':code})['evidence'])==n
    assert c.get(c.base).json()['coding_result']

def test_multistep_plan_uses_updated_shared_cacm(client):
    c=client;s=post(c,'/query',{'text':'Teach me recursion and then give me coding practice'})
    assert [x['agent'] for x in s['plan']['steps']]==['learning','coding']
    s=post(c,'/practice',{'count':1})
    post(c,'/answer',{'answer':'answer','question_id':s['practice']['current_question']['question_id']})
    s=post(c,'/continue')
    assert s['plan']['index']==1 and s['exercise']
    assert s['observation']['attempts']==1
    assert s['plan']['steps'][0]['status']=='assessed'
    assert c.get(c.base).json()['plan']['index']==1

def test_ambiguity_persists_without_agent_execution(client):
    c=client;s=post(c,'/query',{'text':'Can you improve this?'})
    assert s['clarification'] and not s['plan'] and not s['evidence']
    assert c.get(c.base).json()['clarification']
    s=post(c,'/query',{'text':'Teach me recursion'})
    assert s['plan'] and s['clarification'] is None

def test_search_more_than_five_selection_duplicates_and_isolation(client):
    c=client;post(c,'/query',{'text':'Find research papers about agentic AI'})
    research=c.get(c.base+'/research').json()
    assert len(research['search']['results'])==7
    identities=[e['id'] for e in research['search']['results']]
    first=post(c,'/research/add',{'ids':identities});assert len(first['documents'])==7
    assert len(post(c,'/research/add',{'ids':identities})['documents'])==7
    assert all(d['record']['source_scope']=='abstract_only' for d in first['documents'])
    assert not c.get('/api/students/'+c.other+'/research').json()['documents']
    assert not c.get(c.base).json()['evidence']

def test_pdf_batch_recovery_real_extraction_and_corrupt_files(client):
    c=client
    files=[('files',(f'paper-{i}.pdf',make_pdf(i),'application/pdf')) for i in range(7)]
    response=c.post(c.base+'/research/upload',files=files)
    assert response.status_code==200,response.text
    assert len(response.json()['collection']['documents'])==7
    response=c.post(c.base+'/research/upload',files=[('files',('repeat.pdf',make_pdf(0),'application/pdf')),('files',('invalid.txt',b'no pdf','text/plain')),('files',('broken.pdf',b'%PDF-broken','application/pdf'))])
    assert response.status_code==200
    assert any(x.get('error') for x in response.json()['outcomes'])
    for _ in range(3):post(c,'/research/extract')
    docs=c.get(c.base+'/research').json()['documents']
    assert sum(d['record']['status']=='ready' for d in docs)==7
    assert any(d['filename']=='broken.pdf' and d['record']['status'] in ('rejected','extraction_error') and d['record']['warnings'] for d in docs)
    assert not c.get(c.base).json()['evidence']

def test_actual_docx_and_markdown_include_provenance(client):
    c=client
    c.post(c.base+'/research/upload',files=[('files',('paper.pdf',make_pdf(0),'application/pdf'))])
    post(c,'/research/extract');post(c,'/research/analyze')
    body={'title':'Evidence Report','topic':'Offline research','sections':['title','references','methods','limitations']}
    response=c.post(c.base+'/research/report/docx',json=body)
    assert response.status_code==200,response.text
    xml=ZipFile(BytesIO(response.content)).read('word/document.xml').decode()
    assert 'Evidence Report' in xml and 'page' in xml and 'chunk' in xml
    md=c.post(c.base+'/research/report/md',json=body)
    assert md.status_code==200 and 'page' in md.text
    assert not c.get(c.base).json()['evidence']

def test_stale_revision_rejected(client):
    c=client;initial=c.get(c.base).json()['revision']
    post(c,'/query',{'text':'Teach me recursion'})
    r=c.post(c.base+'/query',json={'text':'Teach me recursion'},headers={'X-Revision':str(initial)})
    assert r.status_code==409

def test_provider_failure_is_honest_and_recoverable(client):
    c=client
    with patch.object(Runtime,'_run_learning',side_effect=RuntimeError('provider offline')):
        s=post(c,'/query',{'text':'Teach me recursion'})
    assert s['plan']['steps'][0]['status']=='error'
    assert s['lesson'].get('kind')=='study_workflow' and not s['evidence']
    assert post(c,'/prepare')['plan']['steps'][0]['status']=='ready'

def test_unknown_api_route_is_not_frontend_html(client):
    assert client.get('/api/not-real').status_code==404


def test_interrupted_evaluation_recovers_without_duplicate_evidence(client):
    c=client
    post(c,'/query',{'text':'Teach me recursion'})
    s=post(c,'/practice',{'count':1});qid=s['practice']['current_question']['question_id']
    with patch('test_persistence_streamlit.OfflineEvaluator.evaluate',side_effect=RuntimeError('offline outage')):
        failed=c.post(c.base+'/answer',json={'answer':'answer','question_id':qid})
    assert failed.status_code==503
    assert c.get(c.base).json()['pending']['kind']=='learning'
    assert c.post(c.base+'/continue').status_code==409
    resumed=post(c,'/resume');assert resumed['pending'] is None and len(resumed['evidence'])==1
    assert c.get(c.base).json()['student']['concepts']['Recursion']['attempts']==1


def test_genuine_cross_agent_conflict_and_diagnostic_resolution(client):
    c=client
    post(c,'/query',{'text':'Teach me recursion and then give me coding practice'})
    s=post(c,'/practice',{'count':5})
    for _ in range(5):
        q=s['practice']['current_question']['question_id'];s=post(c,'/answer',{'answer':'answer','question_id':q})
    s=post(c,'/continue')
    s=post(c,'/code',{'code':s['exercise']['task']['starter_code']})
    assert s['observation']['has_conflict']
    assert c.post(c.base+'/continue').status_code==400
    s=post(c,'/diagnostic');assert s['diagnostic']
    s=post(c,'/diagnostic/answer',{'answer':'answer'})
    assert not s['observation']['has_conflict']
    assert not c.get(c.base).json()['observation']['has_conflict']


def test_research_comprehension_uses_analyzed_claims_and_updates_cacm(client):
    from app.research_agent.models import ResearchComprehensionQuestion,ResearchComprehensionEvaluation
    c=client
    post(c,'/query',{'text':'Find research papers about agentic AI'})
    r=c.get(c.base+'/research').json();post(c,'/research/add',{'ids':[r['search']['results'][0]['id']]})
    post(c,'/research/analyze')
    q=ResearchComprehensionQuestion('agentic AI','What does this source report?','answer','Controlled fixture')
    with patch('app.research_agent.assessment_service.ResearchComprehensionGenerator',return_value=SimpleNamespace(generate=lambda **_:q)):
        s=post(c,'/research/question')
    assert s['research_question'] and 'correct_answer' not in s['research_question']
    assert not s['evidence']
    with patch('app.research_agent.assessment_service.ResearchComprehensionEvaluator',return_value=SimpleNamespace(evaluate=lambda _:ResearchComprehensionEvaluation(True,1.0,.9,'Controlled fixture feedback'))):
        s=post(c,'/research/answer',{'answer':'answer'})
    assert len(s['evidence'])==1 and s['evidence'][0]['source_agent']=='research'
    assert len(post(c,'/research/answer',{'answer':'answer'})['evidence'])==1


def test_provider_search_failure_saved_for_explicit_retry(client):
    c=client
    provider=SimpleNamespace(search_page=lambda *_,**kw:(_ for _ in ()).throw(RuntimeError('Provider unavailable')))
    with patch('app.research_agent.search_session.AcademicPaperSearch',return_value=provider):
        r=post(c,'/research/search',{'topic':'arbitrary subject','target':12})
    assert r['search']['error'] and r['search']['results']==[]
    assert c.get(c.base+'/research').json()['search']['error']
    assert len(post(c,'/research/next')['search']['results'])==7


def test_unassessed_answer_keys_and_secrets_not_exposed(client):
    c=client;post(c,'/query',{'text':'Teach me recursion'})
    s=post(c,'/practice',{'count':1})
    assert 'correct_answer' not in s['practice']['current_question']
    from backend.service import public
    with patch.dict('os.environ',{'GEMINI_API_KEY':'controlled-secret-fixture'}):
        assert public('error controlled-secret-fixture')=='error [redacted]'


def test_web_transport_policy_bounds_sdk_without_network():
    from backend.provider_policy import BoundedClient,OriginalClient
    with patch.object(OriginalClient,'__init__',return_value=None) as constructor:
        BoundedClient(api_key='offline-not-real')
    options=constructor.call_args.kwargs['http_options']
    assert options.timeout==60000 and options.retry_options.attempts==2
    with patch.object(OriginalClient,'__init__',return_value=None) as constructor:
        BoundedClient(api_key='offline-not-real',http_options={'timeout':30000})
    assert constructor.call_args.kwargs['http_options'].timeout==30000
