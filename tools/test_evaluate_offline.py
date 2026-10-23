"""Verify evaluation reporting against real, disposable child processes."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import evaluate_offline as runner


class EvaluationRunnerTests(unittest.TestCase):
    def run_fixture(self, mode, source, timeout=5):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'tools').mkdir()
            name = 'test_fixture' if mode == 'unittest' else 'test_fixture.py'
            if source is not None:
                (root / 'test_fixture.py').write_text(source, encoding='utf-8')
            (root / 'tools/offline_suite.json').write_text(
                json.dumps({mode: [name]}), encoding='utf-8')
            with patch.object(runner, 'ROOT', root), patch('sys.argv', [
                    'evaluate_offline.py', '--timeout', str(timeout)]), \
                    contextlib.redirect_stdout(io.StringIO()):
                exit_code = runner.main()
            report = json.loads(next((root / 'data/evaluation').glob(
                '*/results.json')).read_text(encoding='utf-8'))
            return exit_code, report['cases'][0]

    def test_assertion_success_records_actual_count(self):
        code, case = self.run_fixture('unittest',
            'import unittest\nclass Example(unittest.TestCase):\n'
            '    def test_ok(self): self.assertEqual(2 + 2, 4)\n')
        self.assertEqual((code, case['status'], case['tests_run']), (0, 'pass', 1))

    def test_failed_assertion_cannot_be_reported_as_pass(self):
        code, case = self.run_fixture('unittest',
            'import unittest\nclass Example(unittest.TestCase):\n'
            '    def test_bad(self): self.fail("intentional fixture failure")\n')
        self.assertEqual((code, case['status'], case['failures']), (1, 'fail', 1))

    def test_empty_suite_is_failure(self):
        code, case = self.run_fixture('unittest', '# no tests\n')
        self.assertEqual((code, case['status'], case['tests_run']), (1, 'fail', 0))

    def test_nonzero_script_is_failure_and_not_counted_as_unit_test(self):
        code, case = self.run_fixture('script', 'raise SystemExit(3)\n')
        self.assertEqual((code, case['status'], case['tests_run']), (1, 'fail', None))

    def test_missing_file_is_failure(self):
        code, case = self.run_fixture('script', None)
        self.assertEqual((code, case['status']), (1, 'missing'))

    def test_timeout_is_failure(self):
        code, case = self.run_fixture('script', 'import time\ntime.sleep(5)\n', 0.2)
        self.assertEqual((code, case['status']), (1, 'timeout'))

    def test_external_tcp_is_blocked_before_connection(self):
        code, case = self.run_fixture('script',
            'import socket\nsocket.socket().connect(("203.0.113.1", 443))\n')
        self.assertEqual((code, case['status']), (1, 'fail'))


if __name__ == '__main__':
    unittest.main()
