"""Course completion comes from graded lesson quizzes, never from opening media."""
def lesson_key(step):
    return str(step.get('order') or '')+':'+str(step.get('concept') or step.get('title') or '')[:140]

def annotate_plan(plan,attempts):
    result=dict(plan);latest={}
    for a in sorted(attempts,key=lambda a:str(a.get('createdAt','')),reverse=True):
        if a.get('courseTopic')!=plan.get('topic') or not a.get('lessonKey'):continue
        latest.setdefault(a['lessonKey'],a)
    # Module order can change when missing curriculum modules are restored.
    by_concept={}
    for record in sorted(latest.values(),key=lambda a:str(a.get('createdAt','')),reverse=True):
        by_concept.setdefault(record['lessonKey'].partition(':')[2],record)
    states={}
    for step in plan.get('steps') or []:
        key=lesson_key(step);record=latest.get(key) or by_concept.get(key.partition(':')[2])
        states[key]={'attempted':bool(record),'passed':bool(record and record.get('passed')),'score':record.get('score') if record else None}
    completed=sum(1 for s in states.values() if s['passed']);total=len(states)
    attempted=sum(1 for state in states.values() if state['attempted'])
    result['quizProgress']={'lessons':states,'completed':completed,'attempted':attempted,'total':total,
        'attemptPercentage':round(attempted*100/total) if total else 0,
        'percentage':round(completed*100/total) if total else 0}
    return result
