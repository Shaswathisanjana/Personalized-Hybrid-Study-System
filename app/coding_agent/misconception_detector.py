import ast
from dataclasses import dataclass, field

from app.coding_agent.models import CodingTask
from app.coding_agent.static_analyzer import CodingStaticAnalyzer


@dataclass(frozen=True)
class PossibleMisconception:
    code: str
    concept_name: str
    explanation: str
    targeted_hint: str
    line_number: int | None = None


@dataclass
class MisconceptionAnalysis:
    syntax_valid: bool
    findings: list[PossibleMisconception] = field(default_factory=list)
    message: str = ""


class CodingMisconceptionDetector:
    """
    Detects selected possible coding mistakes using AST patterns.

    Findings are advisory, not proof of a student's cognitive
    misconception. This class never executes student code and
    never modifies CACM.
    """

    def __init__(self, static_analyzer=None):
        self.static_analyzer = (
            static_analyzer or CodingStaticAnalyzer()
        )

    def analyze(self, task: CodingTask, code: str):
        if not isinstance(task, CodingTask):
            raise TypeError("task must be a CodingTask.")

        if not isinstance(code, str):
            raise TypeError("code must be a string.")

        if not code.strip():
            return MisconceptionAnalysis(
                syntax_valid=True,
                message="No code entered yet.",
            )

        structural = self.static_analyzer.analyze(code)

        if not structural.syntax_valid:
            return MisconceptionAnalysis(
                syntax_valid=False,
                message=structural.syntax_error,
            )

        tree = ast.parse(code)
        findings = []

        if task.concept_name == "Recursion":
            findings.extend(self._check_recursion(tree))

        elif task.concept_name == "Prime Numbers":
            findings.extend(self._check_prime_numbers(tree))

        elif task.concept_name == "Arrays":
            findings.extend(self._check_arrays(tree))

        return MisconceptionAnalysis(
            syntax_valid=True,
            findings=findings,
            message=(
                f"{len(findings)} possible issue(s) identified."
                if findings
                else "No supported misconception pattern detected."
            ),
        )

    @staticmethod
    def _check_recursion(tree):
        findings = []

        for function in ast.walk(tree):
            if not isinstance(
                function,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue

            # Inspect this function's own statements, excluding
            # nested function definitions.
            nodes = []
            pending = list(function.body)

            while pending:
                node = pending.pop()

                if isinstance(
                    node,
                    (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda),
                ):
                    continue

                nodes.append(node)
                pending.extend(ast.iter_child_nodes(node))

            recursive_calls = [
                node for node in nodes
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == function.name
            ]

            if not recursive_calls:
                continue

            has_conditional = any(
                isinstance(node, (ast.If, ast.IfExp))
                for node in nodes
            )

            if not has_conditional:
                findings.append(
                    PossibleMisconception(
                        code="possible_missing_base_case",
                        concept_name="Recursion",
                        explanation=(
                            "A direct recursive call was found, but "
                            "no conditional stopping logic was visible."
                        ),
                        targeted_hint=(
                            "What is the smallest input whose result "
                            "you already know? Handle that input "
                            "before calling the function again."
                        ),
                        line_number=function.lineno,
                    )
                )

            if function.args.args:
                parameter = function.args.args[0].arg

                for call in recursive_calls:
                    if not call.args:
                        continue

                    first_arg = call.args[0]

                    if (
                        isinstance(first_arg, ast.Name)
                        and first_arg.id == parameter
                    ):
                        findings.append(
                            PossibleMisconception(
                                code="unchanged_recursive_argument",
                                concept_name="Recursion",
                                explanation=(
                                    "A direct recursive call passes "
                                    "the first parameter unchanged."
                                ),
                                targeted_hint=(
                                    "Check whether each recursive call "
                                    "moves the input toward the "
                                    "stopping condition."
                                ),
                                line_number=call.lineno,
                            )
                        )
                        break

        return findings

    @staticmethod
    def _check_prime_numbers(tree):
        findings = []

        for function in ast.walk(tree):
            if not isinstance(function, ast.FunctionDef):
                continue

            if not function.args.args:
                continue

            parameter = function.args.args[0].arg

            for node in ast.walk(function):
                if not isinstance(node, ast.If):
                    continue

                comparison = node.test

                if not (
                    isinstance(comparison, ast.Compare)
                    and len(comparison.ops) == 1
                    and isinstance(comparison.ops[0], ast.Eq)
                    and len(comparison.comparators) == 1
                ):
                    continue

                left = comparison.left
                right = comparison.comparators[0]

                checks_one = (
                    isinstance(left, ast.Name)
                    and left.id == parameter
                    and isinstance(right, ast.Constant)
                    and right.value == 1
                ) or (
                    isinstance(right, ast.Name)
                    and right.id == parameter
                    and isinstance(left, ast.Constant)
                    and left.value == 1
                )

                if not checks_one:
                    continue

                explicitly_returns_true = any(
                    isinstance(statement, ast.Return)
                    and isinstance(statement.value, ast.Constant)
                    and statement.value.value is True
                    for statement in node.body
                )

                if explicitly_returns_true:
                    findings.append(
                        PossibleMisconception(
                            code="one_marked_as_prime",
                            concept_name="Prime Numbers",
                            explanation=(
                                "The function explicitly returns "
                                "True when its input equals 1."
                            ),
                            targeted_hint=(
                                "A prime number must have exactly "
                                "two distinct positive divisors. "
                                "Does 1 satisfy that definition?"
                            ),
                            line_number=node.lineno,
                        )
                    )

        return findings

    @staticmethod
    def _check_arrays(tree):
        findings = []

        for function in ast.walk(tree):
            if not isinstance(function, ast.FunctionDef):
                continue

            for statement in ast.walk(function):
                if not isinstance(statement, ast.Assign):
                    continue

                if not (
                    isinstance(statement.value, ast.Constant)
                    and type(statement.value.value) is int
                    and statement.value.value == 0
                ):
                    continue

                target_names = [
                    target.id
                    for target in statement.targets
                    if isinstance(target, ast.Name)
                ]

                suspicious_names = {
                    "maximum",
                    "max_value",
                    "max_num",
                    "largest",
                    "current_max",
                    "max_so_far",
                    "maxi",
                    "mx",
                }

                if any(
                    name.lower() in suspicious_names
                    for name in target_names
                ):
                    findings.append(
                        PossibleMisconception(
                            code="zero_initialized_maximum",
                            concept_name="Arrays",
                            explanation=(
                                "A maximum-tracking variable is "
                                "initialized to zero. This may "
                                "produce incorrect results for "
                                "arrays containing only negative numbers."
                            ),
                            targeted_hint=(
                                "What happens when every array "
                                "element is negative? Consider "
                                "initializing the running maximum "
                                "using an actual array element."
                            ),
                            line_number=statement.lineno,
                        )
                    )

        return findings
