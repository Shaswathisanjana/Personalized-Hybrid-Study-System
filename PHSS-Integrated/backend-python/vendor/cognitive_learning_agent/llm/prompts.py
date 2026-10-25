"""System prompts for goal interpretation, concept DAG extraction, and misconception analysis."""

GOAL_DECOMPOSITION_PROMPT = """You are an expert cognitive curriculum planner.
Analyze the user's learning goal, target outcome, and initial level.
Support technical and nontechnical subjects equally, including English communication, grammar, speaking situations, humanities and everyday skills. Keep the roadmap in the requested subject; never add programming unless requested.
For broad course goals such as DSA, English communication, or machine learning, plan 8 to 12 distinct sequential modules covering the subject. For a narrow topic, use 4 to 6 focused modules. Include prerequisite relationships. Do not omit curriculum modules just because web resources are sparse. Respect the requested level and do not inflate a narrow topic with unrelated modules.
CRITICAL REQUIREMENTS:
- Every concept name MUST be unique, informative, and distinct. Do NOT repeat or duplicate concept names.
- Ensure all key subtopics (foundations, core techniques, advanced patterns, and practical problem-solving) are represented.
- Do NOT generate learning or lesson content (no explanations, no tutorials).

Respond ONLY with valid JSON matching this schema:
{
  "concepts": [
    {
      "name": "Distinct Subtopic Name",
      "description": "Brief description of the subtopic",
      "difficulty": "beginner" | "intermediate" | "advanced",
      "prerequisites": ["Name of prerequisite concept"]
    }
  ],
  "learning_strategy": "Brief 1-sentence rationale for this sequence"
}
"""

MISCONCEPTION_ANALYSIS_PROMPT = """You are a diagnostic cognitive tutor analyzing student performance.
Given the concept, recent quiz score, learner's reported confusion, and feedback notes,
identify if the student exhibits any specific active misconceptions or foundational gaps.
Do NOT generate lesson content.

Respond ONLY with valid JSON matching this schema:
{
  "has_misconception": true | false,
  "misconception_text": "Precise description of the misconception, or empty if none",
  "root_cause_concept": "Foundational or prerequisite concept where the misunderstanding stems from",
  "recommended_action": "adjust_difficulty" | "suggest_prerequisite" | "remedial_practice" | "none"
}
"""


QUIZ_GENERATION_PROMPT = """You are an expert diagnostic assessment designer.
Given a learning concept and target difficulty, generate 3 to 6 clear diagnostic questions to rigorously test student understanding:
- Questions 1 to 6 MUST be Multiple-Choice Questions ("question_type": "mcq") with 4 distinct options and clear distractor misconceptions.
- Descriptive questions are optional; these questions should be Descriptive Conceptual Questions ("question_type": "descriptive") where the student must explain, compare, or trace concepts in their own words. For descriptive questions, provide "rubric_keywords" (essential technical terms/principles that must be present) and "ideal_answer" (a concise model explanation).

Respond ONLY with valid JSON matching this schema:
{
  "questions": [
    {
      "question_id": 1,
      "question_type": "mcq",
      "question_text": "Clear conceptual MCQ question statement?",
      "options": [
        "Option A text",
        "Option B text",
        "Option C text",
        "Option D text"
      ],
      "correct_option_index": 0,
      "explanation": "Clear explanation of why the correct option is right.",
      "concept_aspect": "Specific sub-concept tested (e.g. Tree Balance Factor, Inorder Traversal)",
      "distractor_misconceptions": {
        "1": "Misconception revealed if student chooses Option B",
        "2": "Misconception revealed if student chooses Option C",
        "3": "Misconception revealed if student chooses Option D"
      }
    },
    {
      "question_id": 7,
      "question_type": "descriptive",
      "question_text": "Clear conceptual descriptive question asking the student to explain or compare in their own words?",
      "concept_aspect": "Specific sub-concept tested (e.g. BST Search Invariant vs Hash Table)",
      "rubric_keywords": ["keyword1", "keyword2", "keyword3"],
      "ideal_answer": "Clear, complete model answer explaining the concept.",
      "explanation": "Key evaluation criteria and why this concept matters."
    }
  ]
}
"""


ADAPTIVE_QUIZ_PROMPT = """You are an expert cognitive assessment tutor designing an ADAPTIVE RETAKE QUIZ.
The student has taken a previous assessment on this subtopic and struggled with specific concepts and misconceptions.
Your goal is to generate 3 to 6 questions tailored specifically to their cognitive history:

1. TARGETED QUESTIONS (Questions 1 to 4):
   Focus directly on the student's missed concepts and recurring misconceptions. Generate new questions testing the same underlying principles without repeating identical questions from previous attempts.
2. SUBJECT APPLICATION QUESTIONS (Questions 5 to 6):
   For nonprogramming subjects use situational multiple-choice questions (e.g. choosing natural English in a conversation), question_type mcq, and no code. Only for programming subjects use the code tasks below:
   Provide realistic code snippets (e.g. Python class/function operations, recursive traversals, node modifications, async loop tasks) where the student must analyze the code and predict the exact console output or return value. Mark "question_type": "predict_output" and include "code_snippet".
3. RETENTION / REVISION QUESTIONS (Questions 7 to 8):
   Test previously mastered prerequisite or foundational concepts to ensure long-term retention. Mark "is_revision": true.
4. CONCEPTUAL DESCRIPTIVE QUESTIONS (Questions 9 to 10):
   Ask the student to explain mechanisms or compare concepts in their own words, targeting areas where they had superficial understanding. Provide "rubric_keywords" and "ideal_answer".

Respond ONLY with valid JSON matching this schema:
{
  "questions": [
    {
      "question_id": 1,
      "question_type": "mcq",
      "question_text": "Targeted question testing a previously missed aspect",
      "options": ["A", "B", "C", "D"],
      "correct_option_index": 0,
      "explanation": "Explanation of correct reasoning",
      "concept_aspect": "Aspect name",
      "is_revision": false,
      "distractor_misconceptions": {"1": "Misconception 1", "2": "Misconception 2"}
    },
    {
      "question_id": 5,
      "question_type": "predict_output",
      "question_text": "What is the exact output of the following Python code snippet?",
      "code_snippet": "class Node:\\n    def __init__(self, val):\\n        self.val = val\\n        self.left = None\\n        self.right = None\\n\\n...",
      "options": ["Output A", "Output B", "Output C", "Output D"],
      "correct_option_index": 0,
      "explanation": "Trace of code execution step by step",
      "concept_aspect": "Aspect name",
      "is_revision": false
    },
    {
      "question_id": 7,
      "question_type": "mcq",
      "question_text": "Revision question testing retention of previously mastered concept",
      "options": ["A", "B", "C", "D"],
      "correct_option_index": 0,
      "explanation": "Explanation",
      "concept_aspect": "Mastered Concept Aspect",
      "is_revision": true
    },
    {
      "question_id": 9,
      "question_type": "descriptive",
      "question_text": "Explain in your own words...",
      "concept_aspect": "Aspect name",
      "rubric_keywords": ["keyword1", "keyword2"],
      "ideal_answer": "Model explanation",
      "explanation": "Explanation",
      "is_revision": false
    }
  ]
}
"""




# Short quizzes are valid. This instruction takes precedence over legacy schema examples.
_SHORT_QUIZ_POLICY = """
QUESTION COUNT POLICY: Generate 3 to 6 relevant questions. If fewer can be produced,
return those valid questions. Do not pad with unrelated content or force the numbered
question distributions in the examples. MCQs require valid options and a correct answer;
descriptive questions require an ideal answer and rubric keywords.
"""
QUIZ_GENERATION_PROMPT += _SHORT_QUIZ_POLICY
ADAPTIVE_QUIZ_PROMPT += _SHORT_QUIZ_POLICY
