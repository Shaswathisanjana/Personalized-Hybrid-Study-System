import ast
from dataclasses import dataclass, field


@dataclass
class CodeReviewIssue:
    category: str
    severity: str
    message: str
    line_number: int | None = None
    suggestion: str = ""


@dataclass
class CodeReviewReport:
    syntax_valid: bool
    issues: list[CodeReviewIssue] = field(default_factory=list)
    function_names: list[str] = field(default_factory=list)
    has_recursion: bool = False
    has_loop: bool = False
    has_return: bool = False

    @property
    def issue_count(self) -> int:
        return len(self.issues)


class CodeReviewEngine:
    """
    Performs deterministic structural inspection of Python code.

    This module does not execute submitted code, call an LLM,
    or modify the student's cognitive state.
    """

    def review(self, code: str) -> CodeReviewReport:

        if not isinstance(code, str):
            raise TypeError("code must be a string.")

        if not code.strip():
            return CodeReviewReport(
                syntax_valid=False,
                issues=[
                    CodeReviewIssue(
                        category="empty_submission",
                        severity="error",
                        message="No Python code was submitted.",
                        suggestion="Enter your Python solution first.",
                    )
                ],
            )

        try:
            tree = ast.parse(code)

        except SyntaxError as exc:
            return CodeReviewReport(
                syntax_valid=False,
                issues=[
                    CodeReviewIssue(
                        category="syntax_error",
                        severity="error",
                        message=exc.msg,
                        line_number=exc.lineno,
                        suggestion=(
                            "Inspect the indicated line and nearby "
                            "lines for missing punctuation, incorrect "
                            "indentation, or incomplete expressions."
                        ),
                    )
                ],
            )

        function_nodes = [
            node
            for node in ast.walk(tree)
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            )
        ]

        function_names = [
            node.name
            for node in function_nodes
        ]

        has_loop = any(
            isinstance(node, (ast.For, ast.While, ast.AsyncFor))
            for node in ast.walk(tree)
        )

        has_return = any(
            isinstance(node, ast.Return)
            for node in ast.walk(tree)
        )

        has_recursion = any(
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == function.name
            for function in function_nodes
            for statement in function.body
            for call in ast.walk(statement)
        )

        return CodeReviewReport(
            syntax_valid=True,
            function_names=function_names,
            has_recursion=has_recursion,
            has_loop=has_loop,
            has_return=has_return,
        )
