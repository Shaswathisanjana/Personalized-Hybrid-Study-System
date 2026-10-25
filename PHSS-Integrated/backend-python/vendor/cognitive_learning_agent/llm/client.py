"""Multi-provider LLM client with Groq, Gemini, and graceful fallback heuristics."""

import json
import logging
import re
from typing import Dict, Any, Optional, List

from cognitive_learning_agent.config import settings
from cognitive_learning_agent.llm.prompts import (
    GOAL_DECOMPOSITION_PROMPT,
    MISCONCEPTION_ANALYSIS_PROMPT,
    QUIZ_GENERATION_PROMPT,
    ADAPTIVE_QUIZ_PROMPT,
)
from cognitive_learning_agent.models.schemas import ConceptQuiz, QuizQuestion, QuestionType, QuizAttemptRecord

logger = logging.getLogger(__name__)


class LLMClient:
    """Provides structured reasoning and JSON output via Groq or Gemini with automatic fallback."""

    def __init__(
        self,
        provider: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        google_api_key: Optional[str] = None,
    ):
        self.provider = provider or settings.PREFER_PROVIDER
        self.groq_api_key = groq_api_key or settings.GROQ_API_KEY
        self.google_api_key = google_api_key or settings.GOOGLE_API_KEY
        self._groq_client = None
        self._gemini_client = None

        if self.groq_api_key:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=self.groq_api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Groq client: {e}")

        if self.google_api_key:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.google_api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Gemini client: {e}")

    def decompose_goal(
        self, goal: str, target_outcome: str, current_level: str, preferred_format: str
    ) -> Dict[str, Any]:
        """Decompose a learning goal into structured concepts and prerequisite DAG."""
        user_prompt = (
            f"Learning Goal: {goal}\n"
            f"Target Outcome: {target_outcome}\n"
            f"Current Level: {current_level}\n"
            f"Preferred Format: {preferred_format}\n"
            "Produce the structured concepts and prerequisites in JSON."
        )

        # 1. Try Groq
        if self._groq_client:
            try:
                completion = self._groq_client.chat.completions.create(
                    model=settings.DEFAULT_GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": GOAL_DECOMPOSITION_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"} if "qwen" not in settings.DEFAULT_GROQ_MODEL else None,
                    temperature=0.2,
                )
                text = completion.choices[0].message.content
                parsed = self._extract_json(text)
                if parsed and "concepts" in parsed and len(parsed["concepts"]) > 0:
                    return parsed
            except Exception as e:
                logger.warning(f"Groq goal decomposition failed: {e}")

        # 2. Try Gemini
        if self._gemini_client:
            try:
                response = self._gemini_client.models.generate_content(
                    model=settings.DEFAULT_GEMINI_MODEL,
                    contents=f"{GOAL_DECOMPOSITION_PROMPT}\n\nUser Request:\n{user_prompt}",
                )
                text = response.text
                parsed = self._extract_json(text)
                if parsed and "concepts" in parsed and len(parsed["concepts"]) > 0:
                    return parsed
            except Exception as e:
                logger.warning(f"Gemini goal decomposition failed: {e}")

        # 3. Rule-based Heuristic Fallback
        return self._heuristic_goal_decomposition(goal, target_outcome, current_level)

    def diagnose_misconception(
        self,
        concept_name: str,
        quiz_score: Optional[float],
        perceived_difficulty: Optional[str],
        reported_confusion: bool,
        notes: Optional[str],
    ) -> Dict[str, Any]:
        """Diagnose whether student performance indicates an active misconception."""
        user_prompt = (
            f"Concept: {concept_name}\n"
            f"Quiz Score: {quiz_score if quiz_score is not None else 'N/A'}\n"
            f"Perceived Difficulty: {perceived_difficulty}\n"
            f"Reported Confusion: {reported_confusion}\n"
            f"Student Notes/Errors: {notes or 'None'}\n"
        )

        if self._groq_client:
            try:
                completion = self._groq_client.chat.completions.create(
                    model=settings.DEFAULT_GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": MISCONCEPTION_ANALYSIS_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                )
                text = completion.choices[0].message.content
                parsed = self._extract_json(text)
                if parsed and "has_misconception" in parsed:
                    return parsed
            except Exception as e:
                logger.warning(f"Groq misconception diagnosis failed: {e}")

        # Fallback rule-based diagnosis
        return self._heuristic_misconception_diagnosis(
            concept_name, quiz_score, perceived_difficulty, reported_confusion, notes
        )

    def generate_concept_quiz(
        self,
        concept_name: str,
        resource_title: str = "",
        difficulty: str = "beginner",
    ) -> ConceptQuiz:
        """Generate a diagnostic multiple-choice quiz testing conceptual understanding and mapping distractors."""
        user_prompt = (
            f"Target Concept: {concept_name}\n"
            f"Resource Studied: {resource_title}\n"
            f"Target Difficulty: {difficulty}\n"
            f"Generate 3 to 6 diagnostic questions specifically testing '{concept_name}'. "
            "Prefer multiple-choice questions with 4 options; you may include descriptive questions with rubric_keywords and ideal_answer. A smaller valid quiz is acceptable. "
            "Keep explanations and ideal answers concise (1-2 sentences each) so that the entire JSON response fits completely without truncation."
        )

        questions: List[QuizQuestion] = []
        quiz_provider_error = None
        from app.orchestrator.intelligence import generate, safe_error
        try:
            parsed = generate(QUIZ_GENERATION_PROMPT + "\n" + user_prompt)
            if parsed and "questions" in parsed and len(parsed["questions"]) > 0:
                for q in parsed["questions"]:
                    q_type_str = str(q.get("question_type", "mcq")).lower()
                    if q_type_str == "predict_output":
                        q_type = QuestionType.PREDICT_OUTPUT
                    elif q_type_str == "descriptive" or not q.get("options"):
                        q_type = QuestionType.DESCRIPTIVE
                    else:
                        q_type = QuestionType.MCQ
                    distractors = {}
                    for k, v in q.get("distractor_misconceptions", {}).items():
                        try:
                            distractors[int(k)] = str(v)
                        except ValueError:
                            pass
                    questions.append(
                        QuizQuestion(
                            question_id=int(q.get("question_id", len(questions) + 1)),
                            question_type=q_type,
                            question_text=q["question_text"],
                            code_snippet=q.get("code_snippet"),
                            options=q.get("options", []),
                            correct_option_index=int(q.get("correct_option_index", 0)),
                            explanation=q.get("explanation", ""),
                            concept_aspect=q.get("concept_aspect", concept_name),
                            distractor_misconceptions=distractors,
                            ideal_answer=q.get("ideal_answer", q.get("explanation", "")),
                            rubric_keywords=q.get("rubric_keywords", []),
                            is_revision=bool(q.get("is_revision", False)),
                        )
                    )
        except Exception as e:
            quiz_provider_error = safe_error("quiz", e)
            logger.warning("Quiz generation failed: %s", quiz_provider_error)

        # Keep a valid short quiz; fallback is only needed when generation is empty.
        if not questions:
            try:
                return self._heuristic_quiz_generation(concept_name, resource_title, difficulty)
            except ValueError as exc:
                raise RuntimeError("Quiz generation could not return usable questions. " + (quiz_provider_error or "The AI response did not contain valid questions. Please retry.")) from exc

        # Enforce sequential IDs 1 to 10
        final_questions = questions[:10]
        for idx, q in enumerate(final_questions, start=1):
            q.question_id = idx

        return ConceptQuiz(
            concept_name=concept_name,
            resource_url=None,
            attempt_number=1,
            quiz_type="initial",
            questions=final_questions,
        )

    def generate_adaptive_quiz(
        self,
        concept_name: str,
        previous_attempts: List[QuizAttemptRecord],
        mastered_concepts: Optional[List[str]] = None,
        resource_title: str = "",
        difficulty: str = "beginner",
    ) -> ConceptQuiz:
        """Generate an adaptive retake quiz based on cognitive memory and previous attempts.

        Prioritizes:
        - Questions addressing missed concepts and recurring misconceptions.
        - Predict Output coding questions.
        - Retention revision questions from previously mastered concepts.
        - In-depth descriptive questions.
        """
        if not previous_attempts:
            return self.generate_concept_quiz(concept_name, resource_title, difficulty)

        attempt_num = len(previous_attempts) + 1

        # Extract missed aspects and misconceptions from past attempts
        missed_aspects = []
        recurring_misconceptions = []
        for att in previous_attempts:
            for wa in att.weak_areas:
                if wa not in missed_aspects:
                    missed_aspects.append(wa)
            for m in att.misconceptions:
                if m not in recurring_misconceptions:
                    recurring_misconceptions.append(m)

        rev_concepts = mastered_concepts or []

        user_prompt = (
            f"Target Concept: {concept_name}\n"
            f"Retake Attempt Number: {attempt_num}\n"
            f"Resource Studied: {resource_title}\n"
            f"Target Difficulty: {difficulty}\n"
            f"Student's Weak Areas / Missed Concepts: {', '.join(missed_aspects) if missed_aspects else 'None identified'}\n"
            f"Active Misconceptions to Remediate: {', '.join(recurring_misconceptions) if recurring_misconceptions else 'None'}\n"
            f"Previously Mastered Concepts (for revision questions): {', '.join(rev_concepts) if rev_concepts else 'Foundational concepts'}\n"
            "Generate 3 to 6 adaptive questions testing these areas. A smaller valid quiz is acceptable. "
            "Prioritize fresh questions on missed concepts. "
            "Include code output questions only for programming topics. "
            "Optional revision questions must relate to this lesson. "
            "Descriptive questions are optional."
        )

        questions: List[QuizQuestion] = []
        quiz_provider_error = None
        from app.orchestrator.intelligence import generate, safe_error
        try:
            parsed = generate(ADAPTIVE_QUIZ_PROMPT + "\n" + user_prompt)
            if parsed and "questions" in parsed and len(parsed["questions"]) > 0:
                for q in parsed["questions"]:
                    q_type_str = str(q.get("question_type", "mcq")).lower()
                    if q_type_str == "predict_output":
                        q_type = QuestionType.PREDICT_OUTPUT
                    elif q_type_str == "descriptive" or not q.get("options"):
                        q_type = QuestionType.DESCRIPTIVE
                    else:
                        q_type = QuestionType.MCQ
                    distractors = {}
                    for k, v in q.get("distractor_misconceptions", {}).items():
                        try:
                            distractors[int(k)] = str(v)
                        except ValueError:
                            pass
                    questions.append(
                        QuizQuestion(
                            question_id=int(q.get("question_id", len(questions) + 1)),
                            question_type=q_type,
                            question_text=q["question_text"],
                            code_snippet=q.get("code_snippet"),
                            options=q.get("options", []),
                            correct_option_index=int(q.get("correct_option_index", 0)),
                            explanation=q.get("explanation", ""),
                            concept_aspect=q.get("concept_aspect", concept_name),
                            distractor_misconceptions=distractors,
                            ideal_answer=q.get("ideal_answer", q.get("explanation", "")),
                            rubric_keywords=q.get("rubric_keywords", []),
                            is_revision=bool(q.get("is_revision", False)),
                        )
                    )
        except Exception as e:
            quiz_provider_error = safe_error("quiz", e)
            logger.warning("Quiz generation failed: %s", quiz_provider_error)

# Supplement or fallback from heuristic adaptive bank

        if not questions:
            try:
                return self._heuristic_adaptive_quiz(
                    concept_name=concept_name,
                    previous_attempts=previous_attempts,
                    mastered_concepts=mastered_concepts,
                    resource_title=resource_title,
                    difficulty=difficulty,
                )
            except ValueError as exc:
                raise RuntimeError("Quiz generation could not return usable questions. " + (quiz_provider_error or "The AI response did not contain valid questions. Please retry.")) from exc

        final_questions = questions[:10]
        for idx, q in enumerate(final_questions, start=1):
            q.question_id = idx

        return ConceptQuiz(
            concept_name=concept_name,
            resource_url=None,
            attempt_number=attempt_num,
            quiz_type="adaptive",
            questions=final_questions,
        )

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON object from markdown or text output."""
        try:
            return json.loads(text)
        except Exception:
            pass

        # Regex match for code fence
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        # Regex match for first { to last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                pass

        return None

    @staticmethod
    def _heuristic_goal_decomposition(goal: str, target_outcome: str, current_level: str) -> Dict[str, Any]:
        """Deterministic heuristic decomposition when external LLMs are unavailable."""
        goal_lower = goal.lower()
        
        # Domain detection: async python, deep learning, rest api, web dev, or generic
        if "async" in goal_lower or "concurrency" in goal_lower or "asyncio" in goal_lower:
            concepts = [
                {"name": "Synchronous vs Asynchronous I/O Fundamentals", "difficulty": "beginner", "prerequisites": []},
                {"name": "Python Event Loop & Coroutines", "difficulty": "beginner", "prerequisites": ["Synchronous vs Asynchronous I/O Fundamentals"]},
                {"name": "async and await Syntax & Task Management", "difficulty": "intermediate", "prerequisites": ["Python Event Loop & Coroutines"]},
                {"name": "Async Web Requests & Scraping with aiohttp", "difficulty": "intermediate", "prerequisites": ["async and await Syntax & Task Management"]},
                {"name": "Concurrency Control, Semaphores & Error Handling", "difficulty": "advanced", "prerequisites": ["Async Web Requests & Scraping with aiohttp"]},
            ]
        elif "transformer" in goal_lower or "attention" in goal_lower or "llm" in goal_lower or "deep learning" in goal_lower:
            concepts = [
                {"name": "Matrix Multiplications & Vector Embeddings", "difficulty": "beginner", "prerequisites": []},
                {"name": "Scaled Dot-Product Attention & Self-Attention", "difficulty": "intermediate", "prerequisites": ["Matrix Multiplications & Vector Embeddings"]},
                {"name": "Multi-Head Attention Mechanism", "difficulty": "intermediate", "prerequisites": ["Scaled Dot-Product Attention & Self-Attention"]},
                {"name": "Positional Encoding & Transformer Architecture", "difficulty": "advanced", "prerequisites": ["Multi-Head Attention Mechanism"]},
                {"name": "Decoder-Only Autoregressive Generation", "difficulty": "advanced", "prerequisites": ["Positional Encoding & Transformer Architecture"]},
            ]
        elif "tree" in goal_lower or "bst" in goal_lower or "data structure" in goal_lower:
            concepts = [
                {"name": "Tree Fundamentals and Terminology", "difficulty": "beginner", "prerequisites": []},
                {"name": "Binary Tree Representation and Traversals", "difficulty": "beginner", "prerequisites": ["Tree Fundamentals and Terminology"]},
                {"name": "Binary Search Trees (BST) and Operations", "difficulty": "intermediate", "prerequisites": ["Binary Tree Representation and Traversals"]},
                {"name": "Balanced Binary Trees and Rotations", "difficulty": "intermediate", "prerequisites": ["Binary Search Trees (BST) and Operations"]},
                {"name": "Tree Problem-Solving Patterns and Applications", "difficulty": "advanced", "prerequisites": ["Balanced Binary Trees and Rotations"]},
            ]
        elif "graph" in goal_lower:
            concepts = [
                {"name": "Graph Fundamentals and Terminology", "difficulty": "beginner", "prerequisites": []},
                {"name": "Graph Representation (Adjacency Matrix & List)", "difficulty": "beginner", "prerequisites": ["Graph Fundamentals and Terminology"]},
                {"name": "Graph Traversals (BFS and DFS)", "difficulty": "beginner", "prerequisites": ["Graph Representation (Adjacency Matrix & List)"]},
                {"name": "Shortest Path Algorithms (Dijkstra and Bellman-Ford)", "difficulty": "intermediate", "prerequisites": ["Graph Traversals (BFS and DFS)"]},
                {"name": "Minimum Spanning Trees (Kruskal and Prim)", "difficulty": "intermediate", "prerequisites": ["Graph Traversals (BFS and DFS)"]},
                {"name": "Advanced Graph Algorithms & Problem Solving", "difficulty": "advanced", "prerequisites": ["Shortest Path Algorithms (Dijkstra and Bellman-Ford)", "Minimum Spanning Trees (Kruskal and Prim)"]},
            ]
        elif "api" in goal_lower or "fastapi" in goal_lower or "rest" in goal_lower:
            concepts = [
                {"name": "HTTP Protocol & RESTful Architecture Principles", "difficulty": "beginner", "prerequisites": []},
                {"name": "FastAPI Routing, Path & Query Parameters", "difficulty": "beginner", "prerequisites": ["HTTP Protocol & RESTful Architecture Principles"]},
                {"name": "Request Validation & Serialization with Pydantic", "difficulty": "intermediate", "prerequisites": ["FastAPI Routing, Path & Query Parameters"]},
                {"name": "Database Integration with SQLAlchemy ORM", "difficulty": "intermediate", "prerequisites": ["Request Validation & Serialization with Pydantic"]},
                {"name": "Authentication, JWT Tokens & Middleware", "difficulty": "advanced", "prerequisites": ["Database Integration with SQLAlchemy ORM"]},
            ]
        else:
            # Generic structured decomposition with 5 distinct pedagogical phases
            words = [w for w in goal.replace(",", " ").split() if len(w) > 3]
            kw = " ".join(words[:3]) if words else goal
            concepts = [
                {"name": f"Foundations & Core Terminology of {kw}", "difficulty": "beginner", "prerequisites": []},
                {"name": f"Key Mechanisms & Syntax of {kw}", "difficulty": "beginner", "prerequisites": [f"Foundations & Core Terminology of {kw}"]},
                {"name": f"Practical Patterns & Implementation in {kw}", "difficulty": "intermediate", "prerequisites": [f"Key Mechanisms & Syntax of {kw}"]},
                {"name": f"Advanced Architecture & Optimization in {kw}", "difficulty": "advanced", "prerequisites": [f"Practical Patterns & Implementation in {kw}"]},
                {"name": f"Real-World Problem Solving & Applications of {kw}", "difficulty": "advanced", "prerequisites": [f"Advanced Architecture & Optimization in {kw}"]},
            ]

        return {
            "concepts": concepts,
            "learning_strategy": f"Stepwise curriculum tailored for {current_level} level targeting outcome: {target_outcome}",
        }

    @staticmethod
    def _heuristic_misconception_diagnosis(
        concept_name: str,
        quiz_score: Optional[float],
        perceived_difficulty: Optional[str],
        reported_confusion: bool,
        notes: Optional[str],
    ) -> Dict[str, Any]:
        """Heuristic rule for diagnosing misconceptions based on score and confusion indicators."""
        notes_str = (notes or "").lower()
        has_misconception = False
        text = ""
        action = "none"

        if reported_confusion or (quiz_score is not None and quiz_score < 0.5):
            has_misconception = True
            if "blocking" in notes_str or "async" in notes_str or "async" in concept_name.lower() or "event loop" in concept_name.lower():
                text = "Conflating CPU-bound multi-threading with asynchronous non-blocking event loops"
            elif "attention" in concept_name.lower() or "matrix" in notes_str:
                text = "Misunderstanding how query and key dot products map to value weights"
            elif "state" in notes_str:
                text = "Assuming stateless functions preserve context across calls without state stores"
            else:
                text = f"Fundamental misunderstanding of core operations in {concept_name}"

            if quiz_score is not None and quiz_score < 0.35:
                action = "suggest_prerequisite"
            else:
                action = "adjust_difficulty"
        elif perceived_difficulty == "too_hard":
            has_misconception = False
            action = "adjust_difficulty"

        return {
            "has_misconception": has_misconception,
            "misconception_text": text,
            "root_cause_concept": concept_name,
            "recommended_action": action,
        }

    @staticmethod
    def _heuristic_quiz_generation(
        concept_name: str, resource_title: str = "", difficulty: str = "beginner"
    ) -> ConceptQuiz:
        """Deterministic diagnostic quiz questions with misconception-mapped distractors."""
        from cognitive_learning_agent.llm.quiz_scope import is_variables, variables_quiz
        if is_variables(concept_name):
            return variables_quiz(concept_name)
        c_lower = concept_name.lower()

        # 1. Balanced Binary Trees and Rotations (AVL / Red-Black)
        if any(re.search(r"\b" + re.escape(k) + r"\b", c_lower) for k in ["avl", "rotation", "balanced", "balance"]):
            questions = [
                QuizQuestion(
                    question_id=1,
                    question_type=QuestionType.MCQ,
                    question_text="In an AVL Tree, what is the valid range for the balance factor (height(left) - height(right)) of any node?",
                    options=["{-1, 0, +1}", "{0, 1, 2}", "{-2, 0, +2}", "Any integer value"],
                    correct_option_index=0,
                    explanation="An AVL tree strictly requires that the balance factor of every node remains in {-1, 0, +1}. Any deviation triggers a rotation.",
                    concept_aspect="AVL Balance Factor Invariant",
                    distractor_misconceptions={
                        1: "Believing balance factors cannot be negative",
                        2: "Assuming balance factor violations of 2 are tolerated",
                        3: "Conflating AVL trees with general unbounded BSTs",
                    },
                ),
                QuizQuestion(
                    question_id=2,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: What is the balance factor (height(left) - height(right)) of node 30 in this tree?",
                    code_snippet=(
                        "class Node:\n"
                        "    def __init__(self, val, left=None, right=None):\n"
                        "        self.val, self.left, self.right = val, left, right\n\n"
                        "def get_height(n):\n"
                        "    return 0 if not n else 1 + max(get_height(n.left), get_height(n.right))\n\n"
                        "# Tree: 30 has left child 20, which has left child 10\n"
                        "root = Node(30, Node(20, Node(10)))\n"
                        "print(get_height(root.left) - get_height(root.right))"
                    ),
                    options=["2", "1", "0", "-2"],
                    correct_option_index=0,
                    explanation="root.left (node 20) has height 2 (20 -> 10). root.right is None (height 0). The balance factor is 2 - 0 = 2 (Left-Left unbalance).",
                    concept_aspect="Predict Output: AVL Balance Factor Calculation",
                    distractor_misconceptions={
                        1: "Miscalculating subtree height as node count",
                        2: "Assuming empty right subtree has height 1",
                        3: "Inverting the subtraction sign",
                    },
                ),
                QuizQuestion(
                    question_id=3,
                    question_type=QuestionType.MCQ,
                    question_text="Which rotation restores balance after an insertion into the left subtree of the left child (Left-Left case)?",
                    options=[
                        "A single Right Rotation on the unbalanced node",
                        "A single Left Rotation on the unbalanced node",
                        "A Left-Right double rotation",
                        "A Right-Left double rotation",
                    ],
                    correct_option_index=0,
                    explanation="The LL case is resolved by a single Right Rotation, bringing the left child up as the new root.",
                    concept_aspect="AVL Left-Left Rotation Mechanics",
                    distractor_misconceptions={
                        1: "Inverting the rotation direction",
                        2: "Unnecessarily applying a double rotation for an LL case",
                        3: "Confusing LL with RL violation",
                    },
                ),
                QuizQuestion(
                    question_id=4,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: Which value becomes the new root after applying right_rotate to node 30?",
                    code_snippet=(
                        "class Node:\n"
                        "    def __init__(self, val, left=None, right=None):\n"
                        "        self.val, self.left, self.right = val, left, right\n\n"
                        "def right_rotate(y):\n"
                        "    x = y.left\n"
                        "    y.left = x.right\n"
                        "    x.right = y\n"
                        "    return x\n\n"
                        "root = Node(30, Node(20, Node(10)))\n"
                        "new_root = right_rotate(root)\n"
                        "print(f'{new_root.val} -> {new_root.right.val}')"
                    ),
                    options=["20 -> 30", "30 -> 20", "10 -> 20", "20 -> 10"],
                    correct_option_index=0,
                    explanation="In a right rotation, node 20 becomes the new root, and node 30 becomes its right child. The output is '20 -> 30'.",
                    concept_aspect="Predict Output: Right Rotation Transformation",
                    distractor_misconceptions={
                        1: "Believing node 30 remains root",
                        2: "Assuming node 10 becomes root",
                        3: "Reversing child pointers",
                    },
                ),
                QuizQuestion(
                    question_id=5,
                    question_type=QuestionType.MCQ,
                    question_text="When is a double Left-Right (LR) rotation required in an AVL tree?",
                    options=[
                        "When an insertion occurs in the right subtree of the left child",
                        "When an insertion occurs in the left subtree of the left child",
                        "When an insertion occurs in the right subtree of the right child",
                        "Whenever an AVL tree reaches depth 4",
                    ],
                    correct_option_index=0,
                    explanation="An LR case occurs when the left child is heavier, but the new node was inserted into its right subtree. It requires a Left rotation on the child followed by a Right rotation on the parent.",
                    concept_aspect="AVL Left-Right Double Rotation Case",
                    distractor_misconceptions={
                        1: "Confusing LR case with LL case",
                        2: "Confusing LR with RR case",
                        3: "Assuming rotations depend on absolute tree depth",
                    },
                ),
                QuizQuestion(
                    question_id=6,
                    question_type=QuestionType.MCQ,
                    question_text="Why are Red-Black trees often preferred over AVL trees for write-heavy associative containers (like C++ std::map or Java TreeMap)?",
                    options=[
                        "Red-Black trees require at most 2 rotations on insertion and 3 on deletion, making updates faster than AVL trees.",
                        "Red-Black trees have strictly lower height than AVL trees.",
                        "Red-Black trees do not require any memory pointers.",
                        "AVL trees cannot store string keys.",
                    ],
                    correct_option_index=0,
                    explanation="AVL trees are more rigidly balanced (faster lookups), but require more frequent rotations. Red-Black trees trade slightly looser balance for faster insertions and deletions.",
                    concept_aspect="AVL vs Red-Black Tree Engineering Trade-offs",
                    distractor_misconceptions={
                        1: "Falsely believing Red-Black trees are more rigidly balanced than AVL",
                        2: "Assuming Red-Black trees are pointer-free arrays",
                        3: "Assuming key type restrictions on balanced trees",
                    },
                ),
                QuizQuestion(
                    question_id=7,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain the four rotation cases in an AVL Tree (LL, RR, LR, RL) and state the exact rotation steps for the LR case.",
                    explanation="LL and RR require single rotations (Right and Left). LR and RL require double rotations. LR executes a Left rotation on the left child, followed by a Right rotation on the parent.",
                    concept_aspect="AVL Tree Rotation Taxonomy & LR Execution",
                    ideal_answer="The four AVL rotation cases correspond to the balance factor sign mismatch: LL (single right rotation), RR (single left rotation), LR (left rotate left child, then right rotate unbalanced parent), and RL (right rotate right child, then left rotate parent). For LR, the first rotation transforms it into an LL case, and the second restores height balance.",
                    rubric_keywords=["ll", "rr", "lr", "rl", "single rotation", "double rotation", "left rotate", "right rotate", "balance factor"],
                ),
                QuizQuestion(
                    question_id=8,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain how maintaining the balance factor invariant in an AVL tree guarantees O(log n) worst-case time complexity for search, insertion, and deletion.",
                    explanation="By bounding the height difference to at most 1, the maximum height of an AVL tree with n nodes cannot exceed 1.44 log2(n). Since all operations scale with height, they are strictly O(log n).",
                    concept_aspect="AVL Logarithmic Height Proof & Performance Guarantees",
                    ideal_answer="Because every node's balance factor is constrained to {-1, 0, +1}, the height of an AVL tree with n nodes is mathematically bounded by approximately 1.44 log2(n). Since BST search, insertion, and deletion traverse a single path from root to leaf, their running times are strictly bounded by tree height, guaranteeing worst-case O(log n) performance.",
                    rubric_keywords=["balance factor", "height bound", "1.44", "log n", "worst-case", "search", "insertion", "deletion"],
                ),
                QuizQuestion(
                    question_id=9,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Compare AVL trees with standard unbalanced Binary Search Trees when processing continuously sorted incoming streams of data.",
                    explanation="Inserting sorted data into an unbalanced BST creates a degenerate O(n) linked list. AVL trees continuously rotate to maintain balanced O(log n) height.",
                    concept_aspect="AVL Prevention of Degenerate Skewed Trees",
                    ideal_answer="When fed sequentially sorted data (e.g. 1, 2, 3, 4, ...), an unbalanced BST degrades into a linear linked list of height n, causing search time to regress to O(n). In contrast, an AVL tree immediately detects balance factor violations (reaching +2 or -2) and performs rotations, ensuring the tree remains balanced with logarithmic height O(log n).",
                    rubric_keywords=["sorted stream", "degenerate", "linked list", "o(n)", "rotations", "o(log n)", "rebalance"],
                ),
                QuizQuestion(
                    question_id=10,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Describe how node height and balance factor are recomputed during tree traversal unwinding after an insertion in an AVL tree.",
                    explanation="During recursion unwind, the height of each ancestor is updated as 1 + max(left_height, right_height). If balance factor reaches +/-2, the appropriate rotation is executed and new heights are assigned.",
                    concept_aspect="AVL Post-Insertion Unwinding & Height Recalculation",
                    ideal_answer="After inserting a new leaf, the recursive call stack unwinds back to the root. At each ancestor node, the height is recomputed as 1 + max(left_child_height, right_child_height). The balance factor is calculated, and if it evaluates to 2 or -2, rotation functions are invoked, returning the new subtree root with updated heights.",
                    rubric_keywords=["recursion unwind", "call stack", "height update", "max", "balance factor", "rotation"],
                ),
            ]

        # 2. Binary Search Trees (BST) and Operations
        elif any(re.search(r"\b" + re.escape(k) + r"\b", c_lower) for k in ["bst", "binary search", "search tree", "search trees"]):
            questions = [
                QuizQuestion(
                    question_id=1,
                    question_type=QuestionType.MCQ,
                    question_text="What fundamental ordering invariant must hold true for every node X in a valid Binary Search Tree (BST)?",
                    options=[
                        "All keys in the left subtree must be < X.val, and all keys in the right subtree must be > X.val.",
                        "Every parent node must equal the sum of its direct children.",
                        "Left child must be greater than parent, and right child must be smaller.",
                        "All leaf nodes must reside on the exact same depth level.",
                    ],
                    correct_option_index=0,
                    explanation="The BST property requires that for any node X, all values in its entire left subtree are strictly smaller than X, and all values in its right subtree are strictly greater.",
                    concept_aspect="Binary Search Tree Ordering Invariant",
                    distractor_misconceptions={
                        1: "Confusing BST with sum trees",
                        2: "Inverting left and right subtree ordering",
                        3: "Confusing BST invariant with full/complete tree constraints",
                    },
                ),
                QuizQuestion(
                    question_id=2,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: In what position does value 7 end up after sequential BST insertion?",
                    code_snippet=(
                        "class BST:\n"
                        "    def __init__(self, v): self.v, self.l, self.r = v, None, None\n\n"
                        "def insert(root, val):\n"
                        "    if not root: return BST(val)\n"
                        "    if val < root.v: root.l = insert(root.l, val)\n"
                        "    else: root.r = insert(root.r, val)\n"
                        "    return root\n\n"
                        "root = BST(10)\n"
                        "for x in [5, 15, 3, 7]: insert(root, x)\n"
                        "print(root.l.r.v)"
                    ),
                    options=["7", "5", "3", "15"],
                    correct_option_index=0,
                    explanation="10 is root. 5 goes to root.l. 15 goes to root.r. 3 goes to 5's left (root.l.l). 7 is > 5 so it goes to 5's right (root.l.r). Therefore root.l.r.v is 7.",
                    concept_aspect="Predict Output: BST Node Insertion Path",
                    distractor_misconceptions={
                        1: "Confusing the parent node with the newly inserted node",
                        2: "Assuming 7 goes to root.l.l",
                        3: "Assuming 7 goes to root.r",
                    },
                ),
                QuizQuestion(
                    question_id=3,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: What value does this find_min function print?",
                    code_snippet=(
                        "def find_min(node):\n"
                        "    curr = node\n"
                        "    while curr and curr.l:\n"
                        "        curr = curr.l\n"
                        "    return curr.v\n\n"
                        "r = BST(20); r.l = BST(10); r.l.r = BST(14); r.l.l = BST(4)\n"
                        "print(find_min(r))"
                    ),
                    options=["4", "10", "14", "20"],
                    correct_option_index=0,
                    explanation="In a BST, the minimum element is located at the leftmost node. Traversing left: 20 -> 10 -> 4. Since 4 has no left child, find_min returns 4.",
                    concept_aspect="Predict Output: Finding Minimum Element in BST",
                    distractor_misconceptions={
                        1: "Stopping early at intermediate left child 10",
                        2: "Confusing left child with right child 14",
                        3: "Returning the root value 20",
                    },
                ),
                QuizQuestion(
                    question_id=4,
                    question_type=QuestionType.MCQ,
                    question_text="When deleting a node that has TWO children from a BST, which replacement node preserves the BST invariant?",
                    options=[
                        "Either the In-order Successor (smallest in right subtree) or In-order Predecessor (largest in left subtree)",
                        "Any arbitrary leaf node selected at random",
                        "The root node of the entire tree",
                        "The direct parent node of the node being deleted",
                    ],
                    correct_option_index=0,
                    explanation="Replacing with either the in-order successor or predecessor guarantees that all left subtree nodes remain smaller and all right subtree nodes remain greater.",
                    concept_aspect="BST Deletion with Two Children",
                    distractor_misconceptions={
                        1: "Assuming any random leaf can replace an internal node",
                        2: "Confusing replacement with tree root re-assignment",
                        3: "Confusing replacement node with the parent node",
                    },
                ),
                QuizQuestion(
                    question_id=5,
                    question_type=QuestionType.MCQ,
                    question_text="What is the worst-case time complexity of searching for an element in an unbalanced Binary Search Tree?",
                    options=["O(n)", "O(log n)", "O(1)", "O(n log n)"],
                    correct_option_index=0,
                    explanation="If elements were inserted in sorted order, the BST degenerates into a single long branch (a linked list), resulting in worst-case O(n) search time.",
                    concept_aspect="BST Asymptotic Search Complexity (Unbalanced Case)",
                    distractor_misconceptions={
                        1: "Confusing average-case O(log n) with worst-case unbalanced O(n)",
                        2: "Assuming binary search in arrays O(1) applies to trees",
                        3: "Conflating search time with sorting time O(n log n)",
                    },
                ),
                QuizQuestion(
                    question_id=6,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: What list does an in-order traversal of this BST produce?",
                    code_snippet=(
                        "def inorder(root):\n"
                        "    return inorder(root.l) + [root.v] + inorder(root.r) if root else []\n\n"
                        "r = BST(8); insert(r, 3); insert(r, 10); insert(r, 1); insert(r, 6)\n"
                        "print(inorder(r))"
                    ),
                    options=["[1, 3, 6, 8, 10]", "[8, 3, 1, 6, 10]", "[1, 6, 3, 10, 8]", "[10, 8, 6, 3, 1]"],
                    correct_option_index=0,
                    explanation="Inorder traversal (Left -> Node -> Right) of any valid BST always yields the keys in sorted ascending order: [1, 3, 6, 8, 10].",
                    concept_aspect="Predict Output: BST In-order Traversal Order",
                    distractor_misconceptions={
                        1: "Confusing in-order with pre-order traversal",
                        2: "Confusing in-order with post-order traversal",
                        3: "Assuming descending order traversal",
                    },
                ),
                QuizQuestion(
                    question_id=7,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain the step-by-step algorithm to delete a node having TWO children from a Binary Search Tree.",
                    explanation="Find the in-order successor (minimum in right subtree), copy its value to the target node, then recursively delete the successor from the right subtree.",
                    concept_aspect="BST Two-Child Deletion Algorithm",
                    ideal_answer="To delete a node with two children: 1) Locate its in-order successor by traversing to the leftmost node in its right subtree. 2) Copy the successor's key into the node being deleted. 3) Recursively delete the in-order successor from the right subtree, which is guaranteed to have at most one child (a right child), simplifying deletion to a base case.",
                    rubric_keywords=["in-order successor", "right subtree", "leftmost", "copy value", "recursive delete", "one child"],
                ),
                QuizQuestion(
                    question_id=8,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain why inserting pre-sorted numbers (e.g. 1, 2, 3, 4, 5) into a naive BST degrades search performance from O(log n) to O(n).",
                    explanation="Every new element is greater than the previous, so it is always placed as the right child with no left children, creating a degenerate linear list of height n.",
                    concept_aspect="BST Degeneracy Under Sorted Input",
                    ideal_answer="When inserting pre-sorted elements in ascending order, each incoming element is greater than all previously inserted nodes. Consequently, each node is inserted strictly as the right child of the preceding node, leaving all left child pointers null. The tree degenerates into a linear singly linked list of height n, making search traversal linear O(n) instead of logarithmic O(log n).",
                    rubric_keywords=["pre-sorted", "right child", "degenerate", "linked list", "height n", "linear", "o(n)", "o(log n)"],
                ),
                QuizQuestion(
                    question_id=9,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Describe how to efficiently find the Lowest Common Ancestor (LCA) of two nodes p and q in a Binary Search Tree without extra memory.",
                    explanation="Start at root: if both p and q are smaller than current node, go left. If both are greater, go right. The split point where p and q lie on different sides is the LCA.",
                    concept_aspect="BST Lowest Common Ancestor (LCA) Algorithm",
                    ideal_answer="Starting at root: if both p.val and q.val are strictly less than root.val, the LCA must reside in the left subtree, so we recurse left. If both p.val and q.val are strictly greater than root.val, we recurse right. The first node where p and q diverge (one is on the left and the other on the right, or root equals p or q) is the LCA. This takes O(h) time and O(1) auxiliary space.",
                    rubric_keywords=["lowest common ancestor", "lca", "split point", "less than", "greater than", "o(h)", "diverge"],
                ),
                QuizQuestion(
                    question_id=10,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain how duplicate values can be handled in a Binary Search Tree and analyze the trade-offs of each approach.",
                    explanation="Option 1: Allow duplicates in right subtree. Option 2: Store a frequency counter within each node. Counter avoids increasing tree height and maintains O(log n) depth.",
                    concept_aspect="Handling Duplicates in BST (Frequency Counter vs Right Subtree)",
                    ideal_answer="There are two primary strategies for handling duplicate keys in a BST: 1) Node Counter: Augment each node with a frequency count. When inserting an existing key, simply increment its counter. This keeps tree height minimal and search fast. 2) Directional convention: Standardize that duplicates always go to the right (or left) subtree. This increases tree height and complicates deletion.",
                    rubric_keywords=["duplicate", "frequency count", "counter", "right subtree", "tree height", "trade-offs"],
                ),
            ]

        # 3. Binary Tree Representation and Traversals
        elif any(re.search(r"\b" + re.escape(k) + r"\b", c_lower) for k in ["traversal", "representation", "inorder", "preorder", "postorder"]):
            questions = [
                QuizQuestion(
                    question_id=1,
                    question_type=QuestionType.MCQ,
                    question_text="In an array-based binary tree representation (0-indexed), where are the left and right children of a node at index i located?",
                    options=[
                        "Left child at 2i + 1, Right child at 2i + 2",
                        "Left child at 2i, Right child at 2i + 1",
                        "Left child at i + 1, Right child at i + 2",
                        "Left child at i // 2, Right child at (i // 2) + 1",
                    ],
                    correct_option_index=0,
                    explanation="In standard 0-indexed array representations of binary trees, the left child of node i is at 2i + 1, the right child is at 2i + 2, and the parent is at (i - 1) // 2.",
                    concept_aspect="Array-based Binary Tree Indexing Formula",
                    distractor_misconceptions={
                        1: "Confusing 0-indexed array formula with 1-indexed formula (2i and 2i+1)",
                        2: "Assuming linear sequential indexing",
                        3: "Confusing parent formula with child formula",
                    },
                ),
                QuizQuestion(
                    question_id=2,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: What list of values does this preorder traversal generate?",
                    code_snippet=(
                        "class Node:\n"
                        "    def __init__(self, val, left=None, right=None):\n"
                        "        self.val, self.left, self.right = val, left, right\n\n"
                        "def preorder(n):\n"
                        "    return [n.val] + preorder(n.left) + preorder(n.right) if n else []\n\n"
                        "root = Node(1, Node(2), Node(3, Node(4)))\n"
                        "print(preorder(root))"
                    ),
                    options=["[1, 2, 3, 4]", "[2, 1, 4, 3]", "[2, 4, 3, 1]", "[1, 3, 4, 2]"],
                    correct_option_index=0,
                    explanation="Preorder visits Node -> Left -> Right. 1 is visited first, then left child 2, then right child 3, then 3's left child 4, producing [1, 2, 3, 4].",
                    concept_aspect="Predict Output: Preorder Depth-First Traversal",
                    distractor_misconceptions={
                        1: "Confusing preorder with inorder traversal",
                        2: "Confusing preorder with postorder traversal",
                        3: "Visiting right child before left child",
                    },
                ),
                QuizQuestion(
                    question_id=3,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: What string is printed by this postorder traversal?",
                    code_snippet=(
                        "def postorder(n):\n"
                        "    return postorder(n.left) + postorder(n.right) + [n.val] if n else []\n\n"
                        "root = Node('A', Node('B'), Node('C'))\n"
                        "print(''.join(postorder(root)))"
                    ),
                    options=["BCA", "ABC", "BAC", "CBA"],
                    correct_option_index=0,
                    explanation="Postorder visits Left -> Right -> Node. Left is 'B', Right is 'C', Node is 'A'. Output is 'BCA'.",
                    concept_aspect="Predict Output: Postorder Depth-First Traversal",
                    distractor_misconceptions={
                        1: "Confusing postorder with preorder ('ABC')",
                        2: "Confusing postorder with inorder ('BAC')",
                        3: "Reversing right and left children ('CBA')",
                    },
                ),
                QuizQuestion(
                    question_id=4,
                    question_type=QuestionType.MCQ,
                    question_text="Why is Post-order traversal (Left -> Right -> Node) specifically chosen when deleting or freeing a dynamically allocated binary tree?",
                    options=[
                        "It ensures child nodes are processed and freed before their parent node is deallocated.",
                        "It requires O(1) space whereas other traversals require O(n^2).",
                        "It visits nodes in alphabetical sorted order.",
                        "It converts a binary tree into a balanced AVL tree.",
                    ],
                    correct_option_index=0,
                    explanation="In postorder traversal, both subtrees are completely visited and processed before the parent node is visited, preventing dangling pointer references during deallocation.",
                    concept_aspect="Post-order Traversal for Bottom-Up Processing & Cleanup",
                    distractor_misconceptions={
                        1: "Falsely assuming space complexity differences",
                        2: "Confusing post-order with in-order sorting property",
                        3: "Confusing traversal with tree balancing",
                    },
                ),
                QuizQuestion(
                    question_id=5,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: What does level-order (BFS) traversal print for this tree?",
                    code_snippet=(
                        "from collections import deque\n"
                        "def bfs(root):\n"
                        "    res, q = [], deque([root]) if root else deque()\n"
                        "    while q:\n"
                        "        node = q.popleft()\n"
                        "        res.append(node.val)\n"
                        "        if node.left: q.append(node.left)\n"
                        "        if node.right: q.append(node.right)\n"
                        "    return res\n\n"
                        "root = Node(1, Node(2, Node(4), Node(5)), Node(3))\n"
                        "print(bfs(root))"
                    ),
                    options=["[1, 2, 3, 4, 5]", "[1, 2, 4, 5, 3]", "[4, 5, 2, 3, 1]", "[1, 3, 2, 5, 4]"],
                    correct_option_index=0,
                    explanation="BFS visits level 0 ([1]), then level 1 ([2, 3]), then level 2 ([4, 5]), yielding [1, 2, 3, 4, 5].",
                    concept_aspect="Predict Output: Level-Order Breadth-First Traversal (BFS)",
                    distractor_misconceptions={
                        1: "Confusing BFS with DFS preorder",
                        2: "Confusing BFS with postorder bottom-up",
                        3: "Reversing right and left queue pushes",
                    },
                ),
                QuizQuestion(
                    question_id=6,
                    question_type=QuestionType.MCQ,
                    question_text="Which auxiliary data structure is fundamentally required to implement an iterative Depth-First Search (DFS) without using recursion?",
                    options=["A Last-In-First-Out (LIFO) Stack", "A First-In-First-Out (FIFO) Queue", "A Min-Heap Priority Queue", "A Doubly-Linked Circular List"],
                    correct_option_index=0,
                    explanation="Recursion uses the program call stack. To simulate recursion iteratively, an explicit LIFO Stack is required.",
                    concept_aspect="Iterative DFS Simulation Using Explicit Stacks",
                    distractor_misconceptions={
                        1: "Confusing DFS stacks with BFS queues",
                        2: "Confusing DFS with priority queues",
                        3: "Assuming DFS requires linked lists",
                    },
                ),
                QuizQuestion(
                    question_id=7,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain how Inorder, Preorder, and Postorder traversals differ in visit order, and give a distinct use-case for each.",
                    explanation="Inorder (LNR): sorted order on BSTs. Preorder (NLR): serialization and tree copying. Postorder (LRN): bottom-up evaluation and deletion.",
                    concept_aspect="DFS Traversal Differences & Specific Engineering Use-Cases",
                    ideal_answer="1) Preorder (Root, Left, Right): Visits parent before children; ideal for serializing/saving a tree structure and copying trees. 2) Inorder (Left, Root, Right): Visits nodes in non-decreasing order on a Binary Search Tree; ideal for sorted iteration. 3) Postorder (Left, Right, Root): Visits children before parent; ideal for bottom-up calculation (e.g. subtree height, expression tree evaluation, and memory deletion).",
                    rubric_keywords=["inorder", "preorder", "postorder", "left root right", "root left right", "left right root", "use-case", "serialization", "deletion", "sorted"],
                ),
                QuizQuestion(
                    question_id=8,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Describe how to reconstruct a unique Binary Tree given its Preorder and Inorder traversal arrays. Why is Inorder necessary?",
                    explanation="Preorder identifies the root (first element). Inorder partitions the remaining nodes into left and right subtrees. Without Inorder, the tree structure is ambiguous.",
                    concept_aspect="Tree Reconstruction from Preorder and Inorder Traversals",
                    ideal_answer="The first element in the Preorder traversal identifies the current root node. We find this root value in the Inorder traversal array: all elements to its left belong to the left subtree, and all elements to its right belong to the right subtree. We count the left subtree size to slice both arrays and recursively construct the left and right children. Inorder is strictly necessary because preorder alone cannot disambiguate left vs right branching.",
                    rubric_keywords=["reconstruct", "preorder", "inorder", "root", "partition", "left subtree", "right subtree", "slice", "recursive"],
                ),
                QuizQuestion(
                    question_id=9,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Contrast Breadth-First (Level-Order) traversal and Depth-First traversal regarding memory usage on complete vs skewed binary trees.",
                    explanation="On a complete binary tree, BFS requires O(n) memory (last level has n/2 nodes), whereas DFS requires O(log n). On a skewed tree, DFS requires O(n) call stack, while BFS requires O(1).",
                    concept_aspect="Space Complexity Comparison: BFS vs DFS Across Tree Shapes",
                    ideal_answer="On a balanced/complete binary tree of n nodes, DFS memory is bounded by tree height O(log n) on the call stack, whereas BFS queue must hold the widest level containing n/2 nodes, requiring O(n) space. Conversely, on a degenerate skewed tree, DFS call stack grows linearly to O(n), while BFS queue size never exceeds 1 node, using O(1) auxiliary space.",
                    rubric_keywords=["bfs", "dfs", "space complexity", "queue", "call stack", "complete tree", "skewed tree", "o(log n)", "o(n)"],
                ),
                QuizQuestion(
                    question_id=10,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain how Morris Traversal achieves Inorder traversal with O(1) auxiliary space by creating temporary threaded links.",
                    explanation="Finds the in-order predecessor. If predecessor's right child is null, points it to current node (thread) and moves left. If already pointing to current, removes thread, visits node, and moves right.",
                    concept_aspect="Morris In-order Threaded Traversal Algorithm",
                    ideal_answer="Morris Traversal achieves O(1) extra space without recursion or an explicit stack using threaded binary trees. For each node, it locates its in-order predecessor (rightmost node of left subtree). If the predecessor's right pointer is null, it temporarily links it to the current node and steps left. When it encounters the link again, it unlinks it, visits the current node, and steps right, restoring the tree.",
                    rubric_keywords=["morris traversal", "o(1) space", "threaded", "in-order predecessor", "temporary link", "null", "restore"],
                ),
            ]

        # 4. Tree Problem-Solving Patterns and Applications
        elif any(re.search(r"\b" + re.escape(k) + r"\b", c_lower) for k in ["problem-solving", "pattern", "application", "patterns", "diameter", "lca", "symmetric"]):
            questions = [
                QuizQuestion(
                    question_id=1,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: What is the maximum depth (height) of this binary tree?",
                    code_snippet=(
                        "class Node:\n"
                        "    def __init__(self, val, left=None, right=None):\n"
                        "        self.val, self.left, self.right = val, left, right\n\n"
                        "def max_depth(root):\n"
                        "    if not root: return 0\n"
                        "    return 1 + max(max_depth(root.left), max_depth(root.right))\n\n"
                        "root = Node(1, Node(2, Node(3)), Node(4))\n"
                        "print(max_depth(root))"
                    ),
                    options=["3", "2", "4", "1"],
                    correct_option_index=0,
                    explanation="The longest path from root to leaf is 1 -> 2 -> 3, which contains 3 nodes. max_depth returns 3.",
                    concept_aspect="Predict Output: Binary Tree Maximum Depth",
                    distractor_misconceptions={
                        1: "Only counting the right branch (1 -> 4)",
                        2: "Counting total nodes instead of height",
                        3: "Returning 0-indexed edge count instead of node height",
                    },
                ),
                QuizQuestion(
                    question_id=2,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: What boolean result does is_same_tree return for t1 and t2?",
                    code_snippet=(
                        "def is_same_tree(p, q):\n"
                        "    if not p and not q: return True\n"
                        "    if not p or not q or p.val != q.val: return False\n"
                        "    return is_same_tree(p.left, q.left) and is_same_tree(p.right, q.right)\n\n"
                        "t1 = Node(1, Node(2), None)\n"
                        "t2 = Node(1, None, Node(2))\n"
                        "print(is_same_tree(t1, t2))"
                    ),
                    options=["False", "True", "None", "Error"],
                    correct_option_index=0,
                    explanation="In t1, node 2 is the left child. In t2, node 2 is the right child. Structurally they are different, so is_same_tree evaluates to False.",
                    concept_aspect="Predict Output: Tree Structural Identity Check",
                    distractor_misconceptions={
                        1: "Believing trees with identical values regardless of branch position are same",
                        2: "Assuming node comparison checks only sets of values",
                        3: "Confusing boolean evaluation with None",
                    },
                ),
                QuizQuestion(
                    question_id=3,
                    question_type=QuestionType.MCQ,
                    question_text="What defines the Diameter of a Binary Tree?",
                    options=[
                        "The length (number of edges) of the longest path between any two nodes, which may or may not pass through the root.",
                        "The total number of nodes located on the bottom-most level of the tree.",
                        "The maximum number of children any node in the tree possesses.",
                        "The difference in depth between the leftmost and rightmost leaf nodes.",
                    ],
                    correct_option_index=0,
                    explanation="The diameter of a binary tree is the length of the longest path between any two nodes. Crucially, this path does not necessarily need to pass through the root.",
                    concept_aspect="Binary Tree Diameter Definition",
                    distractor_misconceptions={
                        1: "Confusing diameter with tree width at a given level",
                        2: "Confusing diameter with tree degree",
                        3: "Assuming the diameter must always pass through the root node",
                    },
                ),
                QuizQuestion(
                    question_id=4,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: What are the left and right values of the root after running invert_tree?",
                    code_snippet=(
                        "def invert_tree(root):\n"
                        "    if not root: return None\n"
                        "    root.left, root.right = invert_tree(root.right), invert_tree(root.left)\n"
                        "    return root\n\n"
                        "root = Node(4, Node(2), Node(7))\n"
                        "invert_tree(root)\n"
                        "print(f'{root.left.val} {root.right.val}')"
                    ),
                    options=["7 2", "2 7", "4 4", "7 4"],
                    correct_option_index=0,
                    explanation="invert_tree mirrors the binary tree by swapping left and right subtrees. The left child becomes 7 and the right child becomes 2: '7 2'.",
                    concept_aspect="Predict Output: Inverting / Mirroring a Binary Tree",
                    distractor_misconceptions={
                        1: "Assuming children remain in original positions",
                        2: "Replacing child values with root value",
                        3: "Swapping only one side",
                    },
                ),
                QuizQuestion(
                    question_id=5,
                    question_type=QuestionType.MCQ,
                    question_text="In an arbitrary (non-BST) binary tree, how does the Lowest Common Ancestor (LCA) recursive algorithm identify the common ancestor of nodes p and q?",
                    options=[
                        "If p is found in the left subtree and q is found in the right subtree (or vice versa), the current node is the LCA.",
                        "By subtracting node keys and checking if difference is zero.",
                        "By computing the arithmetic mean of p.val and q.val.",
                        "By performing Dijkstra's shortest path algorithm.",
                    ],
                    correct_option_index=0,
                    explanation="If recursive DFS finds one target node in the left subtree and the other in the right subtree, the current node is their lowest split point / LCA.",
                    concept_aspect="Arbitrary Binary Tree LCA Identification Pattern",
                    distractor_misconceptions={
                        1: "Assuming non-BST nodes can use key value comparisons like BSTs",
                        2: "Confusing LCA with numerical arithmetic means",
                        3: "Confusing tree ancestor search with graph shortest paths",
                    },
                ),
                QuizQuestion(
                    question_id=6,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: What does has_path_sum print when searching for target sum 8?",
                    code_snippet=(
                        "def has_path_sum(root, target):\n"
                        "    if not root: return False\n"
                        "    if not root.left and not root.right: return target == root.val\n"
                        "    rem = target - root.val\n"
                        "    return has_path_sum(root.left, rem) or has_path_sum(root.right, rem)\n\n"
                        "# Tree: 5 -> left=3 (leaf), right=2 (has left=1)\n"
                        "root = Node(5, Node(3), Node(2, Node(1)))\n"
                        "print(has_path_sum(root, 8))"
                    ),
                    options=["True", "False", "8", "None"],
                    correct_option_index=0,
                    explanation="The root-to-leaf path 5 -> 3 sums to 5 + 3 = 8. Since 3 is a leaf, has_path_sum evaluates to True.",
                    concept_aspect="Predict Output: Root-to-Leaf Path Sum Backtracking",
                    distractor_misconceptions={
                        1: "Failing to check the left leaf path (5 + 3 = 8)",
                        2: "Returning the sum value instead of boolean",
                        3: "Continuing past leaf node 3",
                    },
                ),
                QuizQuestion(
                    question_id=7,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain the recursive algorithm to check whether a binary tree is Symmetric (a mirror image of itself around its center).",
                    explanation="Two trees are mirrors if roots have same value, and left subtree of tree1 is mirror of right subtree of tree2, and right subtree of tree1 is mirror of left subtree of tree2.",
                    concept_aspect="Symmetric Tree Mirror Verification Algorithm",
                    ideal_answer="A binary tree is symmetric if its left and right subtrees are mirror reflections of each other. We use a helper function is_mirror(t1, t2): 1) If both t1 and t2 are null, return True. 2) If only one is null or t1.val != t2.val, return False. 3) Recursively return is_mirror(t1.left, t2.right) and is_mirror(t1.right, t2.left).",
                    rubric_keywords=["symmetric", "mirror", "reflection", "t1.left", "t2.right", "t1.right", "t2.left", "recursive"],
                ),
                QuizQuestion(
                    question_id=8,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Describe how to compute the Diameter of a Binary Tree in O(N) time using bottom-up post-order DFS without recalculating heights repeatedly.",
                    explanation="Postorder helper returns height of current subtree. At each node, compute left_height + right_height as candidate diameter, update global max, and return 1 + max(left, right).",
                    concept_aspect="O(N) Bottom-Up Diameter Calculation Pattern",
                    ideal_answer="A naive algorithm calculates height at every node resulting in O(N^2) time. To achieve O(N) time, we compute height bottom-up in a single post-order DFS pass. At each node, we recursively obtain left_height and right_height. The longest path passing through this node is left_height + right_height. We update a running global maximum diameter with this value, and return 1 + max(left_height, right_height) to the parent.",
                    rubric_keywords=["diameter", "o(n)", "bottom-up", "post-order", "left_height", "right_height", "global maximum", "single pass"],
                ),
                QuizQuestion(
                    question_id=9,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain how a Trie (Prefix Tree) applies tree hierarchical branching to solve prefix searching and autocomplete efficiently compared to hash tables.",
                    explanation="Trie nodes store characters on edges. Prefix search takes O(L) where L is query length, independent of the number of words N. Hash tables cannot perform prefix search in O(L).",
                    concept_aspect="Trie (Prefix Tree) Architecture & Prefix Matching Applications",
                    ideal_answer="A Trie is an n-ary tree where each node represents a character along a string path, with a boolean flag marking end-of-word. Unlike hash tables where looking up words with a given prefix requires scanning all entries O(N * L), a Trie finds all words with prefix P in O(|P| + matches) time by simply following prefix edges down to the branch root, making it ideal for autocomplete and spell checking.",
                    rubric_keywords=["trie", "prefix tree", "autocomplete", "prefix search", "o(l)", "hash table", "end-of-word", "branching"],
                ),
                QuizQuestion(
                    question_id=10,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain how the Maximum Path Sum problem in a binary tree handles negative node values during bottom-up dynamic programming.",
                    explanation="If a subtree's max gain is negative, we prune it by taking max(0, gain). The node's split path sum is val + left_gain + right_gain.",
                    concept_aspect="Binary Tree Maximum Path Sum with Negative Values",
                    ideal_answer="In Maximum Path Sum, any node can have negative values. When recursively computing the maximum contribution (gain) from the left and right subtrees, we must clamp negative gains to 0 using max(0, subtree_gain), which effectively prunes branches that would decrease the total sum. At each node, we test the complete path (node.val + left_gain + right_gain) against the global maximum, and return node.val + max(left_gain, right_gain) upwards.",
                    rubric_keywords=["maximum path sum", "negative values", "prune", "max(0, ...)", "gain", "global maximum", "bottom-up"],
                ),
            ]

        # 5. Tree Fundamentals and Terminology (Default for initial tree subtopic)
        elif any(re.search(r"\b" + re.escape(k) + r"\b", c_lower) for k in ["tree", "fundamental", "terminology", "dsa", "node", "leaf"]):
            questions = [
                QuizQuestion(
                    question_id=1,
                    question_type=QuestionType.MCQ,
                    question_text="In any valid tree data structure containing N vertices (nodes), how many total edges must it possess?",
                    options=["Exactly N - 1 edges", "Exactly N edges", "N + 1 edges", "N * (N - 1) / 2 edges"],
                    correct_option_index=0,
                    explanation="A fundamental graph theory property of any tree is that an acyclic connected graph with N vertices always contains strictly N - 1 edges.",
                    concept_aspect="Tree Edge to Vertex Mathematical Invariant (E = N - 1)",
                    distractor_misconceptions={
                        1: "Believing a tree has equal edges and vertices (which forms a cycle)",
                        2: "Adding extraneous edge count",
                        3: "Confusing trees with complete graphs Kn",
                    },
                ),
                QuizQuestion(
                    question_id=2,
                    question_type=QuestionType.MCQ,
                    question_text="Which term correctly identifies the topmost node in a tree hierarchy, which has an in-degree of 0 (no parent)?",
                    options=["Root Node", "Leaf Node", "Branch Node", "Sibling Node"],
                    correct_option_index=0,
                    explanation="The root node is the topmost node in a tree hierarchy from which all other nodes descend; it has in-degree 0 (no parent).",
                    concept_aspect="Tree Root Node Definition & In-degree Property",
                    distractor_misconceptions={
                        1: "Confusing the root node with terminal leaf nodes",
                        2: "Using informal branch terminology instead of formal root definition",
                        3: "Confusing parent-child relationships with siblings",
                    },
                ),
                QuizQuestion(
                    question_id=3,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: What value does this simple tree node linkage print?",
                    code_snippet=(
                        "class TreeNode:\n"
                        "    def __init__(self, val, left=None, right=None):\n"
                        "        self.val = val\n"
                        "        self.left = left\n"
                        "        self.right = right\n\n"
                        "root = TreeNode(10, TreeNode(5), TreeNode(15))\n"
                        "print(root.left.val + root.right.val)"
                    ),
                    options=["20", "10", "30", "15"],
                    correct_option_index=0,
                    explanation="root.left.val is 5, root.right.val is 15. The sum 5 + 15 = 20 is printed.",
                    concept_aspect="Predict Output: Basic TreeNode Object Linkage",
                    distractor_misconceptions={
                        1: "Returning the root value instead of children sum",
                        2: "Summing all three nodes including root (30)",
                        3: "Accessing only right child",
                    },
                ),
                QuizQuestion(
                    question_id=4,
                    question_type=QuestionType.MCQ,
                    question_text="What is the precise definition of a Leaf Node (Terminal Node) in a tree?",
                    options=[
                        "A node having degree 0 (it has zero child nodes)",
                        "A node with exactly one child",
                        "The node located at index 0 of an array",
                        "Any node that has both a parent and at least one child",
                    ],
                    correct_option_index=0,
                    explanation="A leaf node (terminal or external node) has out-degree 0, meaning it has no children.",
                    concept_aspect="Leaf Node Definition and Out-degree",
                    distractor_misconceptions={
                        1: "Confusing leaf nodes with single-child internal nodes",
                        2: "Confusing leaf nodes with array root index",
                        3: "Confusing leaf nodes with internal branch nodes",
                    },
                ),
                QuizQuestion(
                    question_id=5,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the output: How many leaf nodes are counted by this count_leaves function?",
                    code_snippet=(
                        "def count_leaves(node):\n"
                        "    if not node: return 0\n"
                        "    if not node.left and not node.right: return 1\n"
                        "    return count_leaves(node.left) + count_leaves(node.right)\n\n"
                        "# Tree: Root(1) with left child 2 (has child 4) and right child 3\n"
                        "root = TreeNode(1, TreeNode(2, TreeNode(4)), TreeNode(3))\n"
                        "print(count_leaves(root))"
                    ),
                    options=["2", "3", "4", "1"],
                    correct_option_index=0,
                    explanation="Node 4 has no children (leaf 1). Node 3 has no children (leaf 2). Node 2 has child 4 (not a leaf). Node 1 has children (not a leaf). Total leaves = 2.",
                    concept_aspect="Predict Output: Recursive Leaf Node Counting",
                    distractor_misconceptions={
                        1: "Counting node 2 as a leaf",
                        2: "Counting all nodes in the tree",
                        3: "Counting only the right leaf",
                    },
                ),
                QuizQuestion(
                    question_id=6,
                    question_type=QuestionType.MCQ,
                    question_text="What is the distinction between the Depth of a node and the Height of a node in a tree?",
                    options=[
                        "Depth is the number of edges from root down to the node; Height is the number of edges on the longest path from the node down to a leaf.",
                        "Depth and Height are identical interchangeable terms.",
                        "Depth is measured from leaf upwards; Height is measured from root downwards.",
                        "Height is the total number of siblings a node has.",
                    ],
                    correct_option_index=0,
                    explanation="Depth measures distance from the root downwards (root has depth 0). Height measures distance from the node down to its deepest leaf (leaves have height 0).",
                    concept_aspect="Node Depth vs Node Height Distinction",
                    distractor_misconceptions={
                        1: "Treating depth and height as synonyms",
                        2: "Inverting the reference frames of depth and height",
                        3: "Confusing height with node degree or sibling count",
                    },
                ),
                QuizQuestion(
                    question_id=7,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain the difference between the Depth of a node, the Height of a node, and the Height of a tree.",
                    explanation="Depth: edges from root to node. Height of node: longest edges from node to leaf. Height of tree: height of root node (or maximum depth of any leaf).",
                    concept_aspect="Tree Depth vs Height Reference Frames",
                    ideal_answer="1) Depth of a node is the length of the path (number of edges) from the tree root down to that specific node. The root has depth 0. 2) Height of a node is the length of the longest path from that node down to a descendant leaf node. Leaf nodes have height 0. 3) Height of a tree is the height of its root node, which equals the maximum depth of any node in the tree.",
                    rubric_keywords=["depth", "height", "root", "leaf", "edges", "path", "maximum depth", "longest path"],
                ),
                QuizQuestion(
                    question_id=8,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Differentiate between the Degree of a node and the Degree of a tree, giving examples.",
                    explanation="Degree of a node: number of children it has. Degree of a tree: maximum degree among all nodes in the tree.",
                    concept_aspect="Degree of Node vs Degree of Tree",
                    ideal_answer="The degree of a node is the total number of direct subtrees or child nodes branching from it. A leaf node has degree 0, while a binary node can have degree 0, 1, or 2. The degree of a tree is the maximum degree of any node in that tree (e.g. a binary tree has degree 2, while a ternary tree has degree 3).",
                    rubric_keywords=["degree of node", "degree of tree", "children", "maximum degree", "binary tree", "leaf degree 0"],
                ),
                QuizQuestion(
                    question_id=9,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Contrast a Binary Tree with a General (N-ary) Tree regarding node storage and child relationships.",
                    explanation="In a binary tree, children are ordered strictly as left and right (at most 2). In an n-ary tree, nodes can have arbitrary numbers of children, often stored as a list or First-Child Next-Sibling representation.",
                    concept_aspect="Binary Tree vs General N-ary Tree Structural Representation",
                    ideal_answer="In a Binary Tree, each node has at most two children, explicitly designated as the left child and right child, meaning order matters (a left child is structurally distinct from a right child). In a General (N-ary) Tree, each node can have an arbitrary number of children. In memory, N-ary trees are commonly implemented either via dynamic child pointer arrays or the memory-efficient 'First-Child Next-Sibling' linked representation.",
                    rubric_keywords=["binary tree", "n-ary tree", "general tree", "at most two", "left and right", "first-child next-sibling", "child array"],
                ),
                QuizQuestion(
                    question_id=10,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Differentiate between a Full Binary Tree and a Complete Binary Tree. What structural invariants must be satisfied for each?",
                    explanation="Full binary tree: every node has either 0 or 2 children. Complete binary tree: all levels full except possibly the last, which is filled from left to right without gaps.",
                    concept_aspect="Full Binary Tree vs Complete Binary Tree Criteria",
                    ideal_answer="A Full Binary Tree requires that every node has either 0 or 2 children (no node has exactly 1 child). A Complete Binary Tree requires that all levels are entirely filled, except possibly the deepest level, which must be filled contiguously from left to right without any missing gaps. A complete tree can be mapped directly to an array without wasted space.",
                    rubric_keywords=["full binary tree", "complete binary tree", "two children", "leaf", "all levels", "left to right", "contiguous"],
                ),
            ]
        elif any(re.search(r"\b" + re.escape(k) + r"\b", c_lower) for k in ["async", "concurren", "event loop", "await", "coroutine", "aiohttp"]):
            questions = [
                # 6 MCQs
                QuizQuestion(
                    question_id=1,
                    question_type=QuestionType.MCQ,
                    question_text="In Python's asyncio model, what actually happens when an `await` expression is executed within a coroutine?",
                    options=[
                        "Execution of the current coroutine is suspended, yielding control back to the event loop so other ready tasks can run.",
                        "The operating system immediately spawns a new background thread to execute the awaited function concurrently.",
                        "The entire Python process halts and blocks waiting for the awaited call, preventing any other code from running.",
                        "The Python Global Interpreter Lock (GIL) is permanently disabled for all coroutines in the application.",
                    ],
                    correct_option_index=0,
                    explanation="`await` cooperatively yields control back to the single-threaded event loop so other scheduled tasks can make progress while I/O is pending.",
                    concept_aspect="Cooperative Event Loop & Non-blocking I/O",
                    distractor_misconceptions={
                        1: "Belief that asyncio automatically spawns parallel OS threads for coroutines",
                        2: "Belief that await is a synchronous blocking call freezing the process",
                        3: "Conflating Python GIL management with cooperative task scheduling",
                    },
                ),
                QuizQuestion(
                    question_id=2,
                    question_type=QuestionType.MCQ,
                    question_text="Why does calling synchronous `time.sleep(5)` inside an `async def` route handler harm an asyncio web server?",
                    options=[
                        "It issues a synchronous blocking syscall on the main thread, freezing the single event loop and stalling all other concurrent requests.",
                        "It triggers an unhandled asyncio.InvalidStateError because sleep is forbidden in coroutines.",
                        "It consumes 100% of all host CPU cores in a busy-wait spinlock.",
                        "It prematurely closes all existing client TCP connections due to network reset.",
                    ],
                    correct_option_index=0,
                    explanation="Since asyncio runs on a single event loop thread by default, blocking calls like `time.sleep` block the entire loop. `await asyncio.sleep()` should be used instead.",
                    concept_aspect="Blocking Calls vs Asynchronous Non-blocking Sleep",
                    distractor_misconceptions={
                        1: "Believing time.sleep triggers syntax/runtime type exceptions rather than loop starvation",
                        2: "Confusing OS kernel sleep blocking with CPU-bound busy-wait loops",
                        3: "Assuming application thread blocking directly resets network sockets",
                    },
                ),
                QuizQuestion(
                    question_id=3,
                    question_type=QuestionType.MCQ,
                    question_text="What is the distinction between an `async def` coroutine function and an asyncio `Task`?",
                    options=[
                        "A coroutine is an inactive generator-like object until awaited or scheduled; a Task wraps a coroutine and actively schedules it on the event loop.",
                        "A Task runs in a separate process with isolated memory, whereas a coroutine shares thread state.",
                        "A coroutine can only run synchronous code, whereas a Task can run multi-threaded GPU code.",
                        "There is no difference; coroutine and Task are identical aliases.",
                    ],
                    correct_option_index=0,
                    explanation="Calling a coroutine function returns a coroutine object. Wrapping it with `asyncio.create_task()` schedules its execution concurrently on the event loop.",
                    concept_aspect="Coroutines vs Asyncio Tasks",
                    distractor_misconceptions={
                        1: "Confusing asyncio Tasks with multiprocessing Processes",
                        2: "Assuming coroutines are restricted to synchronous operations",
                        3: "Assuming coroutines and Tasks are identical without lifecycle differences",
                    },
                ),
                QuizQuestion(
                    question_id=4,
                    question_type=QuestionType.MCQ,
                    question_text="How does `asyncio.gather(*tasks)` handle concurrent execution and return values?",
                    options=[
                        "It runs multiple awaitable tasks concurrently and returns a list of their results in the exact order they were passed.",
                        "It runs tasks sequentially one by one in alphabetical order.",
                        "It drops all results except the single fastest completing task.",
                        "It spawns a worker thread pool for every task passed.",
                    ],
                    correct_option_index=0,
                    explanation="`asyncio.gather` aggregates multiple awaitable objects, executes them concurrently, and yields results preserving original argument order.",
                    concept_aspect="Concurrent Task Aggregation with asyncio.gather",
                    distractor_misconceptions={
                        1: "Believing gather executes tasks in strict sequential order",
                        2: "Confusing asyncio.gather with asyncio.wait(return_when=FIRST_COMPLETED)",
                        3: "Assuming gather requires OS thread pools",
                    },
                ),
                QuizQuestion(
                    question_id=5,
                    question_type=QuestionType.MCQ,
                    question_text="When should `asyncio.Semaphore` be utilized in an asynchronous network scraper?",
                    options=[
                        "To bound and throttle the maximum number of simultaneous outgoing HTTP connections.",
                        "To encrypt outgoing HTTPS packets with private TLS keys.",
                        "To automatically parse HTML DOM trees using multiprocessing.",
                        "To restart crashed Python processes upon network timeout.",
                    ],
                    correct_option_index=0,
                    explanation="Semaphores limit concurrent access to shared resources or external APIs to avoid server rate limiting and socket exhaustion.",
                    concept_aspect="Concurrency Throttling with Semaphores",
                    distractor_misconceptions={
                        1: "Confusing semaphores with network packet encryption",
                        2: "Confusing concurrency limits with HTML DOM parsing",
                        3: "Confusing synchronization primitives with process supervisor daemons",
                    },
                ),
                QuizQuestion(
                    question_id=6,
                    question_type=QuestionType.MCQ,
                    question_text="If CPU-heavy computation (like heavy image processing or cryptography) is needed inside an asyncio program, how should it be handled?",
                    options=[
                        "Offload the heavy CPU work to a ProcessPoolExecutor using `loop.run_in_executor`.",
                        "Execute it directly inside the main coroutine with `await`.",
                        "Wrap the synchronous math loop inside an empty async function.",
                        "Call `asyncio.sleep(0)` before every arithmetic calculation.",
                    ],
                    correct_option_index=0,
                    explanation="CPU-bound tasks block the event loop and cannot yield via I/O; they must be offloaded to separate OS processes via ProcessPoolExecutor.",
                    concept_aspect="CPU-bound Work vs I/O-bound Concurrency",
                    distractor_misconceptions={
                        1: "Believing async/await magically accelerates CPU-bound mathematical operations",
                        2: "Assuming async def syntax automatically multi-threads CPU work",
                        3: "Believing sleep(0) allows parallel CPU utilization",
                    },
                ),
                # 4 Descriptive Questions
                QuizQuestion(
                    question_id=7,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain how the Python Event Loop coordinates asynchronous tasks. How does it manage tasks that are waiting for network I/O?",
                    explanation="The event loop maintains a queue of ready tasks. When a task awaits I/O, it registers an OS event listener (via epoll/kqueue/IOCP) and pauses. The loop runs other ready tasks. When OS signals I/O completion, the paused task is placed back on the ready queue.",
                    concept_aspect="Event Loop Mechanics & OS Selector Multiplexing",
                    ideal_answer="The event loop is a single-threaded execution manager. When a task hits an `await` on network I/O, it registers a non-blocking socket with the OS selector (epoll/kqueue) and yields control. The event loop immediately switches to execute other ready tasks. Once the OS signals data is ready, the event loop resumes the paused coroutine.",
                    rubric_keywords=["event loop", "single thread", "yield", "non-blocking", "os selector", "epoll", "resume"],
                ),
                QuizQuestion(
                    question_id=8,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Describe the difference between Concurrency and Parallelism. How does asyncio achieve concurrency without multi-threading?",
                    explanation="Concurrency is dealing with lots of things at once (structure); parallelism is doing lots of things at once (execution on multiple cores). Asyncio achieves concurrency via cooperative multitasking on a single thread.",
                    concept_aspect="Concurrency vs Parallelism in Python",
                    ideal_answer="Concurrency is about managing multiple tasks in progress simultaneously by interleaving execution during wait times, whereas parallelism executes multiple computations at the exact same physical instant across multiple CPU cores. Asyncio achieves concurrency on a single thread through cooperative multitasking, switching tasks whenever one yields during I/O wait.",
                    rubric_keywords=["concurrency", "parallelism", "cooperative multitasking", "interleaving", "single thread", "multiple cores"],
                ),
                QuizQuestion(
                    question_id=9,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain why exception handling inside concurrent tasks (e.g. within `asyncio.gather`) requires careful consideration, and how `return_exceptions=True` impacts error handling.",
                    explanation="By default, if one task in gather raises an exception, other tasks continue running but gather immediately raises the first exception, potentially leaking or ignoring errors in sibling tasks. With return_exceptions=True, exceptions are treated as return values in the output list.",
                    concept_aspect="Exception Handling in Concurrent Asyncio Workflows",
                    ideal_answer="In asyncio.gather, by default, the first exception raised immediately bubbles up, which can cause other tasks' results or exceptions to be lost or unhandled. Setting return_exceptions=True prevents early failure by capturing raised Exception instances directly into the returned result list, allowing the caller to inspect and handle failures individually for each task.",
                    rubric_keywords=["exception", "gather", "return_exceptions", "bubble up", "task failure", "unhandled"],
                ),
                QuizQuestion(
                    question_id=10,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Discuss best practices for closing async resources (such as `aiohttp.ClientSession` or database connections) to avoid unclosed connector warnings and resource leaks.",
                    explanation="Async network clients maintain open connection pools and TCP sockets. They must be cleanly closed using async context managers (`async with`) to guarantee graceful socket termination and loop shutdown.",
                    concept_aspect="Asynchronous Resource Lifecycle & Context Managers",
                    ideal_answer="Async resources like aiohttp ClientSession or database connection pools manage underlying network sockets and file descriptors. They should always be managed using `async with` context managers. This guarantees that `close()` and socket teardown are executed even if an unhandled error occurs, avoiding resource leakage and dangling connector warnings.",
                    rubric_keywords=["async with", "context manager", "connection pool", "close", "socket leak", "resource cleanup"],
                ),
            ]
        elif any(re.search(r"\b" + re.escape(k) + r"\b", c_lower) for k in ["api", "rest", "fastapi", "pydantic", "http"]):
            questions = [
                # 6 MCQs
                QuizQuestion(
                    question_id=1,
                    question_type=QuestionType.MCQ,
                    question_text="What does idempotency mean when designing RESTful HTTP APIs?",
                    options=[
                        "Making multiple identical requests has the same intended effect on server state as making a single request.",
                        "The server always returns identical HTTP response bodies for any given client IP address.",
                        "The API endpoint executes within a fixed time budget regardless of workload.",
                        "All incoming request payloads are encrypted with symmetric AES keys.",
                    ],
                    correct_option_index=0,
                    explanation="An idempotent operation (like GET, PUT, or DELETE) can be safely retried without unintentionally modifying resource state repeatedly.",
                    concept_aspect="RESTful HTTP Idempotency Semantics",
                    distractor_misconceptions={
                        1: "Confusing server state idempotency with static response caching",
                        2: "Confusing HTTP idempotency with real-time execution guarantees",
                        3: "Conflating protocol semantics with transport payload encryption",
                    },
                ),
                QuizQuestion(
                    question_id=2,
                    question_type=QuestionType.MCQ,
                    question_text="In modern Python API frameworks like FastAPI, what primary role does Pydantic serve during request handling?",
                    options=[
                        "Parsing incoming request bodies, strictly validating field types/constraints, and generating OpenAPI schemas.",
                        "Compiling Python route functions into native C++ shared libraries for faster CPU execution.",
                        "Managing PostgreSQL database connection pools and ACID transactions directly.",
                        "Handling TLS handshake termination and SSL certificate rotation.",
                    ],
                    correct_option_index=0,
                    explanation="Pydantic provides data validation and parsing using Python type hints, producing structured validation errors and OpenAPI specifications.",
                    concept_aspect="Schema Validation & Serialization",
                    distractor_misconceptions={
                        1: "Confusing runtime schema validation with ahead-of-time C++ compilation",
                        2: "Confusing data validation models with database ORM connection poolers",
                        3: "Conflating application validation with network TLS termination",
                    },
                ),
                QuizQuestion(
                    question_id=3,
                    question_type=QuestionType.MCQ,
                    question_text="Which HTTP status code should be returned when a resource is successfully created via a POST request?",
                    options=[
                        "201 Created",
                        "200 OK",
                        "204 No Content",
                        "202 Accepted",
                    ],
                    correct_option_index=0,
                    explanation="HTTP status 201 Created is the standard response indicating that a new resource has been successfully created on the server.",
                    concept_aspect="HTTP Response Status Codes for Resource Creation",
                    distractor_misconceptions={
                        1: "Using generic 200 OK instead of specific 201 Created",
                        2: "Confusing creation with 204 No Content",
                        3: "Confusing synchronous creation with 202 Accepted asynchronous processing",
                    },
                ),
                QuizQuestion(
                    question_id=4,
                    question_type=QuestionType.MCQ,
                    question_text="What is the key functional difference between HTTP PUT and HTTP PATCH methods?",
                    options=[
                        "PUT replaces the entire resource representation; PATCH applies a partial update to specific fields.",
                        "PUT is for creating resources; PATCH is strictly for deleting resources.",
                        "PUT cannot be cached; PATCH is always cached by CDN proxies.",
                        "PUT requires XML; PATCH requires JSON.",
                    ],
                    correct_option_index=0,
                    explanation="PUT is idempotent and replaces the complete resource, whereas PATCH modifies only the specified attributes.",
                    concept_aspect="PUT vs PATCH Resource Modification Semantics",
                    distractor_misconceptions={
                        1: "Confusing PATCH with deletion operations",
                        2: "Assuming PUT and PATCH have contrasting proxy caching rules",
                        3: "Assuming HTTP verbs dictate payload serialization formats",
                    },
                ),
                QuizQuestion(
                    question_id=5,
                    question_type=QuestionType.MCQ,
                    question_text="In FastAPI, how does Dependency Injection (`Depends`) facilitate clean architecture?",
                    options=[
                        "It decouples shared logic (such as DB sessions, auth checks, rate limiters) from route handlers, injecting them at request time.",
                        "It converts all synchronous functions into multi-threaded assembly routines.",
                        "It forces all route handlers to run on separate physical database servers.",
                        "It prevents client browsers from inspecting JSON response payloads.",
                    ],
                    correct_option_index=0,
                    explanation="FastAPI's dependency injection system allows developers to declare reusable dependencies that run before or around endpoint logic.",
                    concept_aspect="FastAPI Dependency Injection Architecture",
                    distractor_misconceptions={
                        1: "Confusing dependency injection with binary assembly compilation",
                        2: "Confusing application DI with database clustering",
                        3: "Assuming DI is a client-side payload obfuscation mechanism",
                    },
                ),
                QuizQuestion(
                    question_id=6,
                    question_type=QuestionType.MCQ,
                    question_text="Why should JWT (JSON Web Tokens) access tokens have a relatively short expiration time (e.g. 15-30 minutes)?",
                    options=[
                        "Because stateless JWTs cannot be easily revoked without server-side blacklisting; short lifetimes limit the exposure window if compromised.",
                        "Because JWT cryptographic algorithms fail after 1,000 mathematical operations.",
                        "Because browsers automatically delete HTTP headers that exceed 30 minutes in age.",
                        "Because longer JWT tokens consume too much CPU memory to verify.",
                    ],
                    correct_option_index=0,
                    explanation="Since JWTs are self-contained and verified statelessly via cryptographic signatures, revoking an individual token is hard; short expiry times paired with refresh tokens minimize exposure.",
                    concept_aspect="Stateless JWT Authentication & Security Windows",
                    distractor_misconceptions={
                        1: "Believing cryptographic verification degrades over time",
                        2: "Confusing HTTP header lifecycles with token payload expiration",
                        3: "Believing token lifespan impacts CPU memory footprint",
                    },
                ),
                # 4 Descriptive Questions
                QuizQuestion(
                    question_id=7,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain the core constraints of REST architecture (e.g. Statelessness, Uniform Interface, Client-Server separation). Why is statelessness essential for scalability?",
                    explanation="Statelessness means each request from client to server must contain all of the information necessary to understand and complete the request, without relying on stored server session state. This allows any server in a cluster to handle any request.",
                    concept_aspect="REST Architectural Constraints & Stateless Scalability",
                    ideal_answer="REST architecture requires separation of concerns between client and server, a uniform interface, and strict statelessness. Statelessness means the server retains no client context between requests; every incoming request contains all necessary auth and data. This allows horizontal scaling across multiple servers without session replication.",
                    rubric_keywords=["stateless", "client-server", "horizontal scaling", "session", "uniform interface"],
                ),
                QuizQuestion(
                    question_id=8,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain how database session lifecycles (like SQLAlchemy sessions) should be managed within API request handlers to prevent connection pool exhaustion and transaction leaks.",
                    explanation="Database sessions should be opened per request and closed/yielded using context managers or FastAPI dependencies with try/finally blocks to ensure rollback on error and release back to pool.",
                    concept_aspect="Database Session Lifecycles & Connection Pooling",
                    ideal_answer="A database session should be created on demand when an API request begins, utilized during handler execution, and explicitly closed in a `finally` block or FastAPI `yield` dependency. This guarantees that connections are returned to the pool and uncommitted transactions are rolled back if an error occurs.",
                    rubric_keywords=["session", "connection pool", "yield", "finally", "rollback", "commit", "leak"],
                ),
                QuizQuestion(
                    question_id=9,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Compare Session-based Authentication (stateful with cookies) versus Token-based Authentication (stateless with JWTs). What are the trade-offs of each?",
                    explanation="Session auth stores session IDs in server memory/Redis, enabling instant revocation but requiring state synchronization across nodes. JWT auth is stateless and verifiable by any service via cryptographic signature, but instant revocation requires a blacklist.",
                    concept_aspect="Stateful Sessions vs Stateless JWT Authentication Trade-offs",
                    ideal_answer="Session authentication stores session data on the server (e.g. in Redis or DB) and sends a cookie ID to the client; this allows easy server-side revocation but requires shared state across server nodes. Token authentication (like JWT) stores claims signed cryptographically in the token itself; it is stateless and scales easily across microservices, but revoking a compromised token before expiry is difficult.",
                    rubric_keywords=["session", "cookie", "jwt", "stateless", "stateful", "revocation", "horizontal scaling"],
                ),
                QuizQuestion(
                    question_id=10,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Discuss how API versioning and structured error responses (such as RFC 7807 Problem Details) help maintain backwards compatibility and client stability.",
                    explanation="Versioning (e.g., /v1/ vs /v2/ or headers) ensures breaking changes do not break legacy clients. Standardized error envelopes provide consistent error codes, messages, and validation details so clients can handle failures gracefully.",
                    concept_aspect="API Versioning & Standardized Error Contracts",
                    ideal_answer="API versioning (via URI path prefixes like /v1/ or HTTP headers) enables introducing breaking changes without affecting existing client integrations. Pairing this with standardized error formats (e.g. consistent JSON keys with error code, message, and field errors) ensures clients can reliably parse and respond to errors programmatically.",
                    rubric_keywords=["versioning", "backwards compatibility", "breaking changes", "standardized error", "status code"],
                ),
            ]
        else:
            raise ValueError("No verified fallback quiz exists for this lesson. Restore the AI provider and retry; unrelated questions will not be substituted.")

        return ConceptQuiz(
            concept_name=concept_name,
            resource_url=None,
            questions=questions,
        )

    @staticmethod
    def _heuristic_adaptive_quiz(
        concept_name: str,
        previous_attempts: List[Any],
        mastered_concepts: Optional[List[str]] = None,
        resource_title: str = "",
        difficulty: str = "beginner",
    ) -> ConceptQuiz:
        """Deterministic heuristic adaptive quiz generator prioritizing missed concepts,

        Predict Output coding questions, and retention revision questions.
        """
        from cognitive_learning_agent.llm.quiz_scope import is_variables, variables_quiz
        if is_variables(concept_name):
            return variables_quiz(concept_name)
        c_lower = concept_name.lower()
        attempt_num = len(previous_attempts) + 1 if previous_attempts else 2

        # Extract weak aspects from past attempts
        missed = []
        for att in (previous_attempts or []):
            wa_list = att.weak_areas if hasattr(att, "weak_areas") else att.get("weak_areas", [])
            for wa in wa_list:
                if wa not in missed:
                    missed.append(wa)

        if any(re.search(r"\b" + re.escape(k) + r"\b", c_lower) for k in ["tree", "bst", "traversal", "binary tree", "dsa", "node", "avl"]):
            questions = [
                # 4 Targeted Questions (addressing previously missed concepts)
                QuizQuestion(
                    question_id=1,
                    question_type=QuestionType.MCQ,
                    question_text="In a Binary Search Tree (BST), which traversal order is required to process and print all node keys in descending (reverse sorted) order?",
                    options=[
                        "Reverse Inorder (Right Subtree -> Root -> Left Subtree)",
                        "Postorder (Left Subtree -> Right Subtree -> Root)",
                        "Preorder (Root -> Left Subtree -> Right Subtree)",
                        "Level-order traversal using a FIFO queue",
                    ],
                    correct_option_index=0,
                    explanation="Since standard Inorder visits Left -> Root -> Right (yielding ascending keys), reversing the direction to Right -> Root -> Left visits nodes in strictly descending sorted order.",
                    concept_aspect="Inorder Traversal & BST Sorted Invariant",
                    distractor_misconceptions={
                        1: "Confusing reverse inorder with postorder traversal",
                        2: "Assuming preorder traversal produces sorted output",
                        3: "Assuming level-order traversal is sorted",
                    },
                    is_revision=False,
                ),
                QuizQuestion(
                    question_id=2,
                    question_type=QuestionType.MCQ,
                    question_text="An AVL tree node has a Left Subtree of height 3 and a Right Subtree of height 1. What is its balance factor and what action must be taken?",
                    options=[
                        "Balance factor is +2; a tree rotation (LL or LR) is required to restore balance.",
                        "Balance factor is +1; the tree is currently balanced so no rotation is needed.",
                        "Balance factor is 0; nodes must be re-inserted from scratch.",
                        "Balance factor is +3; nodes must be converted into a red-black tree.",
                    ],
                    correct_option_index=0,
                    explanation="Balance factor = Height(Left) - Height(Right) = 3 - 1 = +2. Because |balance factor| > 1, the AVL invariant is violated and a rotation is mandatory.",
                    concept_aspect="AVL Tree Invariant & Balance Factor Calculation",
                    distractor_misconceptions={
                        1: "Incorrectly calculating balance factor or tolerating imbalance greater than 1",
                        2: "Believing tree balance factor is always 0",
                        3: "Confusing balance factor calculation with tree height",
                    },
                    is_revision=False,
                ),
                QuizQuestion(
                    question_id=3,
                    question_type=QuestionType.MCQ,
                    question_text="For any non-empty binary tree with N nodes, what is the exact number of null/None child references across all nodes?",
                    options=[
                        "N + 1 null references",
                        "N - 1 null references",
                        "2N null references",
                        "Log2(N) null references",
                    ],
                    correct_option_index=0,
                    explanation="Every binary tree node has 2 pointer fields, giving 2N total references. Exactly N - 1 edges connect the N nodes to parents, leaving 2N - (N - 1) = N + 1 null pointers.",
                    concept_aspect="Binary Tree Definition and Node Constraints",
                    distractor_misconceptions={
                        1: "Confusing null child pointers with the number of internal tree edges (N - 1)",
                        2: "Assuming all 2N pointers are null",
                        3: "Conflating pointer count with tree depth",
                    },
                    is_revision=False,
                ),
                QuizQuestion(
                    question_id=4,
                    question_type=QuestionType.MCQ,
                    question_text="When sequentially sorted keys [10, 20, 30, 40, 50] are inserted into an unbalanced BST, how does the tree structure behave and what is its search complexity?",
                    options=[
                        "It degenerates into a right-skewed linked chain with height 5 and worst-case search complexity O(n).",
                        "It automatically self-balances into height 3 with O(log n) search complexity.",
                        "It forms a complete binary tree with height 2 and O(1) search complexity.",
                        "It causes an unhandled recursion stack overflow error during insertion.",
                    ],
                    correct_option_index=0,
                    explanation="Inserting monotonically increasing keys into a standard BST always attaches each new node to the right child of the previous, degrading into a linear list of height N with O(n) search.",
                    concept_aspect="BST Search Complexity & Tree Degeneracy",
                    distractor_misconceptions={
                        1: "Assuming standard BSTs automatically balance themselves without AVL/Red-Black logic",
                        2: "Confusing tree height with log n guarantees of balanced trees",
                        3: "Assuming sequential inserts trigger runtime syntax errors",
                    },
                    is_revision=False,
                ),
                # 2 PREDICT OUTPUT Coding Questions
                QuizQuestion(
                    question_id=5,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the exact console output of the following Python code that constructs a Binary Search Tree and performs an Inorder traversal:",
                    code_snippet=(
                        "class Node:\n"
                        "    def __init__(self, key):\n"
                        "        self.val = key\n"
                        "        self.left = None\n"
                        "        self.right = None\n"
                        "\n"
                        "def insert(root, key):\n"
                        "    if root is None:\n"
                        "        return Node(key)\n"
                        "    if key < root.val:\n"
                        "        root.left = insert(root.left, key)\n"
                        "    else:\n"
                        "        root.right = insert(root.right, key)\n"
                        "    return root\n"
                        "\n"
                        "def inorder(root, out):\n"
                        "    if root:\n"
                        "        inorder(root.left, out)\n"
                        "        out.append(root.val)\n"
                        "        inorder(root.right, out)\n"
                        "\n"
                        "root = None\n"
                        "for k in [40, 20, 60, 10, 30]:\n"
                        "    root = insert(root, k)\n"
                        "\n"
                        "result = []\n"
                        "inorder(root, result)\n"
                        "print(result)"
                    ),
                    options=[
                        "[10, 20, 30, 40, 60]",
                        "[40, 20, 60, 10, 30]",
                        "[10, 30, 20, 60, 40]",
                        "[60, 40, 30, 20, 10]",
                    ],
                    correct_option_index=0,
                    explanation="An Inorder traversal (Left -> Root -> Right) on a valid BST always visits all inserted keys in strictly ascending sorted order: [10, 20, 30, 40, 60].",
                    concept_aspect="Predict Output: BST Construction & Inorder Traversal",
                    distractor_misconceptions={
                        1: "Confusing Inorder traversal output with original insertion sequence",
                        2: "Misordering left vs right child processing during recursion",
                        3: "Assuming Inorder prints in descending reverse order",
                    },
                    is_revision=False,
                ),
                QuizQuestion(
                    question_id=6,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the exact return value / output of the following recursive Python code measuring maximum tree depth (height):",
                    code_snippet=(
                        "class TreeNode:\n"
                        "    def __init__(self, val, left=None, right=None):\n"
                        "        self.val = val\n"
                        "        self.left = left\n"
                        "        self.right = right\n"
                        "\n"
                        "def max_depth(root):\n"
                        "    if not root:\n"
                        "        return 0\n"
                        "    return 1 + max(max_depth(root.left), max_depth(root.right))\n"
                        "\n"
                        "# Construct tree:\n"
                        "#       10\n"
                        "#      /  \\\n"
                        "#     5    15\n"
                        "#    /\n"
                        "#   2\n"
                        "tree = TreeNode(10,\n"
                        "    TreeNode(5, TreeNode(2)),\n"
                        "    TreeNode(15)\n"
                        ")\n"
                        "print(max_depth(tree))"
                    ),
                    options=[
                        "3",
                        "2",
                        "4",
                        "1",
                    ],
                    correct_option_index=0,
                    explanation="The longest path from root to any leaf node is 10 -> 5 -> 2, which consists of 3 nodes. Thus, max_depth returns 1 + max(2, 1) = 3.",
                    concept_aspect="Predict Output: Recursive Tree Depth Calculation",
                    distractor_misconceptions={
                        1: "Only counting the depth of the shallower subtree (15)",
                        2: "Counting total edge count plus extra offset",
                        3: "Assuming depth is measured only from root",
                    },
                    is_revision=False,
                ),
                # 2 Retention Revision Questions (Mastered Foundations)
                QuizQuestion(
                    question_id=7,
                    question_type=QuestionType.MCQ,
                    question_text="[Revision Retention] What is the primary operational trade-off between contiguous arrays and linked data structures when inserting at the beginning (index 0)?",
                    options=[
                        "O(1) pointer update in linked structures vs O(n) element shifting in contiguous arrays.",
                        "O(1) direct write in contiguous arrays vs O(n) traversal in linked structures.",
                        "Both take O(n log n) due to memory sorting overhead.",
                        "Neither allows insertions at index 0.",
                    ],
                    correct_option_index=0,
                    explanation="Inserting at index 0 of a linked structure only requires pointing the new node's next pointer to the current head (O(1)), whereas arrays require shifting all n subsequent elements one position right (O(n)).",
                    concept_aspect="Retention Review: Linear Data Structures & Pointer Overhead",
                    distractor_misconceptions={
                        1: "Assuming contiguous arrays allow constant-time front insertions",
                        2: "Confusing memory allocation with sorting operations",
                        3: "Believing linked structures do not permit front prepend",
                    },
                    is_revision=True,
                ),
                QuizQuestion(
                    question_id=8,
                    question_type=QuestionType.MCQ,
                    question_text="[Revision Retention] In any recursive algorithm, why is a well-defined base case strictly mandatory?",
                    options=[
                        "To terminate recursion and prevent unbounded call stack growth resulting in a RecursionError.",
                        "To allocate GPU registers for parallel threads.",
                        "To ensure the garbage collector deletes circular references.",
                        "To automatically convert recursive calls into hash maps.",
                    ],
                    correct_option_index=0,
                    explanation="A base case provides the stopping condition where recursion halts; without it, function frames continuously push onto the call stack until maximum recursion depth is exceeded.",
                    concept_aspect="Retention Review: Recursion Mechanics & Call Stack Management",
                    distractor_misconceptions={
                        1: "Confusing recursion call stack frames with GPU hardware execution",
                        2: "Confusing recursive base cases with garbage collection",
                        3: "Assuming recursion automatically creates dictionary lookups",
                    },
                    is_revision=True,
                ),
                # 2 Descriptive Questions
                QuizQuestion(
                    question_id=9,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain how self-balancing trees (such as AVL trees) use single and double rotations to correct height imbalance while preserving the BST ordering invariant.",
                    explanation="Explains Left (RR), Right (LL), Left-Right (LR), and Right-Left (RL) rotations, how child pointers are swapped, and why values remain sorted.",
                    concept_aspect="Tree Rotations & BST Invariant Preservation",
                    ideal_answer="When a node's balance factor exceeds +/-1, AVL trees perform rotations: single rotations (LL or RR) when the child is heavy in the same direction, and double rotations (LR or RL) when zigzag imbalance occurs. Rotations preserve the BST invariant because subtrees being shifted have values strictly between the rotated nodes, ensuring left < root < right holds throughout.",
                    rubric_keywords=["rotations", "single rotation", "double rotation", "balance factor", "preserve", "bst invariant", "subtrees"],
                    is_revision=False,
                ),
                QuizQuestion(
                    question_id=10,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Compare the search, insertion, and deletion time complexities between an unmanaged Binary Search Tree and a Balanced Binary Search Tree in both average and worst cases.",
                    explanation="Contrasts average O(log n) with worst-case O(n) for degenerate BSTs, while balanced trees guarantee O(log n) worst case.",
                    concept_aspect="Time Complexity Trade-offs: Degenerate vs Balanced Trees",
                    ideal_answer="In an unmanaged BST, operations average O(log n), but if keys are inserted in sorted order, the tree degenerates into a linear list with O(n) worst-case time complexity. In a balanced BST (like AVL or Red-Black), rotations keep the tree height strictly logarithmic (h = O(log n)), guaranteeing O(log n) time complexity for search, insertion, and deletion in all cases.",
                    rubric_keywords=["average case", "worst case", "o(log n)", "o(n)", "degenerate", "balanced", "guarantee"],
                    is_revision=False,
                ),
            ]
        elif any(re.search(r"\b" + re.escape(k) + r"\b", c_lower) for k in ["async", "concurren", "event loop", "await", "coroutine", "aiohttp"]):
            questions = [
                # 4 Targeted Questions
                QuizQuestion(
                    question_id=1,
                    question_type=QuestionType.MCQ,
                    question_text="When running multiple tasks concurrently in asyncio, what is the key behavioral difference between `asyncio.sleep(1)` and `time.sleep(1)`?",
                    options=[
                        "`asyncio.sleep` yields control back to the event loop allowing other tasks to run; `time.sleep` blocks the entire thread and freezes the loop.",
                        "`time.sleep` yields to other coroutines; `asyncio.sleep` spawns a background thread.",
                        "Both freeze the entire Python process identically.",
                        "`asyncio.sleep` can only be used inside C extensions.",
                    ],
                    correct_option_index=0,
                    explanation="`asyncio.sleep` is an asynchronous non-blocking coroutine that cooperatively releases the single thread back to the loop. `time.sleep` issues a blocking OS syscall that freezes the thread.",
                    concept_aspect="Non-blocking Sleep vs Thread Blocking",
                    distractor_misconceptions={
                        1: "Confusing synchronous sleep with cooperative yielding",
                        2: "Assuming asyncio coroutines spawn background threads",
                        3: "Assuming async sleep is restricted to C extensions",
                    },
                    is_revision=False,
                ),
                QuizQuestion(
                    question_id=2,
                    question_type=QuestionType.MCQ,
                    question_text="If one coroutine inside `asyncio.gather(task1, task2, return_exceptions=False)` raises an unhandled Exception, what happens to the remaining tasks?",
                    options=[
                        "`gather` immediately raises that exception, but sibling tasks continue running in the background until they complete or are explicitly cancelled.",
                        "All other tasks are automatically terminated and aborted instantaneously by the OS kernel.",
                        "The entire Python interpreter process exits with code 1.",
                        "The exception is silently ignored and swallowed.",
                    ],
                    correct_option_index=0,
                    explanation="In `asyncio.gather`, when `return_exceptions=False`, the first exception immediately propagates to the awaiter, but other already-scheduled tasks continue executing unless cancelled explicitly.",
                    concept_aspect="Exception Handling in Concurrent Workflows",
                    distractor_misconceptions={
                        1: "Believing gather automatically halts and cleans up all sibling tasks",
                        2: "Assuming exceptions exit the entire OS process",
                        3: "Assuming gather ignores errors",
                    },
                    is_revision=False,
                ),
                QuizQuestion(
                    question_id=3,
                    question_type=QuestionType.MCQ,
                    question_text="Why does wrapping a CPU-bound mathematical loop in `async def` fail to improve throughput on a multi-core CPU?",
                    options=[
                        "Python's asyncio runs on a single thread and GIL; CPU calculations do not yield via I/O and monopolize the event loop.",
                        "Asyncio restricts math operations to 8-bit integers.",
                        "CPU computations require TLS network certificates.",
                        "The Python compiler converts coroutines into slow bash scripts.",
                    ],
                    correct_option_index=0,
                    explanation="Coroutines achieve concurrency via cooperative multitasking during I/O waits. CPU-bound code does not await I/O, so it blocks the single-threaded loop unless offloaded to a ProcessPoolExecutor.",
                    concept_aspect="CPU-bound Work vs I/O Concurrency",
                    distractor_misconceptions={
                        1: "Believing async/await creates parallel OS threads across multi-core CPUs",
                        2: "Assuming async def restricts numeric bitwidth",
                        3: "Conflating async execution with shell scripts",
                    },
                    is_revision=False,
                ),
                QuizQuestion(
                    question_id=4,
                    question_type=QuestionType.MCQ,
                    question_text="How does an `asyncio.Semaphore(value=5)` regulate throughput in an asynchronous web scraper?",
                    options=[
                        "It acts as an atomic counter allowing at most 5 concurrent tasks to enter the protected block simultaneously.",
                        "It buffers 5 gigabytes of HTTP payloads in RAM.",
                        "It encrypts passwords across 5 database shards.",
                        "It restarts the Python process every 5 minutes.",
                    ],
                    correct_option_index=0,
                    explanation="A semaphore maintains internal counters; tasks acquire a ticket before performing I/O and release it when done, capping concurrent connections at 5 to prevent server rate limiting.",
                    concept_aspect="Concurrency Throttling with Semaphores",
                    distractor_misconceptions={
                        1: "Confusing concurrency rate limiters with memory buffers",
                        2: "Confusing semaphores with database sharding",
                        3: "Confusing synchronization with process supervisors",
                    },
                    is_revision=False,
                ),
                # 2 PREDICT OUTPUT Coding Questions
                QuizQuestion(
                    question_id=5,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the exact printed output sequence of the following asyncio Python program:",
                    code_snippet=(
                        "import asyncio\n"
                        "\n"
                        "async def task_a():\n"
                        "    print('A1', end=' ')\n"
                        "    await asyncio.sleep(0.04)\n"
                        "    print('A2', end=' ')\n"
                        "\n"
                        "async def task_b():\n"
                        "    print('B1', end=' ')\n"
                        "    await asyncio.sleep(0.01)\n"
                        "    print('B2', end=' ')\n"
                        "\n"
                        "async def main():\n"
                        "    await asyncio.gather(task_a(), task_b())\n"
                        "\n"
                        "asyncio.run(main())"
                    ),
                    options=[
                        "A1 B1 B2 A2",
                        "A1 A2 B1 B2",
                        "B1 B2 A1 A2",
                        "A1 B1 A2 B2",
                    ],
                    correct_option_index=0,
                    explanation="task_a starts and prints A1, then yields during its 0.04s sleep. task_b starts and prints B1, then sleeps for only 0.01s. task_b's timer expires first, printing B2. Finally, task_a's 0.04s sleep completes, printing A2. The output is A1 B1 B2 A2.",
                    concept_aspect="Predict Output: Event Loop Cooperative Scheduling Order",
                    distractor_misconceptions={
                        1: "Assuming coroutines execute sequentially in arguments order without interleaving",
                        2: "Assuming task_b runs entirely before task_a starts",
                        3: "Assuming sleep times are ignored by the scheduler",
                    },
                    is_revision=False,
                ),
                QuizQuestion(
                    question_id=6,
                    question_type=QuestionType.PREDICT_OUTPUT,
                    question_text="Predict the exact printed output of this asyncio script using `return_exceptions=True`:",
                    code_snippet=(
                        "import asyncio\n"
                        "\n"
                        "async def compute(x):\n"
                        "    if x == 0:\n"
                        "        raise ValueError('Zero not allowed')\n"
                        "    return 100 // x\n"
                        "\n"
                        "async def main():\n"
                        "    results = await asyncio.gather(\n"
                        "        compute(2),\n"
                        "        compute(0),\n"
                        "        compute(5),\n"
                        "        return_exceptions=True\n"
                        "    )\n"
                        "    print([r if not isinstance(r, Exception) else 'ERR' for r in results])\n"
                        "\n"
                        "asyncio.run(main())"
                    ),
                    options=[
                        "[50, 'ERR', 20]",
                        "[50, 20]",
                        "['ERR']",
                        "ValueError: Zero not allowed",
                    ],
                    correct_option_index=0,
                    explanation="With return_exceptions=True, the raised ValueError is returned as an element in the result list instead of crashing gather. The output list maps 100//2=50, the exception to 'ERR', and 100//5=20, giving [50, 'ERR', 20].",
                    concept_aspect="Predict Output: Asyncio Gather Exception Aggregation",
                    distractor_misconceptions={
                        1: "Assuming failed tasks are silently dropped from the result list",
                        2: "Assuming the first error crashes the program despite return_exceptions=True",
                        3: "Assuming return_exceptions returns only error objects",
                    },
                    is_revision=False,
                ),
                # 2 Retention Revision Questions
                QuizQuestion(
                    question_id=7,
                    question_type=QuestionType.MCQ,
                    question_text="[Revision Retention] What is an asynchronous generator in Python and what keyword is used to yield values from it?",
                    options=[
                        "A function defined with `async def` that uses the `yield` keyword to stream items asynchronously.",
                        "A function that returns a pre-computed array wrapped in a tuple.",
                        "A multithreaded daemon that writes bytes directly to disk.",
                        "A regular lambda expression with callback closures.",
                    ],
                    correct_option_index=0,
                    explanation="An asynchronous generator function contains both `async def` and `yield`, allowing consumers to iterate over elements using `async for` as items become available.",
                    concept_aspect="Retention Review: Asynchronous Generators & Iterators",
                    distractor_misconceptions={
                        1: "Confusing streaming async generators with eager batch arrays",
                        2: "Confusing generators with thread daemons",
                        3: "Confusing async generators with simple lambdas",
                    },
                    is_revision=True,
                ),
                QuizQuestion(
                    question_id=8,
                    question_type=QuestionType.MCQ,
                    question_text="[Revision Retention] What is the difference between concurrency and parallelism?",
                    options=[
                        "Concurrency is managing multiple tasks by interleaving during wait times; parallelism is executing computations simultaneously across multiple CPU cores.",
                        "Concurrency requires multiple physical CPUs; parallelism runs on a single core.",
                        "Concurrency is only for graphics processing; parallelism is for disk I/O.",
                        "There is no difference; they are exact synonyms.",
                    ],
                    correct_option_index=0,
                    explanation="Concurrency is about task structure (handling many tasks at once via interleaving), while parallelism is about physical execution (doing many computations simultaneously on multiple CPU cores).",
                    concept_aspect="Retention Review: Concurrency vs Parallelism",
                    distractor_misconceptions={
                        1: "Swapping definitions of concurrency and parallelism",
                        2: "Restricting concurrency to GPU hardware",
                        3: "Assuming both terms are identical",
                    },
                    is_revision=True,
                ),
                # 2 Descriptive Questions
                QuizQuestion(
                    question_id=9,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Explain the role of the OS selector (epoll, kqueue, or IOCP) in Python's asyncio event loop. How does non-blocking I/O prevent thread starvation?",
                    explanation="Explains selector registration, polling for socket read/write readiness, and resuming coroutines.",
                    concept_aspect="Event Loop Mechanics & OS Selector Polling",
                    ideal_answer="The event loop registers non-blocking socket file descriptors with the OS selector (epoll on Linux, kqueue on macOS, IOCP on Windows). When a coroutine awaits network I/O, it registers interest and pauses. The OS selector notifies the loop when the socket has incoming bytes ready, allowing the event loop to resume the paused task without wasting CPU cycles in busy-wait polling.",
                    rubric_keywords=["os selector", "epoll", "kqueue", "non-blocking", "event loop", "resume", "socket"],
                    is_revision=False,
                ),
                QuizQuestion(
                    question_id=10,
                    question_type=QuestionType.DESCRIPTIVE,
                    question_text="Discuss strategies for gracefully shutting down an asyncio application when a SIGINT or cancel signal is received, ensuring no tasks or network sessions are leaked.",
                    explanation="Details gathering outstanding tasks, calling task.cancel(), awaiting asyncio.gather(..., return_exceptions=True), and closing client sessions.",
                    concept_aspect="Graceful Cancellation & Resource Teardown",
                    ideal_answer="Upon receiving a shutdown signal, the application should fetch all pending tasks via asyncio.all_tasks(), issue cancel() on each, and await them using asyncio.gather(return_exceptions=True). Then, close any open client sessions (e.g. aiohttp ClientSession or database connection pools) using async context managers or explicit close() calls before stopping the loop.",
                    rubric_keywords=["graceful shutdown", "cancel", "all_tasks", "gather", "return_exceptions", "client session", "close"],
                    is_revision=False,
                ),
            ]
        else:
            raise ValueError("No verified fallback quiz exists for this lesson. Restore the AI provider and retry; unrelated questions will not be substituted.")

        return ConceptQuiz(
            concept_name=concept_name,
            resource_url=None,
            attempt_number=attempt_num,
            quiz_type="adaptive",
            questions=questions[:10],
        )



