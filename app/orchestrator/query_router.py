from dataclasses import dataclass, field
import json
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors


load_dotenv()


@dataclass
class QueryRoute:
    """
    Structured routing decision produced by the QueryRouter.
    """

    original_query: str
    concept: str

    intents: list[str] = field(
        default_factory=list
    )

    selected_agents: list[str] = field(
        default_factory=list
    )

    needs_cognitive_tracking: bool = False

    reason: str = ""


class QueryRouter:
    """
    Routes a natural-language student request to one or
    more specialized educational agents.

    Primary routing:
        Gemini semantic routing

    Backup routing:
        Deterministic local routing if Gemini is
        temporarily unavailable.

    Available agents:
        learning
        research
        coding

    CACM is not an agent. It is the shared cognitive
    layer that receives evidence from agent interactions.
    """

    VALID_AGENTS = {
        "learning",
        "research",
        "coding",
    }

    VALID_INTENTS = {
        "learn",
        "research",
        "code",
    }

    def __init__(
        self,
        model_name: str = "gemini-3.1-flash-lite-preview",
        max_retries: int = 2,
        retry_delay: float = 2.0,
    ):

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model_name = model_name

        self.max_retries = max(
            0,
            max_retries,
        )

        self.retry_delay = max(
            0.0,
            retry_delay,
        )

    # ==================================================
    # PUBLIC ROUTING METHOD
    # ==================================================

    def route(
        self,
        query: str,
    ) -> QueryRoute:
        """
        Analyze a student's natural-language request.

        Gemini is attempted first.

        Temporary Gemini server failures trigger a small
        number of retries.

        If Gemini is still unavailable, a deterministic
        local fallback router is used.
        """

        query = query.strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        prompt = self._build_prompt(
            query
        )

        # ----------------------------------------------
        # Gemini semantic routing
        # ----------------------------------------------

        for attempt in range(
            self.max_retries + 1
        ):

            try:

                response = (
                    self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                    )
                )

                text = (
                    response.text
                    if response.text
                    else ""
                ).strip()

                text = self._remove_markdown_fences(
                    text
                )

                data = json.loads(
                    text
                )

                return self._build_route(
                    original_query=query,
                    data=data,
                )

            # ------------------------------------------
            # Temporary Gemini/server-side problem
            # ------------------------------------------

            except errors.ServerError:

                if attempt < self.max_retries:

                    time.sleep(
                        self.retry_delay
                    )

                    continue

                print(
                    "Query Router: Gemini is temporarily "
                    "unavailable. Using local fallback."
                )

                return self._fallback_route(
                    query
                )

            # ------------------------------------------
            # Gemini returned malformed JSON
            # ------------------------------------------

            except json.JSONDecodeError:

                print(
                    "Query Router: Gemini returned invalid "
                    "JSON. Using local fallback."
                )

                return self._fallback_route(
                    query
                )

            # ------------------------------------------
            # Gemini response violates our schema
            # ------------------------------------------

            except ValueError:

                print(
                    "Query Router: Gemini routing response "
                    "failed validation. Using local fallback."
                )

                return self._fallback_route(
                    query
                )

            # ------------------------------------------
            # Client-side API errors
            #
            # Do NOT silently hide authentication,
            # configuration, or invalid-request errors.
            # ------------------------------------------

            except errors.ClientError as exc:

                raise RuntimeError(
                    "Gemini client error while routing "
                    "the query. Check API configuration."
                ) from exc

            except errors.APIError as exc:

                print(
                    "Query Router: Gemini API error. "
                    "Using local fallback."
                )

                return self._fallback_route(
                    query
                )

        # Defensive fallback.
        return self._fallback_route(
            query
        )

    # ==================================================
    # GEMINI PROMPT
    # ==================================================

    def _build_prompt(
        self,
        query: str,
    ) -> str:

        return f"""
You are the routing component of an educational
multi-agent system.

The system contains exactly THREE specialized agents:

1. learning

Used when the student wants:
- explanations
- teaching
- lessons
- conceptual understanding
- practice quizzes
- learning support

2. research

Used when the student wants:
- academic papers
- research literature
- literature review
- research-grounded synthesis
- evidence from academic sources
- research comprehension

3. coding

Used when the student wants:
- programming problems
- coding practice
- code evaluation
- debugging
- implementation exercises

A query may require ONE OR MORE agents.

Examples:

Query:
"Teach me recursion"

Result:
concept = "recursion"
intents = ["learn"]
selected_agents = ["learning"]

Query:
"Find research papers about federated learning
in healthcare"

Result:
concept = "federated learning in healthcare"
intents = ["research"]
selected_agents = ["research"]

Query:
"Give me a Python coding problem on binary search"

Result:
concept = "binary search"
intents = ["code"]
selected_agents = ["coding"]

Query:
"Teach me binary search and then give me a
coding problem"

Result:
concept = "binary search"
intents = ["learn", "code"]
selected_agents = ["learning", "coding"]

Query:
"Find papers about transformers and help me
understand them"

Result:
concept = "transformers"
intents = ["research", "learn"]
selected_agents = ["research", "learning"]

COGNITIVE TRACKING RULE:

needs_cognitive_tracking should be TRUE when the
requested interaction is likely to generate evidence
about the student's understanding or performance.

Examples include:
- quizzes
- comprehension questions
- coding submissions
- assessments
- learning activities where understanding is tested

Simply requesting information or papers does NOT by
itself prove anything about student mastery.

Therefore:

"Find papers on transformers"
-> needs_cognitive_tracking = false

"Find papers on transformers and test my understanding"
-> needs_cognitive_tracking = true

"Give me a coding problem"
-> needs_cognitive_tracking = true

"Teach me recursion"
-> true because this is an active learning interaction

STUDENT QUERY:

{query}

Return ONLY valid JSON.

Required structure:

{{
    "concept": "main academic concept",
    "intents": ["learn"],
    "selected_agents": ["learning"],
    "needs_cognitive_tracking": true,
    "reason": "short explanation of routing decision"
}}

Rules:

- Do not invent agents.
- selected_agents may contain only:
  learning, research, coding

- intents may contain only:
  learn, research, code

- Do not route every query to every agent.
- Choose only agents actually required.
- Preserve a specific topic when the user provides one.
- Do not replace a specific topic with a broader topic.
- Keep reason concise.
"""

    # ==================================================
    # LOCAL FALLBACK ROUTER
    # ==================================================

    def _fallback_route(
        self,
        query: str,
    ) -> QueryRoute:
        """
        Deterministic backup router.

        This is NOT intended to replace Gemini semantic
        routing.

        Its purpose is to keep the system operational
        during temporary external API failures.
        """

        lowered = query.lower()

        intents = []
        selected_agents = []

        # ----------------------------------------------
        # Research intent
        # ----------------------------------------------

        research_terms = [
            "research paper",
            "research papers",
            "paper on",
            "papers on",
            "paper about",
            "papers about",
            "academic paper",
            "academic papers",
            "literature review",
            "research literature",
            "journal article",
            "journal articles",
            "research about",
            "research on",
            "studies on",
            "studies about",
        ]

        if any(
            term in lowered
            for term in research_terms
        ):
            intents.append(
                "research"
            )

            selected_agents.append(
                "research"
            )

        # ----------------------------------------------
        # Coding intent
        # ----------------------------------------------

        coding_terms = [
            "coding problem",
            "coding question",
            "coding practice",
            "programming problem",
            "programming question",
            "write code",
            "write a program",
            "implement",
            "debug",
            "debugging",
            "code practice",
            "code challenge",
        ]

        if any(
            term in lowered
            for term in coding_terms
        ):
            intents.append(
                "code"
            )

            selected_agents.append(
                "coding"
            )

        # ----------------------------------------------
        # Learning intent
        # ----------------------------------------------

        learning_terms = [
            "teach me",
            "explain",
            "help me understand",
            "help me learn",
            "learn about",
            "learn ",
            "understand ",
            "from basics",
            "quiz me",
            "test my understanding",
            "practice quiz",
            "what is ",
            "what are ",
            "how does ",
            "how do ",
            "why does ",
            "why do ",
        ]

        if any(
            term in lowered
            for term in learning_terms
        ):
            intents.append(
                "learn"
            )

            selected_agents.append(
                "learning"
            )

        # ----------------------------------------------
        # If intent is ambiguous, default to Learning.
        #
        # This gives a sensible educational response
        # rather than sending the query to every agent.
        # ----------------------------------------------

        if not selected_agents:

            intents = [
                "learn"
            ]

            selected_agents = [
                "learning"
            ]

        # Remove duplicates while preserving order.

        intents = list(
            dict.fromkeys(
                intents
            )
        )

        selected_agents = list(
            dict.fromkeys(
                selected_agents
            )
        )

        concept = self._extract_fallback_concept(
            query=query,
        )

        # ----------------------------------------------
        # Cognitive tracking
        # ----------------------------------------------

        assessment_terms = [
            "quiz",
            "test my understanding",
            "test me",
            "assess",
            "assessment",
            "coding problem",
            "coding question",
            "coding practice",
            "programming problem",
            "code challenge",
            "debug",
            "implement",
        ]

        has_assessment = any(
            term in lowered
            for term in assessment_terms
        )

        has_learning = (
            "learning"
            in selected_agents
        )

        has_coding = (
            "coding"
            in selected_agents
        )

        needs_cognitive_tracking = (
            has_assessment
            or has_learning
            or has_coding
        )

        return QueryRoute(
            original_query=query,
            concept=concept,
            intents=intents,
            selected_agents=selected_agents,
            needs_cognitive_tracking=(
                needs_cognitive_tracking
            ),
            reason=(
                "Local fallback routing was used because "
                "semantic routing was temporarily "
                "unavailable."
            ),
        )

    # ==================================================
    # FALLBACK CONCEPT EXTRACTION
    # ==================================================

    @staticmethod
    def _extract_fallback_concept(
        query: str,
    ) -> str:
        """
        Best-effort concept extraction used only when
        Gemini semantic routing is unavailable.

        It removes common request phrases while trying
        to preserve the student's actual topic.
        """

        concept = query.strip()

        patterns = [
            r"^please\s+",
            r"^can you\s+",
            r"^could you\s+",
            r"^i want you to\s+",
            r"^i want to\s+",
            r"^teach me\s+",
            r"^explain\s+",
            r"^help me understand\s+",
            r"^help me learn\s+",
            r"^find research papers about\s+",
            r"^find research papers on\s+",
            r"^find papers about\s+",
            r"^find papers on\s+",
            r"^find academic papers about\s+",
            r"^find academic papers on\s+",
            r"^give me a python coding problem on\s+",
            r"^give me a coding problem on\s+",
            r"^give me a programming problem on\s+",
            r"^give me coding practice on\s+",
            r"^what is\s+",
            r"^what are\s+",
        ]

        for pattern in patterns:

            concept = re.sub(
                pattern,
                "",
                concept,
                flags=re.IGNORECASE,
            ).strip()

        # Remove some trailing request wording.

        trailing_patterns = [
            r"\s+from basics[.!?]*$",
            r"\s+in simple terms[.!?]*$",
            r"\s+simply[.!?]*$",
            r"[.!?]+$",
        ]

        for pattern in trailing_patterns:

            concept = re.sub(
                pattern,
                "",
                concept,
                flags=re.IGNORECASE,
            ).strip()

        if not concept:
            concept = query.strip()

        return concept

    # ==================================================
    # ROUTE VALIDATION
    # ==================================================

    def _build_route(
        self,
        original_query: str,
        data: dict,
    ) -> QueryRoute:
        """
        Validate Gemini's routing decision before the
        rest of the application is allowed to use it.
        """

        concept = str(
            data.get(
                "concept",
                "",
            )
        ).strip()

        if not concept:
            raise ValueError(
                "Router did not identify a concept."
            )

        raw_intents = data.get(
            "intents",
            [],
        )

        raw_agents = data.get(
            "selected_agents",
            [],
        )

        if not isinstance(
            raw_intents,
            list,
        ):
            raise ValueError(
                "Router intents must be a list."
            )

        if not isinstance(
            raw_agents,
            list,
        ):
            raise ValueError(
                "Router selected_agents must be a list."
            )

        intents = []

        for intent in raw_intents:

            normalized = str(
                intent
            ).strip().lower()

            if (
                normalized
                not in self.VALID_INTENTS
            ):
                raise ValueError(
                    "Router produced an invalid intent: "
                    + normalized
                )

            if normalized not in intents:
                intents.append(
                    normalized
                )

        selected_agents = []

        for agent in raw_agents:

            normalized = str(
                agent
            ).strip().lower()

            if (
                normalized
                not in self.VALID_AGENTS
            ):
                raise ValueError(
                    "Router produced an invalid agent: "
                    + normalized
                )

            if (
                normalized
                not in selected_agents
            ):
                selected_agents.append(
                    normalized
                )

        if not selected_agents:
            raise ValueError(
                "Router did not select an agent."
            )

        needs_cognitive_tracking = bool(
            data.get(
                "needs_cognitive_tracking",
                False,
            )
        )

        reason = str(
            data.get(
                "reason",
                "",
            )
        ).strip()

        return QueryRoute(
            original_query=original_query,
            concept=concept,
            intents=intents,
            selected_agents=selected_agents,
            needs_cognitive_tracking=(
                needs_cognitive_tracking
            ),
            reason=reason,
        )

    # ==================================================
    # RESPONSE CLEANUP
    # ==================================================

    @staticmethod
    def _remove_markdown_fences(
        text: str,
    ) -> str:
        """
        Remove accidental ```json ... ``` wrappers.
        """

        text = text.strip()

        if text.startswith("```"):

            lines = text.splitlines()

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            text = "\n".join(
                lines
            ).strip()

        return text