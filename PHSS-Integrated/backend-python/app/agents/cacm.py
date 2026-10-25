"""Rebuild shared CACM from persisted evidence, scoped to the signed-in user."""
from dataclasses import asdict
from datetime import datetime
import re
from app.database.mongo import get_db
from smera_app.cognitive.models import StudentCognitiveModel
from smera_app.cognitive.evidence import LearningEvidence
from smera_app.cognitive.cognitive_engine import CognitiveEngine

def concept_key(value):
    return re.sub(r'\s+',' ',re.sub(r'[_-]+',' ',str(value).lower())).strip()[:250]

def replay(user_id, events):
    student,engine = StudentCognitiveModel(user_id=user_id),CognitiveEngine()
    seen=set(); provisional=0
    for item in sorted(events,key=lambda e:str(e.get('timestamp',''))):
        if item['id'] in seen: continue
        seen.add(item['id'])
        if not item.get('verified'):
            provisional+=1
            continue
        evidence=LearningEvidence(user_id=user_id,concept_name=concept_key(item['concept']),source_agent=item['agent'],evidence_type=item['kind'],performance=max(0,min(1,float(item['performance']))),difficulty=.5,reliability=.85)
        engine.process_evidence(student,evidence)
    concepts=[]
    for name,c in student.concepts.items():
        conflicts=engine.active_conflicts.get((user_id,name),[])
        concepts.append({'concept':name,'mastery':c.mastery,'confidence':c.confidence,'attempts':c.attempts,
            'misconceptions':c.misconceptions,'conflicts':[asdict(x) for x in conflicts],
            'next_action':'diagnostic' if conflicts else 'revision' if c.mastery < .7 else 'practice'})
    return {'concepts':concepts,'verifiedEvidence':len(seen)-provisional,'provisionalEvidence':provisional,
        'policy':'Smera CACM replay of graded quizzes and server-verified code. Viewing materials never raises mastery.'}

def snapshot(user_id):
    db=get_db(); events=[]
    for q in db.quiz_attempts.find({'userId':user_id}).sort('createdAt',-1).limit(500):
        total=q.get('totalQuestions',0)
        if not total: continue
        events.append({'id':'quiz:'+str(q['_id']),'concept':q.get('conceptName','General'),'agent':'learning','kind':'quiz',
            'verified':True,'performance':q.get('correctCount',0)/total,'timestamp':q.get('createdAt','')})
    for c in db.codingattempts.find({'userId':user_id}).sort('acceptedAt',-1).limit(500):
        topics=c.get('question',{}).get('topics') or [c.get('question',{}).get('topic','Coding')]
        for topic in topics:
            result=c.get('serverResult') or c.get('result') or {}
            events.append({'id':'code:'+str(c['_id'])+':'+topic,'concept':topic,'agent':'coding','kind':'code_submission',
                'verified':c.get('provenance')=='server_verified' and bool(c.get('serverResult')),
                'performance':1 if result.get('status')=='passed' else 0,'timestamp':c.get('verifiedAt') or c.get('acceptedAt','')})
    return replay(user_id,events)
