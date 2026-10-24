"""Local FastAPI adapter for the existing PHSS services."""
from pathlib import Path
from contextlib import contextmanager
import logging, os, json
from time import perf_counter
from dataclasses import asdict
from typing import Annotated
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env',override=False)
from backend.provider_policy import configure_provider_bounds
configure_provider_bounds()
from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Request
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from backend.service import Application, public
from app.persistence.streamlit_state import save_state
from app.persistence.sqlite_store import StaleSnapshotError
from app.persistence.research_document_store import StaleDocumentError

class Profile(BaseModel): name:str=Field(min_length=1,max_length=100)
class Query(BaseModel): text:str=Field(min_length=1,max_length=8000)
class Code(BaseModel): code:str=Field(max_length=100000)
class ReviewDraft(Code): context:str=Field(default='',max_length=8000)
class Answer(BaseModel): answer:str=Field(min_length=1,max_length=20000); question_id:str|None=None
class Practice(BaseModel): count:int=Field(default=3,ge=1,le=10)
class Search(BaseModel): topic:str=Field(min_length=1,max_length=500); target:int=Field(default=20,ge=1)
class Selection(BaseModel): ids:list[str]=Field(max_length=200); selected:bool=True
class Report(BaseModel):
    title:str=Field(default='Research Analysis Report',max_length=200)
    topic:str=Field(default='',max_length=500)
    ids:list[str]=Field(default_factory=list,max_length=100)
    sections:list[str]=Field(default_factory=lambda:['title','references','overviews','objectives','methods','evaluation','comparison','themes','differences','gaps','directions','limitations'],max_length=12)
    allow_partial:bool=False
    metadata_only:bool=False

class BodyLimit:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        maximum=210*1024*1024 if scope['path'].endswith('/upload') else 512*1024
        total=0;started=False
        async def bounded_receive():
            nonlocal total
            message=await receive();total+=len(message.get('body',b''))
            if total>maximum:raise OverflowError('Request exceeds configured transport limit.')
            return message
        async def observed_send(message):
            nonlocal started
            if message['type']=='http.response.start':started=True
            await send(message)
        try:await self.app(scope,bounded_receive,observed_send)
        except OverflowError:
            if started:raise
            await JSONResponse({'detail':'Request exceeds configured transport limit.'},413)(scope,receive,send)

def create_app(application=None):
    api=FastAPI(title='PHSS Web API',version='1.0.0')
    service=application or Application()
    api.state.service=service
    @api.middleware('http')
    async def server_timing(request,call_next):
        started=perf_counter()
        response=await call_next(request)
        response.headers['Server-Timing']=f'app;dur={(perf_counter()-started)*1000:.1f}'
        return response
    api.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5173','http://localhost:5173'],allow_methods=['GET','POST','PUT'],allow_headers=['Content-Type','X-Revision'])
    api.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])
    api.add_middleware(BodyLimit)
    @api.exception_handler(ValueError)
    async def invalid(request,exc):return JSONResponse({'detail':str(exc)[:500]},400)
    @api.exception_handler(StaleSnapshotError)
    @api.exception_handler(StaleDocumentError)
    async def stale(request,exc):return JSONResponse({'detail':'Saved work changed. Refresh before retrying.'},409)
    @api.exception_handler(Exception)
    async def failure(request,exc):
        logging.getLogger('phss').error('Workflow failed (%s)',type(exc).__name__)
        return JSONResponse({'detail':'The activity could not finish. Saved work is retained; refresh and retry explicitly. Check server provider configuration.'},503)
    @contextmanager
    def state(identity,revision=None,wait=False):
        acquired=service.lock.acquire(timeout=5) if wait else service.lock.acquire(blocking=False)
        if not acquired:raise HTTPException(409,'Another operation is running. Wait, then refresh.')
        try:
            if not any(p[0]==identity for p in service.store.list_profiles()):raise HTTPException(404,'Unknown student profile.')
            s=service.load(identity)
            if revision is not None and revision!=s['_persistence_revision']:raise HTTPException(409,'This page is stale. Refresh before retrying.')
            yield s
        finally:service.lock.release()
    @api.get('/api/health')
    def health():return dict(status='ok',provider_configured=bool(os.getenv('GEMINI_API_KEY')),mode='local profiles; no authentication')
    @api.get('/api/coding/topics')
    def coding_topics():
        from app.coding_agent.verified_exercises import VERIFIED_CONCEPTS
        return list(VERIFIED_CONCEPTS)
    @api.get('/api/topics')
    def topics():
        from app.learning_agent.topic_bank import LearningTopicBank
        return public(LearningTopicBank().all_topics())
    @api.get('/api/profiles')
    def profiles():return [dict(id=i,name=n) for i,n in service.store.list_profiles()]
    @api.post('/api/profiles',status_code=201)
    def profile(body:Profile):
        with service.lock:return dict(id=service.store.create_profile(body.name),name=body.name)
    @api.get('/api/students/{identity}')
    def get_state(identity:str):
        with state(identity,wait=True) as s:return service.view(s)
    def mutate(identity,revision,action):
        with state(identity,revision) as s:
            if s.get('_assessment_pending') and getattr(action,'__name__','')!='resume_action':
                raise HTTPException(409,'Resume the interrupted assessment before another action.')
            action(s);save_state(s);return service.view(s)
    @api.post('/api/students/{identity}/query')
    def query(identity:str,body:Query,x_revision:int|None=Header(default=None)):return mutate(identity,x_revision,lambda s:service.query(s,body.text))
    @api.post('/api/students/{identity}/prepare')
    def prepare(identity:str,x_revision:int|None=Header(default=None)):return mutate(identity,x_revision,lambda s:service.prepare(s,retry=True))
    @api.post('/api/students/{identity}/continue')
    def continue_(identity:str,x_revision:int|None=Header(default=None)):return mutate(identity,x_revision,service.continue_plan)
    @api.post('/api/students/{identity}/resume')
    def resume(identity:str,x_revision:int|None=Header(default=None)):
        def resume_action(s):service.resume(s)
        return mutate(identity,x_revision,resume_action)
    @api.post('/api/students/{identity}/practice')
    def practice(identity:str,body:Practice,x_revision:int|None=Header(default=None)):return mutate(identity,x_revision,lambda s:service.practice_start(s,body.count))
    @api.post('/api/students/{identity}/answer')
    def answer(identity:str,body:Answer,x_revision:int|None=Header(default=None)):return mutate(identity,x_revision,lambda s:service.practice_answer(s,body.answer,body.question_id))
    @api.put('/api/students/{identity}/draft')
    def draft(identity:str,body:Code,x_revision:int|None=Header(default=None)):
        def action(s):s['advanced_coding_editor']=body.code
        return mutate(identity,x_revision,action)
    @api.post('/api/students/{identity}/code')
    def submit(identity:str,body:Code,x_revision:int|None=Header(default=None)):return mutate(identity,x_revision,lambda s:service.code_submit(s,body.code))
    @api.post('/api/students/{identity}/hint')
    def hint(identity:str,body:Code,x_revision:int|None=Header(default=None)):return mutate(identity,x_revision,lambda s:service.hint(s,body.code))
    @api.post('/api/students/{identity}/review')
    def review(identity:str,x_revision:int|None=Header(default=None)):return mutate(identity,x_revision,service.review)
    @api.post('/api/students/{identity}/code-review/open')
    def open_review(identity:str,x_revision:int|None=Header(default=None)):
        return mutate(identity,x_revision,lambda s:service.open_code_review(s))
    @api.put('/api/students/{identity}/code-review/draft')
    def review_draft(identity:str,body:ReviewDraft,x_revision:int|None=Header(default=None)):
        return mutate(identity,x_revision,lambda s:service.save_code_review(s,body.code,body.context))
    @api.post('/api/students/{identity}/code-review/check')
    def check_review(identity:str,body:ReviewDraft,x_revision:int|None=Header(default=None)):
        def action(s):
            service.save_code_review(s,body.code,body.context)
            service.check_code_review(s)
        return mutate(identity,x_revision,action)
    @api.post('/api/students/{identity}/diagnostic')
    def diagnostic(identity:str,x_revision:int|None=Header(default=None)):return mutate(identity,x_revision,lambda s:service.diagnostic(s))
    @api.post('/api/students/{identity}/diagnostic/answer')
    def diagnostic_answer(identity:str,body:Answer,x_revision:int|None=Header(default=None)):return mutate(identity,x_revision,lambda s:service.diagnostic(s,body.answer))
    @api.get('/api/students/{identity}/research')
    def research(identity:str):
        with state(identity,wait=True) as s:return service.research_view(s)
    @api.post('/api/students/{identity}/research/search')
    def search(identity:str,body:Search):
        with state(identity) as s:
            session=service.search(s);session.start(body.topic,body.target);session.fetch_next();return service.research_view(s)
    @api.post('/api/students/{identity}/research/next')
    def next_page(identity:str):
        with state(identity) as s:service.search(s).fetch_next();return service.research_view(s)
    @api.post('/api/students/{identity}/research/add')
    def add(identity:str,body:Selection):
        from app.research_agent.models import ResearchPaper
        with state(identity) as s:
            search=service.search(s);record,_=search.load()
            entries={e['id']:e for e in (record or {}).get('results',[])}
            if set(body.ids)-entries.keys():raise ValueError('Select papers from your saved search.')
            documents=service.collection(s).documents
            for i in body.ids:
                documents.add_paper(identity,ResearchPaper(**entries[i]['paper']));search.select(i,True)
            return service.research_view(s)
    @api.post('/api/students/{identity}/research/upload')
    def upload(identity:str,files:Annotated[list[UploadFile],File()]):
        with state(identity) as s:
            collection=service.collection(s);maximum=collection.limits.max_file_bytes
            if len(files)>collection.limits.max_documents:raise HTTPException(413,'Upload count exceeds collection limit.')
            outcomes=[]
            for file in files:
                try:
                    content=file.file.read(maximum+1)
                    if len(content)>maximum:raise ValueError('PDF exceeds configured file size limit.')
                    outcomes.append(dict(filename=file.filename,result=collection.documents.pdfs.add(identity,Path((file.filename or '').replace('\\','/')).name,content,collection.limits)))
                except ValueError as exc:outcomes.append(dict(filename=file.filename,error=str(exc)))
                finally:file.file.close()
            return dict(outcomes=outcomes,collection=service.research_view(s))
    @api.post('/api/students/{identity}/research/select')
    def select(identity:str,body:Selection):
        with state(identity) as s:
            c=service.collection(s)
            for i in body.ids:c.documents.get(identity,i)
            for i in body.ids:c.select(i,body.selected)
            return service.research_view(s)
    @api.post('/api/students/{identity}/research/remove')
    def remove(identity:str,body:Selection):
        with state(identity) as s:
            collection=service.collection(s)
            for i in body.ids:collection.documents.get(identity,i)
            for i in body.ids:collection.remove(i)
            return service.research_view(s)
    @api.post('/api/students/{identity}/research/extract')
    def extract(identity:str):
        with state(identity) as s:service.collection(s).extract_batch();return service.research_view(s)
    @api.post('/api/students/{identity}/research/analyze')
    def analyze(identity:str):
        with state(identity) as s:service.collection(s).analyze_batch();return service.research_view(s)
    @api.post('/api/students/{identity}/research/prepare-report')
    def prepare_report(identity:str):
        with state(identity) as s:
            collection=service.collection(s)
            collection.extract_batch(selected_only=True)
            collection.analyze_batch()
            return service.research_view(s)
    @api.post('/api/students/{identity}/research/question')
    def research_question(identity:str,x_revision:int|None=Header(default=None)):return mutate(identity,x_revision,service.research_assess)
    @api.post('/api/students/{identity}/research/answer')
    def research_answer(identity:str,body:Answer,x_revision:int|None=Header(default=None)):return mutate(identity,x_revision,lambda s:service.research_answer(s,body.answer))
    @api.post('/api/students/{identity}/research/report/{format}')
    def report(identity:str,format:str,body:Report):
        from app.research_agent.research_report import report_sources
        from backend.research_reports import validate_export,readable_docx,readable_markdown
        with state(identity) as s:
            docs=service.collection(s).list();sources=report_sources(docs)
            if body.ids:
                if set(body.ids)-{x['id'] for x in sources}:raise ValueError('Report sources must be selected sources in this profile.')
                sources=[x for x in sources if x['id'] in body.ids]
                docs=[d for d in docs if d['document_id'] in body.ids]
            if len(sources)>service.search(s).limits.max_report_sources:raise ValueError('Report source limit exceeded.')
            if not sources:raise ValueError('Select at least one research source.')
            if format not in {'docx','md'}:raise HTTPException(404,'Unsupported report format.')
            try:status=validate_export(docs,body.sections,body.allow_partial,body.metadata_only)
            except ValueError as exc:raise HTTPException(409,str(exc)) from exc
            options=dict(partial=not status['ready'] and not body.metadata_only,metadata_only=body.metadata_only)
            preferences=json.dumps(dict(title=body.title,topic=body.topic,sections=body.sections,sources=[x['id'] for x in sources]))
            with service.store._connection() as db:
                db.execute('INSERT INTO research_report_preferences VALUES(?,?,1) ON CONFLICT(student_id) DO UPDATE SET record=excluded.record,revision=revision+1',(identity,preferences))
            filename='source-bibliography' if body.metadata_only else 'research-report'
            if format=='docx':
                return Response(readable_docx(body.title,body.topic,sources,body.sections,**options),
                    media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    headers={'Content-Disposition':f'attachment; filename="{filename}.docx"'})
            return Response(readable_markdown(body.title,body.topic,sources,body.sections,**options),
                media_type='text/markdown',headers={'Content-Disposition':f'attachment; filename="{filename}.md"'})
    @api.get('/{path:path}',include_in_schema=False)
    def frontend(path:str):
        if path.startswith('api/'):raise HTTPException(404,'Unknown API route.')
        root=ROOT/'frontend/dist';file=(root/path).resolve()
        if not file.is_relative_to(root.resolve()):raise HTTPException(404)
        if file.is_file():return FileResponse(file)
        if (root/'index.html').exists():return FileResponse(root/'index.html')
        return JSONResponse({'detail':'Frontend not built. Run npm.cmd run build in frontend.'},404)
    return api

app=create_app()
