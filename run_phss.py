"""Launch PHSS on loopback using the current environment or existing packages."""
import argparse
import runpy
import sys

from tools.local_environment import ROOT, dependency_errors, prepare_imports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check imports without starting the app')
    parser.add_argument('--port', type=int, default=8501)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    prepare_imports()
    missing = dependency_errors()
    if missing:
        print('Cannot import required dependencies: ' + ', '.join(missing))
        print('See docs/SETUP.md. No packages were installed.')
        return 1
    if args.check:
        print('PHSS dependencies imported successfully. No providers called or student data opened.')
        return 0
    sys.argv = ['streamlit', 'run', str(ROOT / 'review_ui.py'),
                '--server.address=127.0.0.1', f'--server.port={args.port}',
                '--server.headless=true', '--browser.gatherUsageStats=false']
    runpy.run_module('streamlit', run_name='__main__')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
