"""Smera's actual structured reviewer, adapted to the unified provider layer."""
import ast
import json
from dataclasses import asdict
from types import SimpleNamespace
from smera_app.coding_agent.ai_code_reviewer import AICodeReviewer
from app.agents.coding.debugging import extract_code
from app.orchestrator.intelligence import generate

class ProviderBridge:
    @property
    def models(self):return self
    def generate_content(self,model,contents):
        data=generate(contents+'\nUse a precise learning_concept, such as Two pointers on sorted arrays, Loop termination, or Recursion base cases. Identify misconceptions only where supported by the submitted code; otherwise describe the concept involved without claiming a weakness. If code has lost line breaks, restore the intended formatting in corrected_code and distinguish formatting repair from a logic correction.')
        return SimpleNamespace(text=json.dumps(data))

def review_submission(message, generator=None):
    source=extract_code(message)
    client=ProviderBridge()
    if generator:
        client.generate_content=lambda model,contents:SimpleNamespace(text=json.dumps(generator(contents)))
    reviewer=AICodeReviewer(client=client,model_name='unified-provider')
    review=reviewer.review(source,problem_description=message)
    concept=review.learning_concept.strip() or 'Python program structure'
    correction=review.corrected_code.strip()
    if correction:
        try:ast.parse(correction)
        except SyntaxError:
            # Do not show a syntactically invalid generated patch as corrected code.
            raise ValueError('The generated correction did not pass the Python syntax check. Please retry the review.')
    elif not review.issues:
        try:ast.parse(source);correction=source
        except SyntaxError:raise ValueError('The reviewer did not provide a correction. Please retry.')
    if review.issues and not correction:
        raise ValueError('The reviewer identified issues but did not return corrected code. Please retry.')
    return {'summary':review.summary,'issues':[asdict(i) for i in review.issues], 'corrected_code':correction,
            'learning_concept':concept,'correction_verified':False,'correction_syntax_checked':bool(correction),
            'concept_note':'This is the concept involved, not proof of a learning weakness. Confirm understanding with a practice task or quiz.'}
