"""Topic boundaries for diagnostic assessment; URLs are never topic evidence."""
import re

def is_variables(concept):
    return bool(re.search(r"\b(variables?|assignments?|identifiers?)\b",concept,re.I)) and bool(re.search(r"\b(python|syntax|variables?|assignments?)\b",concept,re.I))

def validate_scope(concept, questions):
    if not questions:
        raise ValueError("No questions were generated for this lesson. Please retry.")
    if is_variables(concept):
        off_topic=re.compile(r"\b(idempotenc\w*|restful|http|https|endpoints?|fastapi|pydantic|binary trees?|avl|circuit breakers?)\b",re.I)
        for q in questions:
            text=" ".join(str(getattr(q,k,"") or "") for k in ("question_text","explanation","ideal_answer","concept_aspect"))
            if off_topic.search(text):
                raise ValueError("Quiz generation returned a question outside variables and assignment. Please retry; this quiz has not been assessed.")

def variables_quiz(concept):
    from cognitive_learning_agent.models.schemas import ConceptQuiz, QuizQuestion, QuestionType
    mcqs=[
      ("After x = 5 followed by x = 8, what is x?",["8","5","13","An error"],"Assignment binds x to its latest value.","Reassignment"),
      ("Which is a valid Python variable name?",["student_score","2score","student-score","class"],"Names may contain underscores but cannot start with a digit or be a keyword.","Identifiers"),
      ("What does = do in x = 10?",["Assigns a value to a name","Tests equality","Prints a value","Declares a constant"],"The assignment operator binds a name to a value; == compares values.","Assignment operator"),
      ("After x = 3; y = x; x = 9, what is y?",["3","9","12","Undefined"],"Rebinding x does not rebind y, which still refers to the integer 3.","Name binding"),
      ("Which expression evaluates to the string '7'?",["str(7)","int('7')","7 + 0","float(7)"],"str converts a value to its string representation.","Basic types"),
      ("What happens when print(score) runs before score is assigned?",["NameError","It prints 0","It prints None","It creates score"],"An undefined name causes NameError.","Unbound names")
    ]
    questions=[]
    for i,(text,options,explanation,aspect) in enumerate(mcqs,1):
        shift=i%4; rotated=options[shift:]+options[:shift]
        questions.append(QuizQuestion(question_id=i,question_type=QuestionType.MCQ,question_text=text,options=rotated,correct_option_index=(-shift)%4,explanation=explanation,concept_aspect=aspect))
    desc=[
      ("Explain the difference between = and == in Python.","= assigns a value to a name; == compares two values for equality.",["assign","compare"],"Assignment and equality"),
      ("Explain why total_cost is a valid identifier but 2cost is not.","An identifier may use letters, digits and underscores, but cannot start with a digit.",["identifier","digit","underscore"],"Naming rules"),
      ("For a = 4; b = a; a = 6, explain the final values of a and b.","a is 6 and b is 4. The final assignment rebinds a without changing b.",["6","4","assignment"],"Independent bindings"),
      ("Describe what Python does for age = 20 followed by age = 'twenty'.","The name age is rebound from an integer value to a string value; names are not fixed to one type.",["integer","string","name"],"Dynamic typing")
    ]
    for i,(text,answer,keywords,aspect) in enumerate(desc,7):
        questions.append(QuizQuestion(question_id=i,question_type=QuestionType.DESCRIPTIVE,question_text=text,explanation=answer,ideal_answer=answer,rubric_keywords=keywords,concept_aspect=aspect))
    return ConceptQuiz(concept_name=concept,questions=questions)
