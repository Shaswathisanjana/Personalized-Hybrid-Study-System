"""HTTP-independent adapter. Existing services own all cognitive decisions."""
from pathlib import Path
from threading import RLock
from dataclasses import asdict, is_dataclass
from datetime import datetime, date
from enum import Enum
import os, json
from app.persistence.sqlite_store import SQLiteStudentStore
from app.persistence.streamlit_state import load_profile, save_state
from app.orchestrator.student_journey import StudentJourneyService
from app.orchestrator.study_workspace import start_workspace, prepare_active, ensure_learning, advance_workspace

from backend.practice_context import bind_practice, visible_practice

ROOT = Path(__file__).resolve().parents[1]

def public(value):
    if is_dataclass(value): return public(asdict(value))
    if isinstance(value, dict): return {str(k): public(v) for k,v in value.items()}
    if isinstance(value, (list, tuple, set)): return [public(v) for v in value]
    if isinstance(value, (datetime,date)): return value.isoformat()
    if isinstance(value, Enum): return value.value
    if isinstance(value,str):
        for name in ('GEMINI_API_KEY','YOUTUBE_API_KEY','OPENALEX_API_KEY'):
            key=os.getenv(name)
            if key:value=value.replace(key,'[redacted]')
        return value
    if value is None or isinstance(value,(int,float,bool)): return value
    raise TypeError(f'Unsupported API output: {type(value).__name__}')

class LazyOrchestrator:
    def __init__(self, engine): self.cognitive_engine, self._runtime = engine, None
    def __getattr__(self, key):
        from app.orchestrator.orchestrator_runtime import OrchestratorRuntime
        if self._runtime is None: self._runtime = OrchestratorRuntime(self.cognitive_engine)
        return getattr(self._runtime,key)

class Application:
    def __init__(self, path=None, factory=LazyOrchestrator):
        path=Path(path or ROOT/'data/student_state/phss.sqlite3').resolve()
        if not path.is_relative_to(ROOT) and factory is LazyOrchestrator:
            raise ValueError('Application database must be inside PHSS_Web_App.')
        self.store=SQLiteStudentStore(path)
        self.factory=factory
        self.lock=RLock()
    def load(self, identity):
        state={}
        load_profile(state,self.store,identity,self.factory)
        return state
    def view(self,s):
        student=s['student']; engine=s['orchestrator'].cognitive_engine
        plan=s.get('journey_workspace')
        concept=plan['concept'] if plan else None
        observation=StudentJourneyService(student,s['orchestrator']).observe(concept) if concept else None
        lesson=None
        result=s.get('last_result')
        if result:
            lesson=next((x.output for x in result.agent_results if x.agent=='learning'),None)
        from app.learning_agent.study_planner import LearningStudyPlanner
        study_plan=LearningStudyPlanner().create_plan(student,engine,concept) if concept else None
        session=visible_practice(s)
        from backend.coding_recommendations import recommend
        recommendation=recommend(s)
        output=public(dict(student=student,plan=plan,coding_recommendation=recommendation,coding_practice_focus=s.get('advanced_coding_practice_focus'),clarification=s.get('journey_clarification'),lesson=lesson,
            exercise=s.get('advanced_coding_exercise'),code=s.get('advanced_coding_editor',''),
            hints=s.get('advanced_coding_hint_history',[]),coding_result=s.get('advanced_coding_submission_record'),
            review=s.get('advanced_coding_guided_result'),coding_execution=s.get('advanced_coding_execution_preview'),coding_review_error=s.get('advanced_coding_review_error'),coding_saved_drafts=s.get('advanced_coding_topic_drafts',{}),code_review=s.get('standalone_code_review'),practice=session,feedback=s.get('practice_last_outcome') if session else None,
            research_question=s.get('research_assessment_question'),research_feedback=s.get('research_assessment_feedback'),
            diagnostic=s.get('learning_diagnostic_session'),diagnostic_outcome=s.get('learning_diagnostic_outcome'),
            conflicts=engine.active_conflicts,evidence=engine.evidence_store.get_all_evidence(),
            observation=observation,study_plan=study_plan,progress=s['learning_progress_tracker']._records,
            pending=s.get('_assessment_pending'),revision=s['_persistence_revision']))
        if output.get('exercise'):output['exercise'].pop('reference_code',None)
        for question in ((output.get('practice') or {}).get('current_question'),(output.get('diagnostic') or {}).get('question'),output.get('research_question')):
            if isinstance(question,dict):
                question.pop('correct_answer',None);question.pop('expected_answer',None);question.pop('explanation',None)
        return output
    def query(self,s,text):
        from app.orchestrator.query_router import ClarificationRequired, clarified_request
        pending=s.get('journey_clarification')
        query=clarified_request(text,pending,s['student'].user_id)
        try: result=StudentJourneyService(s['student'],s['orchestrator']).handle_request(query,defer_workflows=True)
        except ClarificationRequired as exc:
            s['journey_clarification']=dict(user_id=s['student'].user_id,query=text,question=exc.question,topic='')
            save_state(s); return
        s.pop('journey_clarification',None)
        s['last_result']=result; s['last_query']=text
        plan=start_workspace(s,result)
        plan['coding_mode']=getattr(result.route,'coding_mode','practice')
        save_state(s)
        self.prepare(s)
    def prepare(self,s,retry=False):
        step=prepare_active(s)
        if step is None:return
        if s.get('journey_clarification'):raise ValueError('Resolve the pending clarification first.')
        if step['agent']=='learning':
            bind_practice(s)
            save_state(s)
            ensure_learning(s,lambda:save_state(s),retry=retry)
        elif step['status']=='ready': return
        elif step['status'] in ('error','running') and not retry:
            raise ValueError('Preparation interrupted; retry explicitly.')
        else:
            step.update(status='running',error=''); save_state(s)
            try:
                if step['agent']=='coding':
                    if s['journey_workspace'].get('coding_mode')=='review':
                        self.open_code_review(s)
                        self.check_code_review(s)
                    else:self.coding_load(s,s['journey_workspace']['concept'])
                elif s['journey_workspace'].get('research_mode','search')=='search':
                    search=self.search(s)
                    search.start(s['journey_workspace']['concept'],min(10,search.limits.max_target,search.limits.max_results)); search.fetch_next()
                step['status']='ready'
            except Exception:
                step.update(status='error',error='Activity preparation failed. Retry explicitly; saved work is preserved.')
                save_state(s); raise
        save_state(s)
    def continue_plan(self,s):
        if s.get('_assessment_pending'):raise ValueError('Resume the interrupted assessment first.')
        advance_workspace(s);save_state(s);self.prepare(s)
    def coding_load(self,s,topic):
        from app.coding_agent.verified_exercises import get_verified_exercise
        from app.coding_agent.open_topic import OpenTopicGenerator, observe_action, normalize_topic
        from app.coding_agent.submission_controller import CodingSubmissionController
        from app.coding_agent.adaptive_hint_coordinator import MisconceptionAwareHintCoordinator
        workflow=StudentJourneyService(s['student'],s['orchestrator']).coding_workflow()
        topic=normalize_topic(topic)
        action=observe_action(workflow,topic)
        curated=StudentJourneyService.coding_concept(topic)
        exercise=(get_verified_exercise(curated,action.difficulty) if curated else OpenTopicGenerator(max_attempts=2).generate(topic,action.difficulty,'Python'))
        self.install_coding(s,exercise,workflow,topic)
    def install_coding(self,s,exercise,workflow,topic):
        from app.coding_agent.submission_controller import CodingSubmissionController
        from app.coding_agent.adaptive_hint_coordinator import MisconceptionAwareHintCoordinator
        previous=s.get('advanced_coding_exercise')
        previous_code=s.get('advanced_coding_editor','')
        if previous and previous_code.strip() and previous_code!=previous.task.starter_code:
            from app.cognitive.concept_identity import concept_id
            s.setdefault('advanced_coding_topic_drafts',{})[concept_id(previous.task.concept_name)]=dict(topic=previous.task.concept_name,title=previous.task.title,code=previous_code)
        s.update(advanced_coding_exercise=exercise,advanced_coding_loaded_concept=topic,
            advanced_coding_editor=exercise.task.starter_code,advanced_coding_hint_history=[],
            advanced_coding_hint_engine=MisconceptionAwareHintCoordinator(),
            advanced_coding_controller=CodingSubmissionController(workflow,exercise))
        for key in ('advanced_coding_submission_record','advanced_coding_submission_source','advanced_coding_guided_result','advanced_coding_execution_preview','advanced_coding_review_error','advanced_coding_practice_focus'):
            s.pop(key,None)
    def start_recommended_coding(self,s,recommendation_id,code=None):
        from backend.coding_recommendations import recommend,exercise_signature
        from app.coding_agent.open_topic import OpenTopicGenerator
        from app.coding_agent.verified_exercises import get_verified_exercise
        recommendation=recommend(s)
        if not recommendation or recommendation['id']!=recommendation_id:
            raise ValueError('This recommendation is no longer current. Refresh the evaluated activity.')
        if not recommendation['can_start']:raise ValueError('Resolve the cognitive conflict with the diagnostic first.')
        if code is not None:s['advanced_coding_editor']=code;save_state(s)
        exercise=s['advanced_coding_exercise'];workflow=s['advanced_coding_controller'].workflow
        if recommendation['mode']=='retry':
            for key in ('advanced_coding_submission_record','advanced_coding_guided_result','advanced_coding_review_error','advanced_coding_execution_preview'):s.pop(key,None)
        else:
            if recommendation['mode']=='catalogue':
                exercise=get_verified_exercise(recommendation['topic'],recommendation['difficulty'])
            else:
                context='Choose a different problem on the SAME topic, not a renamed copy. Previous title: '+exercise.task.title+'. Previous specification: '+exercise.task.description[:1400]+'. Practice focus: '+' '.join(recommendation['focus'])
                exercise=OpenTopicGenerator(max_attempts=2).generate(recommendation['topic'],recommendation['difficulty'],'Python',context=context,avoid_signature=exercise_signature(exercise),avoid_title=exercise.task.title)
            self.install_coding(s,exercise,workflow,recommendation['topic'])
        s['advanced_coding_practice_focus']=recommendation
        step=s['journey_workspace']['steps'][s['journey_workspace']['index']]
        from app.orchestrator.study_workspace import evidence_count
        step.update(status='ready',baseline=evidence_count(s,'coding',s['journey_workspace']['concept']))
        save_state(s)
    def code_submit(self,s,code):
        controller=s.get('advanced_coding_controller')
        if controller is None:raise ValueError('Prepare a coding exercise first.')
        if not isinstance(code,str) or not code.strip():raise ValueError('Please write Python code before submitting.')
        s['advanced_coding_editor']=code
        if code!=s.get('advanced_coding_submission_source'):
            for key in ('advanced_coding_submission_record','advanced_coding_guided_result','advanced_coding_review_error','advanced_coding_execution_preview'):s.pop(key,None)
        s['_assessment_pending']=dict(kind='coding',request={'code':code});save_state(s)
        try:record,_=controller.submit(code)
        except Exception:
            evaluator=controller.workflow.evaluator
            execution=getattr(evaluator,'last_execution_evidence',None) if evaluator else None
            if execution:
                s['advanced_coding_execution_preview']=dict(code=code,execution=execution,message='Local test results only. The full assessment did not finish; use Resume interrupted assessment to retry. These test results are not an additional mastery update.')
            save_state(s)
            raise
        s.pop('advanced_coding_execution_preview',None)
        s.update(advanced_coding_submission_record=record,advanced_coding_submission_source=code,advanced_coding_editor=code)
        s.pop('_assessment_pending',None);save_state(s)
    def hint(self,s,code):
        exercise=s.get('advanced_coding_exercise')
        if exercise is None:raise ValueError('Prepare a coding exercise first.')
        history=s.setdefault('advanced_coding_hint_history',[])
        if len(history)>=3:raise ValueError('All three hints have been shown.')
        result=s['advanced_coding_hint_engine'].get_next_hint(task=exercise.task,code=code,session_id=s['student'].user_id)
        history.append(result.hint);s['advanced_coding_editor']=code;save_state(s)
    def review(self,s):
        from app.coding_agent.guided_review_coordinator import GuidedCodeReviewCoordinator
        if not s.get('advanced_coding_submission_record'):raise ValueError('Submit original code first.')
        exercise=s['advanced_coding_exercise']
        try:
            result=GuidedCodeReviewCoordinator().review_submission(code=s['advanced_coding_submission_source'],
                problem_description=exercise.task.description,concept_name=exercise.task.concept_name,test_cases=exercise.test_cases)
            s['advanced_coding_guided_result']=result
            s.pop('advanced_coding_review_error',None)
        except Exception:
            s['advanced_coding_review_error']='AI review could not finish. Your submitted code and evaluated results are saved. Retry Review & verify correction later.'
        save_state(s)

    def open_code_review(self,s,code=None,context=''):
        from app.coding_agent.review_request import extract_review_code
        from app.coding_agent.code_review_engine import CodeReviewEngine
        plan=s.get('journey_workspace')
        if not plan or plan['index']>=len(plan['steps']) or plan['steps'][plan['index']]['agent']!='coding':
            raise ValueError('Start a coding request before opening a review.')
        if code is None:code=extract_review_code(s.get('last_query') or plan['query'])
        plan['coding_mode']='review'
        s['standalone_code_review']=dict(user_id=s['student'].user_id,code=code,context=context,
            status='draft',error='',result=None,structural=public(CodeReviewEngine().review(code)))
        save_state(s)
    def save_code_review(self,s,code,context):
        from app.coding_agent.code_review_engine import CodeReviewEngine
        review=s.get('standalone_code_review')
        if not review:raise ValueError('Open a code review first.')
        if review['code']!=code or review['context']!=context:
            review.update(code=code,context=context,status='draft',error='',result=None,
                structural=public(CodeReviewEngine().review(code)))
        save_state(s)
    def check_code_review(self,s):
        from app.coding_agent.guided_review_coordinator import GuidedCodeReviewCoordinator
        review=s.get('standalone_code_review')
        if not review:raise ValueError('Open a code review first.')
        if not review['code'].strip():
            review.update(status='draft',error='Paste the Python code you want checked. If there are multiple snippets, choose one.')
            save_state(s);return
        if review['status']=='ready':return  # Identical successful review is reusable after refresh.
        review.update(status='running',error='');save_state(s)
        try:
            result=GuidedCodeReviewCoordinator().review_submission(code=review['code'],
                problem_description=review['context'],concept_name=s['journey_workspace']['concept'],test_cases=[])
            review.update(status='ready',result=public(result))
        except Exception:
            review.update(status='error',error='AI review unavailable. Your pasted code and syntax inspection are saved. Retry explicitly.')
        save_state(s)
    def practice_start(self,s,count):
        bind_practice(s)
        save_state(s)
        existing=s.get('practice_session')
        if existing and not existing.is_complete:raise ValueError('Complete or resume the current assessment first.')
        plan=s.get('journey_workspace')
        if not plan:raise ValueError('Start a study request first.')
        result=s['orchestrator'].learning_runtime.start_practice_session(s['student'],plan['concept'],plan['query'],count)
        s['practice_session']=result.session
        s.pop('practice_last_outcome',None)
        save_state(s)
    def practice_answer(self,s,answer,question_id):
        session=visible_practice(s)
        if session is None:raise ValueError('Start adaptive practice for the current topic first.')
        known_ids={attempt.question.question_id for attempt in session.attempts}
        if session.current_question:known_ids.add(session.current_question.question_id)
        if question_id and question_id not in known_ids:raise ValueError('This question belongs to an earlier activity. Refresh the current quiz.')
        s['_assessment_pending']=dict(kind='learning',request=dict(answer=answer,question_id=question_id));save_state(s)
        outcome=s['orchestrator'].learning_runtime.submit_practice_session_answer(s['student'],session,answer,question_id=question_id)
        s['practice_last_outcome']=outcome
        if session.is_complete:
            s['learning_progress_tracker'].complete_practice_session(s['student'].user_id,session.concept_name,session.questions_completed,session.session_id)
        s.pop('_assessment_pending',None);save_state(s)
    def resume(self,s):
        pending=s.get('_assessment_pending')
        if not pending:raise ValueError('No interrupted assessment is saved.')
        if pending['kind']=='coding':self.code_submit(s,pending['request']['code'])
        elif pending['kind']=='learning':self.practice_answer(s,**pending['request'])
        elif pending['kind']=='diagnostic':self.diagnostic(s,pending['request']['answer'])
        elif pending['kind']=='research':self.research_answer(s,pending['request']['answer'])
    def diagnostic(self,s,answer=None):
        from app.learning_agent.diagnostic_bridge import LearningDiagnosticBridge
        bridge=s.get('learning_diagnostic_bridge')
        if bridge is None:
            bridge=LearningDiagnosticBridge(s['student'],s['orchestrator'].cognitive_engine,s['orchestrator'].learning_runtime)
            s['learning_diagnostic_bridge']=bridge
        if answer is None:
            s['learning_diagnostic_session']=bridge.start(s['journey_workspace']['concept'])
        else:
            session=s.get('learning_diagnostic_session')
            if session is None:raise ValueError('Start a diagnostic first.')
            s['_assessment_pending']=dict(kind='diagnostic',request={'answer':answer});save_state(s)
            s['learning_diagnostic_outcome']=bridge.submit_answer(session,answer)
            s.pop('_assessment_pending',None)
        save_state(s)
    def search(self,s):
        from app.research_agent.search_session import ResearchSearchSession
        return ResearchSearchSession(self.store,s['student'].user_id)
    def collection(self,s):
        from app.persistence.research_library_store import UnifiedResearchDocumentStore
        from app.research_agent.collection_service import ResearchCollectionService
        return ResearchCollectionService(self.store,s['student'].user_id,document_store=UnifiedResearchDocumentStore(self.store))
    def research_view(self,s):
        from app.research_agent.full_text_analysis import compare_collection
        from backend.research_reports import readiness
        from app.research_agent.docx_exporter import SECTIONS
        from app.research_agent.research_report import report_sources,evidence_groups
        from app.research_agent.collection_models import CollectionLimits
        from app.research_agent.search_session import SearchLimits
        docs=self.collection(s).list()
        with self.store._connection() as db:
            row=db.execute('SELECT record FROM research_report_preferences WHERE student_id=?',(s['student'].user_id,)).fetchone()
        preferences=json.loads(row[0]) if row else {}
        selected=[d for d in docs if d['record'].get('selected',True)]
        return public(dict(documents=docs,report_readiness=readiness(docs),preferences=preferences,search=self.search(s).load()[0],sections=SECTIONS,
            limits=dict(pdf=asdict(CollectionLimits.from_environment()),search=asdict(SearchLimits.from_environment())),
            thematic_evidence=evidence_groups(report_sources(selected)),comparison=compare_collection('Selected research collection',selected)))
    def research_assess(self,s):
        from app.research_agent.research_workflow import ResearchWorkflowResult
        from app.research_agent.assessment_service import ResearchAssessmentService
        from app.research_agent.full_text_analysis import document_claims
        from app.research_agent.models import ResearchPaper
        from app.research_agent.paper_summarizer import PaperSummary
        docs=[d for d in self.collection(s).list() if d['record'].get('selected',True) and d['record']['analysis']]
        if not docs:raise ValueError('Analyze selected research sources first.')
        # Existing assessment context accepts validated summaries; never invent fields.
        papers=[];summaries=[]
        mapping=dict(research_problem='research_problem',proposed_method='methodology',dataset='dataset',evaluation_metrics='evaluation_metrics',key_findings='findings',limitations='limitations')
        for d in docs:
            m=d['record']['metadata']; claims=document_claims(d); title=m.get('title') or d['filename']
            url=m.get('url') or 'phss-document:'+d['document_id']
            text=' '.join(c['text'] for c in d['record']['chunks'])
            p=ResearchPaper(title=title,authors=m.get('authors',[]),year=m.get('year'),abstract=text,url=url,source='Uploaded PDF' if not d['document_id'].startswith('academic:') else 'OpenAlex')
            summary=PaperSummary(title,p.authors,p.year,url,source_scope=d['record'].get('source_scope','full_text_excerpts'))
            for field,claim_field in mapping.items():
                if claims[claim_field]:
                    item=claims[claim_field][0];quote=item['quote']
                    scope='page '+str(item['page']) if item['page'] is not None else 'abstract-only'
                    setattr(summary,field,quote+' ['+scope+', chunk '+item['chunk_id']+']');summary.evidence_quotes[field]=quote
            papers.append(p);summaries.append(summary)
        import inspect
        fields=inspect.signature(ResearchWorkflowResult).parameters
        values=dict(topic=s['journey_workspace']['concept'],accepted_papers=papers,summaries=summaries)
        result=ResearchWorkflowResult(**{k:v for k,v in values.items() if k in fields})
        s['advanced_research_result']=result
        service=ResearchAssessmentService(StudentJourneyService(s['student'],s['orchestrator']).research_coordinator())
        s['research_assessment_service']=service
        s['research_assessment_question']=service.generate_question(result,s['journey_workspace']['concept']);save_state(s)
    def research_answer(self,s,answer):
        service=s.get('research_assessment_service')
        if service is None:raise ValueError('Generate a research assessment first.')
        s['_assessment_pending']=dict(kind='research',request={'answer':answer});save_state(s)
        s['research_assessment_feedback']=service.submit_answer(s['student'].user_id,s['research_assessment_question'],answer,resume=True)
        s.pop('_assessment_pending',None);save_state(s)
