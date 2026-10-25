"""Read-only, source-bound next-practice decisions using the existing Coding Agent."""
import hashlib,json
from app.cognitive.concept_identity import concept_id
from app.coding_agent.open_topic import observe_action, exercise_signature
from app.coding_agent.verified_exercises import VERIFIED_CONCEPTS,get_verified_exercise



def recommend(state):
    plan=state.get('journey_workspace');record=state.get('advanced_coding_submission_record');exercise=state.get('advanced_coding_exercise')
    if (not plan or plan['index']>=len(plan['steps']) or plan['steps'][plan['index']]['agent']!='coding'
            or plan.get('coding_mode','practice')!='practice' or not record or not exercise or state.get('_assessment_pending')
            or concept_id(plan['concept'])!=concept_id(exercise.task.concept_name)):return None
    workflow=state['advanced_coding_controller'].workflow
    action=observe_action(workflow,exercise.task.concept_name)
    evaluation=record.result.evaluation
    failed=[test.test_name for test in evaluation.test_results if not test.passed]
    passed=sum(test.passed for test in evaluation.test_results)
    difficulty=action.difficulty
    levels=['easy','medium','hard']
    needs_revision=bool(failed or not evaluation.is_correct)
    reason=action.reason
    if needs_revision and levels.index(difficulty)>levels.index(exercise.task.difficulty):
        difficulty=exercise.task.difficulty
        reason+=' Keep practice at or below the current difficulty while the evaluated issues remain unresolved.'
    conflict=action.action_type=='diagnostic_coding'
    curated=next((name for name in VERIFIED_CONCEPTS if concept_id(name)==concept_id(exercise.task.concept_name)),None)
    candidate=get_verified_exercise(curated,difficulty) if curated and not conflict else None
    from backend.coding_history import completed_tasks
    completed=completed_tasks(state,exercise.task.concept_name)
    if candidate and not needs_revision and any(item['signature']==exercise_signature(candidate) for item in completed):
        candidate=None
    if conflict:mode,title='diagnostic','Resolve the cognitive conflict first'
    elif candidate and exercise_signature(candidate)!=exercise_signature(exercise):mode,title='catalogue',candidate.task.title
    elif needs_revision:mode,title='retry','Improve your current solution: '+exercise.task.title
    else:mode,title='variant','New '+difficulty+' practice on '+exercise.task.concept_name
    model=state['student'].find_concept(exercise.task.concept_name)
    focus=['Review failing supplied cases: '+', '.join(failed[:8])+'.'] if failed else []
    if evaluation.detected_misconceptions:focus.append('Evaluation-reported misconceptions: '+', '.join(evaluation.detected_misconceptions[:8])+'.')
    if needs_revision:reason+=' This is revision of an evaluated issue, not a newly completed exercise.'
    if not focus:focus.append('Use the last evaluation feedback to guide revision.' if needs_revision else 'Apply the concept to another task; passing supplied tests is not proof of universal correctness.')
    result=dict(source_submission_id=record.submission_id,topic=exercise.task.concept_name,difficulty=difficulty,
        policy_difficulty=action.difficulty,action=action.action_type,mode=mode,is_revision=needs_revision,title=title,reason=reason,focus=focus,
        passed_tests=passed,total_tests=len(evaluation.test_results),can_start=not conflict,
        mastery=model.mastery if model else None,confidence=model.confidence if model else None,
        current_exercise_signature=exercise_signature(exercise),attempts=model.attempts if model else 0)
    result['id']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result
