"""Run the explicitly curated PHSS suite without external provider calls.

Uses only the standard library to launch tests. This is an accidental-network
guard for trusted tests, not isolation for hostile code. See docs/EVALUATION.md.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

BOOTSTRAP = r'''
import json, os, pathlib, runpy, socket, sys, unittest
root, mode, name, result_path = sys.argv[1:]
sys.path.insert(0, root)
local = pathlib.Path(root) / '.venv' / 'Lib' / 'site-packages'
if local.is_dir():
    sys.path.append(str(local))
os.environ['GEMINI_API_KEY'] = 'offline-evaluation-placeholder'
os.environ['YOUTUBE_API_KEY'] = 'offline-evaluation-placeholder'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
original = socket.socket.connect
def connect(sock, address):
    if not isinstance(address, tuple) or address[0] not in ('127.0.0.1', '::1'):
        raise AssertionError('External network blocked by offline evaluation')
    return original(sock, address)
socket.socket.connect = connect
original_ex = socket.socket.connect_ex
def connect_ex(sock, address):
    if not isinstance(address, tuple) or address[0] not in ('127.0.0.1', '::1'):
        raise AssertionError('External network blocked by offline evaluation')
    return original_ex(sock, address)
socket.socket.connect_ex = connect_ex
if mode == 'script':
    runpy.run_path(str(pathlib.Path(root) / name), run_name='__main__')
else:
    suite = unittest.defaultTestLoader.loadTestsFromName(name)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    metrics = dict(tests_run=result.testsRun, failures=len(result.failures),
                   errors=len(result.errors), skipped=len(result.skipped),
                   expected_failures=len(result.expectedFailures),
                   unexpected_successes=len(result.unexpectedSuccesses))
    pathlib.Path(result_path).write_text(json.dumps(metrics), encoding='utf-8')
    sys.exit(0 if result.wasSuccessful() and result.testsRun > 0 else 1)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='List cases without executing')
    parser.add_argument('--only', help='Run one exact case name from --list')
    parser.add_argument('--timeout', type=float, default=300, help='Seconds per case')
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    manifest = json.loads((ROOT / 'tools/offline_suite.json').read_text(encoding='utf-8'))
    cases = [(mode, name) for mode, names in manifest.items() for name in names]
    if args.only:
        cases = [(mode, name) for mode, name in cases if name == args.only]
        if not cases:
            parser.error('--only must match an explicit manifest entry')
    if args.list:
        for mode, name in cases:
            print(f'{mode}: {name}')
        return 0
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directory = ROOT / 'data/evaluation' / stamp
    directory.mkdir(parents=True)
    records = []
    started = time.perf_counter()
    for index, (mode, name) in enumerate(cases, 1):
        path = ROOT / (name + '.py' if mode == 'unittest' else name)
        metrics_path = directory / f'{index:03}.json'
        record = dict(mode=mode, name=name, status='missing', tests_run=None)
        before = time.perf_counter()
        if path.is_file():
            record['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            try:
                child = subprocess.run(
                    [sys.executable, '-B', '-X', 'utf8', '-c', BOOTSTRAP,
                     str(ROOT), mode, name, str(metrics_path)],
                    cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
                    errors='replace', timeout=args.timeout,
                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
                record.update(status='pass' if child.returncode == 0 else 'fail',
                              exit_code=child.returncode)
                log = child.stdout + child.stderr
                if metrics_path.exists():
                    record.update(json.loads(metrics_path.read_text(encoding='utf-8')))
                if mode == 'unittest' and not metrics_path.exists():
                    record['status'] = 'fail'
            except subprocess.TimeoutExpired:
                record['status'] = 'timeout'
                log = 'Case exceeded timeout; no passing result recorded.\n'
        else:
            log = 'Selected file is missing.\n'
        record['seconds'] = round(time.perf_counter() - before, 3)
        record['log'] = f'{index:03}.log'
        (directory / record['log']).write_text(log, encoding='utf-8')
        records.append(record)
        print(f"{index}/{len(cases)} {record['status'].upper()} {name}", flush=True)
    selected = {name if mode == 'script' else name + '.py' for mode, name in cases}
    inventory = [dict(file=p.name, selected=p.name in selected,
                      status='see_cases' if p.name in selected else 'not_run')
                 for p in sorted(ROOT.glob('test_*.py'))]
    report = dict(created_utc=stamp, python=sys.version, executable=sys.executable,
                  platform=sys.platform, scope='selected' if args.only else 'curated_full',
                  elapsed_seconds=round(time.perf_counter() - started, 3),
                  manifest_sha256=hashlib.sha256((ROOT / 'tools/offline_suite.json').read_bytes()).hexdigest(),
                  cases=records, root_test_inventory=inventory)
    (directory / 'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    passed = sum(r['status'] == 'pass' for r in records)
    count = sum(r.get('tests_run') or 0 for r in records)
    skipped = sum(r.get('skipped', 0) for r in records)
    lines = ['# PHSS offline evaluation', '',
             f"UTC: {stamp}; scope: {report['scope']}", '',
             f'{passed}/{len(records)} cases passed; {count} unittest executions; {skipped} skipped.',
             '', 'A script pass means successful process exit; scripts are not counted as unit tests.',
             'Synthetic fixtures verify software behavior, not real-student educational improvement.', '',
             '| Mode | Case | Status | Tests run | Seconds |', '| --- | --- | --- | ---: | ---: |']
    lines += [f"| {r['mode']} | {r['name']} | {r['status']} | {r.get('tests_run')} | {r['seconds']} |" for r in records]
    lines += ['', 'Other root test files are explicitly not run; see results.json inventory.']
    (directory / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{passed}/{len(records)} cases passed; {count} unittest executions; {skipped} skipped.')
    print(f'Results: {directory.relative_to(ROOT)}')
    return int(passed != len(records))


if __name__ == '__main__':
    raise SystemExit(main())
