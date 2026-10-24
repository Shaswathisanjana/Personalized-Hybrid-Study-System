"""Topic-scoped web practice without changing cognitive assessment policies."""
from app.cognitive.concept_identity import concept_id


def current_topic(state):
    plan=state.get('journey_workspace')
    if not plan or plan['index']>=len(plan['steps']) or plan['steps'][plan['index']]['agent']!='learning':return None
    return concept_id(plan['concept'])


def visible_practice(state):
    session=state.get('practice_session')
    return session if session and concept_id(session.concept_name)==current_topic(state) else None


def bind_practice(state):
    topic=current_topic(state)
    if topic is None:raise ValueError('Open a learning activity before starting adaptive practice.')
    session=state.get('practice_session')
    if session and concept_id(session.concept_name)==topic:return
    cache=state.setdefault('practice_topic_sessions',{})
    if session:
        cache[concept_id(session.concept_name)]=dict(session=session,feedback=state.get('practice_last_outcome'))
    state.pop('practice_session',None);state.pop('practice_last_outcome',None)
    saved=cache.pop(topic,None)
    if saved:
        state['practice_session']=saved['session']
        if saved.get('feedback') is not None:state['practice_last_outcome']=saved['feedback']
