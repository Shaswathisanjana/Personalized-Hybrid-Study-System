from app.cognitive.models import (
    StudentCognitiveModel,
)

from app.learning_agent.remediation import (
    RemediationContext,
)

from app.learning_agent.content_generator import (
    GeneratedContent,
)


class RemediationGenerator:
    """
    Builds a grounded remediation request.

    The misconception is treated as a hypothesis,
    while the original question and answer are
    treated as the primary evidence.
    """

    def generate(
        self,
        student: StudentCognitiveModel,
        context: RemediationContext,
    ) -> GeneratedContent:

        concept = student.get_concept(
            context.concept_name
        )

        grounding = (
            context.build_grounding_text()
        )

        prompt = f"""
Provide a short targeted remediation lesson for the student.

CONCEPT
-------
{context.concept_name}

CURRENT COGNITIVE STATE
-----------------------
Mastery: {concept.mastery:.3f}
Confidence: {concept.confidence:.3f}
Attempts: {concept.attempts}

INTERACTION THAT CAUSED THE ERROR
---------------------------------
{grounding}

IMPORTANT INSTRUCTIONS
----------------------
The original question is the source of truth.

Do NOT change the function, formula, conditions,
base case, recursive step, or other information
given in the original question.

The detected misconception is only a hypothesis.
Do not automatically assume that the hypothesis
is correct.

First reason from the original question and the
student's actual answer.

If the misconception hypothesis is consistent
with the evidence, address it.

If the hypothesis is not supported by the original
question and student answer, do not teach it as fact.

Explain the correct reasoning step by step.

Contrast the student's likely error with the
correct reasoning only when that comparison is
supported by the available evidence.

Use one small worked trace or example.

Do not provide a generic lesson on the entire topic.
Focus on the specific interaction above.
""".strip()

        cognitive_context = {
            "mastery": concept.mastery,
            "confidence": concept.confidence,
            "attempts": concept.attempts,
            "misconceptions": (
                context.detected_misconceptions.copy()
            ),
            "original_question": (
                context.original_question
            ),
            "correct_answer": (
                context.correct_answer
            ),
            "student_answer": (
                context.student_answer
            ),
        }

        return GeneratedContent(
            content_type="grounded_targeted_remediation",
            concept_name=context.concept_name,
            difficulty="easy",
            text=prompt,
            cognitive_context=cognitive_context,
        )