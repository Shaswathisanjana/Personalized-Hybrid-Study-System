import ast
from dataclasses import dataclass, field


@dataclass
class StaticAnalysisResult:
    """
    Structural analysis of a student's Python code.

    This result does not decide overall correctness.
    It provides objective structural evidence that can
    later be combined with behavioral tests and semantic
    evaluation.
    """

    syntax_valid: bool

    function_names: list[str] = field(
        default_factory=list
    )

    has_recursion: bool = False
    has_loop: bool = False
    has_return: bool = False

    recursive_functions: list[str] = field(
        default_factory=list
    )

    syntax_error: str = ""


class CodingStaticAnalyzer:
    """
    Performs safe static analysis of Python code
    using the Abstract Syntax Tree (AST).

    IMPORTANT:
    Student code is parsed, not executed.
    """

    def analyze(
        self,
        code: str,
    ) -> StaticAnalysisResult:

        if not isinstance(code, str):
            raise TypeError(
                "code must be a string."
            )

        # --------------------------------------------------
        # 1. PARSE THE CODE
        # --------------------------------------------------

        try:
            tree = ast.parse(code)

        except SyntaxError as exc:
            return StaticAnalysisResult(
                syntax_valid=False,
                syntax_error=str(exc),
            )

        # --------------------------------------------------
        # 2. FIND ALL FUNCTION DEFINITIONS
        # --------------------------------------------------

        function_nodes = [
            node
            for node in ast.walk(tree)
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        ]

        function_names = [
            node.name
            for node in function_nodes
        ]

        # --------------------------------------------------
        # 3. CHECK FOR LOOPS
        # --------------------------------------------------

        has_loop = any(
            isinstance(
                node,
                (
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                ),
            )
            for node in ast.walk(tree)
        )

        # --------------------------------------------------
        # 4. CHECK FOR RETURN STATEMENTS
        # --------------------------------------------------

        has_return = any(
            isinstance(
                node,
                ast.Return,
            )
            for node in ast.walk(tree)
        )

        # --------------------------------------------------
        # 5. DETECT DIRECT RECURSION
        #
        # For each function:
        #
        # def factorial(n):
        #     ...
        #     factorial(n - 1)
        #
        # we look for a call to the same function name
        # inside its body.
        # --------------------------------------------------

        recursive_functions = []

        for function_node in function_nodes:

            function_name = (
                function_node.name
            )

            for node in ast.walk(
                function_node
            ):

                if not isinstance(
                    node,
                    ast.Call,
                ):
                    continue

                called_function = (
                    node.func
                )

                if (
                    isinstance(
                        called_function,
                        ast.Name,
                    )
                    and
                    called_function.id
                    == function_name
                ):
                    recursive_functions.append(
                        function_name
                    )

                    break

        # Remove duplicates while preserving order.
        recursive_functions = list(
            dict.fromkeys(
                recursive_functions
            )
        )

        has_recursion = bool(
            recursive_functions
        )

        # --------------------------------------------------
        # 6. RETURN STRUCTURAL EVIDENCE
        # --------------------------------------------------

        return StaticAnalysisResult(
            syntax_valid=True,
            function_names=function_names,
            has_recursion=has_recursion,
            has_loop=has_loop,
            has_return=has_return,
            recursive_functions=recursive_functions,
        )