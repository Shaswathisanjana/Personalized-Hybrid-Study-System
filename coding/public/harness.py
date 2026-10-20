"""Execute one student's Python solution. Expected answers stay outside this harness.

The browser runs this in a disposable worker. Server verification uses Judge0's
sandbox; never run this on the Express host with subprocess/exec.
"""
import builtins as _builtins
import contextlib as _contextlib
import copy as _copy
import io as _io
import json as _json
import sys as _sys
import traceback as _traceback

class OutputLimitError(Exception):
    pass

class MissingSolveError(Exception):
    pass

class ResultEncodingError(Exception):
    pass

def _safe_numbers(value):
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) > 9007199254740991:
        raise ResultEncodingError('Return integers larger than 2^53 - 1 as strings to preserve precision')
    if isinstance(value, (list, tuple)):
        for item in value:
            _safe_numbers(item)
    elif isinstance(value, dict):
        for item in value.values():
            _safe_numbers(item)

class _LimitedOutput(_io.StringIO):
    def write(self, text):
        if self.tell() + len(text) > 32000:
            raise OutputLimitError('Output exceeded 32,000 characters')
        return super().write(text)

def _error(exc):
    frames = _traceback.extract_tb(exc.__traceback__)
    student_frames = [f for f in frames if f.filename == '<student>']
    return {
        'type': type(exc).__name__,
        'message': str(exc)[:2000],
        'line': getattr(exc, 'lineno', None) or (student_frames[-1].lineno if student_frames else None),
        'offset': getattr(exc, 'offset', None),
        'text': getattr(exc, 'text', None),
        'traceback': ''.join(_traceback.format_exception(type(exc), exc, exc.__traceback__))[-6000:]
    }

def execute(payload):
    source = payload['code']
    mode = payload['mode']
    tests = payload.get('tests') or ([{'args': []}] if mode == 'function' else [{'stdin': ''}])
    try:
        compiled = compile(source, '<student>', 'exec')
    except (SyntaxError, ValueError, OverflowError) as exc:
        return {'syntax': {'ok': False, 'error': _error(exc)}, 'outcomes': []}
    outcomes = []
    for test in tests:
        stdout, stderr = _LimitedOutput(), _LimitedOutput()
        original_stdin = _sys.stdin
        outcome = {'ok': False, 'stdout': '', 'stderr': ''}
        scope = {'__name__': '__main__', '__builtins__': dict(vars(_builtins))}
        try:
            _sys.stdin = _io.StringIO(test.get('stdin', ''))
            with _contextlib.redirect_stdout(stdout), _contextlib.redirect_stderr(stderr):
                exec(compiled, scope, scope)
                if mode == 'function':
                    solve = scope.get('solve')
                    if not callable(solve):
                        raise MissingSolveError('Expected a top-level solve(...) function')
                    value = solve(*_copy.deepcopy(test.get('args', [])))
                    _safe_numbers(value)
                    try:
                        serialized = _json.dumps(value, allow_nan=False)
                        if len(serialized) > 32000:
                            raise ValueError('Returned result exceeded 32,000 characters')
                        outcome['value'] = _json.loads(serialized)
                    except (TypeError, ValueError, OverflowError) as exc:
                        raise ResultEncodingError(str(exc)) from exc
                outcome['ok'] = True
        except BaseException as exc:
            outcome['error'] = _error(exc)
        finally:
            _sys.stdin = original_stdin
            outcome['stdout'], outcome['stderr'] = stdout.getvalue(), stderr.getvalue()
        outcomes.append(outcome)
    return {'syntax': {'ok': True}, 'outcomes': outcomes}
