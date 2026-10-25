"""Smera semantic multi-agent contract, with its deterministic fallback."""
import re
from app.orchestrator.intelligence import generate
from app.orchestrator.intents import explicit_intent
from app.agents.coding.debugging import looks_like_code

VALID = {'learning', 'coding', 'research'}

def local_route(message):
    if looks_like_code(message):
        return {'concept':'Python code debugging','selected_agents':['coding'],'reason':'Python code detected; sent directly to the Coding Agent.','provider':'local'}
    q = message.lower()
    # Use Smera's actual fallback implementation without requiring a live client.
    try:
        from smera_app.orchestrator.query_router import QueryRouter
        decision = QueryRouter._fallback_route(QueryRouter.__new__(QueryRouter), message)
        agents, topic = decision.selected_agents, decision.concept
    except ImportError:
        agents, topic = [], message
    if agents == ['learning'] and not re.search(r'explain|teach|understand|learn|what is|how does|quiz', q):
        agents = []
    if re.search(r'\b(debug|code|coding|programming|implement|interview|leetcode|syntax|traceback)\b|```|def\s+\w+\(',q) and 'coding' not in agents:
        agents.append('coding')
    if re.search(r'\b(papers?|research|arxiv|literature|citations?)\b',q) and 'research' not in agents:
        agents.insert(0,'research')
    if re.search(r'explain|teach|understand|learn|what is|how does|roadmap',q) and 'learning' not in agents:
        agents.append('learning')
    positions = {
        'learning': re.search(r'teach|explain|understand|learn|roadmap|quiz',q),
        'coding': re.search(r'coding|code|debug|programming|implement|interview|leetcode',q),
        'research': re.search(r'papers?|research|literature|arxiv',q)
    }
    agents.sort(key=lambda a: positions[a].start() if positions[a] else len(q))
    topic = re.sub(r'^(teach me|explain|help me understand|find papers (?:on|about))\s+', '', topic, flags=re.I)
    topic = re.split(r'\s+and (?:then |give |help |explain|teach|implement)',topic,flags=re.I)[0]
    return {'concept': topic[:250], 'selected_agents': agents or ['learning'], 'reason':'Local routing fallback', 'provider':'local'}

def route(message, mode='auto', context=None):
    if mode not in VALID | {'auto'}:
        raise ValueError('Unsupported agent mode.')
    intent = explicit_intent(message)
    if mode == 'auto' and intent and not looks_like_code(message):
        return {'concept': message[:250], 'selected_agents':[intent], 'reason':'Explicit user intent', 'provider':'local'}
    fallback = local_route(message)
    if mode == 'auto' and looks_like_code(message):
        return fallback
    try:
        data = generate('Route this educational request. Return {"concept":"specific topic", "selected_agents":["learning"], "reason":"short reason"}. Agents: learning teaches any academic or practical subject, including English communication, languages, humanities and concepts/roadmaps, coding answers/debugs code and prepares interviews, research retrieves papers. Select multiple agents only when requested, in requested order. A doubt about a paper can go to learning without another search. Resolve pronouns using context.\nRequest: '+message+'\nContext: '+str(context or {}))
        agents = data.get('selected_agents')
        if not isinstance(agents,list) or not agents or any(a not in VALID for a in agents) or not isinstance(data.get('concept'),str) or not data['concept'].strip():
            raise ValueError('Invalid routing output')
        data = {'concept':data['concept'][:250], 'selected_agents':list(dict.fromkeys(agents)), 'reason':str(data.get('reason',''))[:500], 'provider':'semantic'}
    except (RuntimeError, ValueError, TypeError):
        data = fallback
    if mode != 'auto':
        data['selected_agents'] = [mode]
    return data
