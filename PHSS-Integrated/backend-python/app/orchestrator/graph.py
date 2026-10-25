"""Multi-agent routing with contextual handoffs and partial-result isolation."""
from typing import Any, TypedDict
from urllib.parse import urlencode
from langgraph.graph import StateGraph, END
from app.orchestrator.routing import route
from app.orchestrator.intelligence import generate

class PHSSState(TypedDict, total=False):
    user_id: str
    message: str
    mode: str
    context: dict
    decision: dict
    result: dict[str, Any]

def classify(state):
    return {'decision': route(state['message'],state.get('mode','auto'),state.get('context'))}

def execute(state):
    from app.agents.learning.service import create_learning_plan
    from app.agents.research.service import search_papers
    from app.agents.cacm import snapshot
    topic = state['decision']['concept']
    try:
        cognitive = snapshot(state['user_id'])
    except Exception:
        cognitive = {'available':False,'message':'Cognitive history is temporarily unavailable; this response does not update mastery.'}
    outputs = []
    context = {'workspace':state.get('context',{}), 'cognitive':cognitive, 'previous_outputs':[]}
    from app.orchestrator.intents import is_practice_request
    for agent in state['decision']['selected_agents']:
        try:
            if agent == 'learning':
                # PHSS-Unified owns the learning pipeline. A separate explanation
                # provider must never prevent roadmap retrieval or generation.
                requested_level=state.get('context',{}).get('current_level') or 'beginner'
                if requested_level not in {'beginner','intermediate','advanced'}: requested_level='beginner'
                plan = create_learning_plan(state['user_id'],topic,requested_level,state['message'][:500])
                out = {'agent':agent,'success':True,'message':'Your learning roadmap is ready.',
                       'plan':plan.get('existing_plan') or plan}
            elif agent == 'research':
                research = search_papers(state['user_id'],topic,None,full_analysis=True)
                out = {'agent':agent,'success':True,'research':research,'message':'Research report ready.'}
            else:
                from app.agents.coding.review_service import review_submission
                from app.agents.coding.debugging import looks_like_code
                if is_practice_request(state['message']) and not looks_like_code(state['message']):
                    out = {'agent':agent,'success':True,'message':'Choose a matching question in your coding workspace.',
                           'workspace':'/coding/?'+urlencode({'topic':state['message']}),
                           'practice_request':state['message']}
                elif not looks_like_code(state['message']):
                    answer = generate('You are the Coding Agent. Answer this implementation or interview-practice request. Return {"explanation":"clear answer", "code":"Python implementation or starter code", "learning_concept":"precise topic", "practice_task":{"title":"task","description":"problem","starter_code":"code"}}. Do not invent a student submission or claim execution. Request: '+state['message']+'\nContext: '+str(context)[:18000])
                    topic = str(answer.get('learning_concept') or topic)[:250]
                    out = {'agent':agent,'success':True,'message':str(answer.get('explanation','')),'answer':answer,'workspace':'/coding/?'+urlencode({'topic':topic})}
                else:
                    try:
                        review = review_submission(state['message'])
                        topic = review['learning_concept'][:250]
                        out = {'agent':agent,'success':True,'message':review['summary'],'review':review,
                               'workspace':'/coding/?'+urlencode({'topic':topic})}
                    except (RuntimeError, ValueError) as exc:
                        out = {'agent':agent,'success':False,
                               'message':'The code-review service could not produce a correction. Your submission has not been assessed and no mastery change was made.',
                               'service_error':str(exc),'workspace':'/coding/'}
            outputs.append(out)
            context['previous_outputs'].append(out)
        except Exception as exc:
            outputs.append({'agent':agent,'success':False,'message':str(exc)[:700]})
    return {'result':{'agent':'orchestrator','topic':topic,'original_message':state['message'],'routing':state['decision'],'agent_results':outputs,'cognitive':cognitive,
        'message':' → '.join(state['decision']['selected_agents']),
        'handoffs':[{'agent':a,'topic':topic,'message':{'learning':'Explain '+topic+' using the current project context','coding':'Help me implement '+topic,'research':'Find research papers about '+topic}[a]} for a in ['learning','coding','research']]}}

def build_graph():
    graph=StateGraph(PHSSState)
    graph.add_node('classify',classify); graph.add_node('execute',execute)
    graph.set_entry_point('classify'); graph.add_edge('classify','execute'); graph.add_edge('execute',END)
    return graph.compile()

phss_graph=build_graph()

def run_orchestrator(user_id, message, mode='auto', context=None):
    return phss_graph.invoke({'user_id':user_id,'message':message,'mode':mode,'context':context or {}})['result']
