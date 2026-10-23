"""Check loopback Streamlit HTTP startup; does not open a browser or student DB."""
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]


def main():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, '-B', str(ROOT / 'run_phss.py'), '--port', str(port)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    opener = build_opener(ProxyHandler({}))
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                print('FAIL: Streamlit exited before becoming healthy. Run run_phss.py --check.')
                return 1
            try:
                with opener.open(f'http://127.0.0.1:{port}/_stcore/health', timeout=1) as response:
                    if response.status == 200 and response.read().strip() == b'ok':
                        print('PASS: loopback Streamlit HTTP health endpoint returned ok.')
                        print('This checks server startup, not browser behavior or live providers.')
                        return 0
            except (URLError, OSError):
                pass
            time.sleep(0.2)
        print('FAIL: Streamlit health endpoint did not become ready within 30 seconds.')
        return 1
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()


if __name__ == '__main__':
    raise SystemExit(main())
