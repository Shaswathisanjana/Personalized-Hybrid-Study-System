"""Real Chrome/Edge smoke check using isolated offline fixtures and localhost only.

Uses the existing browser and websockets dependency; installs nothing. Artifacts,
including its separate SQLite DB and disposable browser profile, stay in data/.
"""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
local = ROOT / ".venv/Lib/site-packages"
if local.is_dir():
    sys.path.append(str(local))


def serve_fixture():
    import runpy
    import socket
    from types import SimpleNamespace
    from app.persistence.sqlite_store import SQLiteStudentStore
    import app.persistence.streamlit_state as persistence
    import app.orchestrator.orchestrator_runtime as runtime
    import app.coding_agent.integrated_workflow as coding
    import app.research_agent.search_session as search
    from test_student_journey_streamlit import RoutedOfflineOrchestrator
    from app.orchestrator.query_router import QueryRoute
    from test_research_search_collection import PagedFixture, synthetic_paper
    import test_verified_coding_catalog as catalog
    class OfflineRuntime(RoutedOfflineOrchestrator):
        @staticmethod
        def route(query):
            agents = ["learning"] if "teach" in query.lower() else (["research"] if "research" in query.lower() else ["coding"])
            return QueryRoute(query, "Recursion", [], agents, True, "Browser offline fixture")
    persistence.SQLiteStudentStore = lambda path: SQLiteStudentStore(os.environ["PHSS_BROWSER_SMOKE_DATABASE"])
    runtime.OrchestratorRuntime = OfflineRuntime
    coding.CodingEvaluator = catalog.EvaluationGuardrailTests().evaluator
    search.AcademicPaperSearch = lambda: PagedFixture([[synthetic_paper(1)]])
    original = socket.socket.connect
    def local_connect(sock, address):
        if not isinstance(address, tuple) or address[0] not in ("127.0.0.1", "::1"):
            raise AssertionError("External connection blocked in browser fixture")
        return original(sock, address)
    socket.socket.connect = local_connect
    runpy.run_path(str(ROOT / "review_ui.py"), run_name="__main__")


async def smoke():
    import asyncio
    import base64
    from datetime import datetime, timezone
    import json
    import socket
    import subprocess
    import time
    import urllib.request
    from websockets.asyncio.client import connect
    from app.persistence.sqlite_store import SQLiteStudentStore
    from app.persistence.session_recovery import restore
    from test_persistence_streamlit import OfflineOrchestrator
    browser = next((p for p in (
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")) if p.is_file()), None)
    if browser is None:
        raise RuntimeError("No existing Chrome/Edge executable found; no installation attempted.")
    directory = ROOT / "data/browser_smoke" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory.mkdir(parents=True)
    database = directory / "fixture.sqlite3"
    store = SQLiteStudentStore(database)
    owner = store.create_profile("Browser fixture student")
    with socket.socket() as address:
        address.bind(("127.0.0.1", 0))
        port = address.getsockname()[1]
    url = f"http://127.0.0.1:{port}/?student={owner}"
    child_env = {**os.environ, "PHSS_BROWSER_SMOKE_DATABASE": str(database),
                 "GEMINI_API_KEY": "offline-browser-placeholder", "PYTHONDONTWRITEBYTECODE": "1"}
    server = chrome = ws = None
    passed = []
    sequence = 0
    async def command(method, params=None):
        nonlocal sequence
        sequence += 1
        await ws.send(json.dumps(dict(id=sequence, method=method, params=params or {})))
        while True:
            message = await asyncio.wait_for(ws.recv(), timeout=30)
            if message is None:
                raise RuntimeError("Browser debugging connection closed")
            result = json.loads(message)
            if result.get("id") == sequence:
                if "error" in result:
                    raise RuntimeError(str(result["error"]))
                return result.get("result", {})
    async def evaluate(expression):
        result = await command("Runtime.evaluate", dict(expression=expression, returnByValue=True, awaitPromise=True))
        if "exceptionDetails" in result:
            raise RuntimeError(str(result["exceptionDetails"]))
        return result.get("result", {}).get("value")
    async def wait_for(expression, label, seconds=45):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                if await evaluate("document.body && (" + expression + ")"):
                    passed.append(label)
                    return
            except RuntimeError as exc:
                if "execution context" not in str(exc).lower():
                    raise
            await asyncio.sleep(.25)
        raise AssertionError("Browser timeout: " + label)
    async def click(label):
        await wait_for("[...document.querySelectorAll('button')].some(b=>b.innerText.trim()==="
                       + json.dumps(label) + "&&!b.disabled)", "Button ready: " + label)
        found = await evaluate("(()=>{const b=[...document.querySelectorAll('button')].find(b=>b.innerText.trim()==="
                               + json.dumps(label) + ");if(b){b.click();return true;}return false;})()")
        if not found:
            raise AssertionError("Missing button: " + label)
    async def type_into(label, value):
        selector = 'input[aria-label="' + label + '"],textarea[aria-label="' + label + '"]'
        await wait_for("!!document.querySelector(" + json.dumps(selector) + ")", "Input ready: " + label)
        found = await evaluate("(()=>{const e=document.querySelector(" + json.dumps(selector)
                               + ");if(e){e.focus();e.select();return true;}return false;})()")
        if not found:
            raise AssertionError("Missing input: " + label)
        await command("Input.insertText", {"text": value})
        await evaluate("document.activeElement.blur()")
        await asyncio.sleep(.5)
    async def save_screenshot(name):
        content = {"landing.png": "What would you like help with today?", "learning.png": "Your lesson",
                   "coding.png": "Write your Python solution", "research.png": "Saved results: 1"}[name]
        await wait_for("document.body.innerText.includes(" + json.dumps(content) + ")", "Screenshot content ready: " + name)
        await wait_for("![...document.querySelectorAll('button')].some(b=>b.innerText.trim()==='Stop')",
                       "Screen settled: " + name)
        await asyncio.sleep(1)
        await evaluate("document.querySelector('section[data-testid=\"stMain\"]')?.scrollTo(0,0);window.scrollTo(0,0)")
        screenshot = await command("Page.captureScreenshot", {"format": "png"})
        (directory / name).write_bytes(base64.b64decode(screenshot["data"]))
    async def reload_page():
        previous = await evaluate("performance.timeOrigin")
        await command("Page.reload")
        await wait_for("performance.timeOrigin!==" + json.dumps(previous) + "&&document.readyState==='complete'",
                       "Reload committed a fresh document")
    try:
        with (directory / "server.log").open("w", encoding="utf-8") as server_log, \
                (directory / "browser.log").open("w", encoding="utf-8") as browser_log:
            bootstrap = "import sys,runpy;sys.path.append('.venv/Lib/site-packages');sys.argv=" + repr([
                "streamlit", "run", str(Path(__file__).resolve()), "--server.address=127.0.0.1",
                f"--server.port={port}", "--server.headless=true", "--browser.gatherUsageStats=false"]) + ";runpy.run_module('streamlit',run_name='__main__')"
            server = subprocess.Popen([sys.executable, "-B", "-c", bootstrap], cwd=ROOT,
                                      env=child_env, stdout=server_log, stderr=subprocess.STDOUT,
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            deadline = time.monotonic() + 30
            while True:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    if time.monotonic() > deadline:
                        raise RuntimeError("Streamlit fixture did not start")
                    await asyncio.sleep(.25)
            profile = directory / "browser_profile"
            chrome = subprocess.Popen([str(browser), "--headless=new", "--disable-gpu", "--no-first-run",
                "--no-default-browser-check", "--disable-background-networking", "--disable-sync",
                "--disable-component-update", "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1, EXCLUDE localhost",
                "--remote-debugging-port=0", f"--user-data-dir={profile}", url],
                stdout=browser_log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            active = profile / "DevToolsActivePort"
            deadline = time.monotonic() + 30
            while not active.is_file():
                if time.monotonic() > deadline:
                    raise RuntimeError("Browser debugging endpoint did not start")
                await asyncio.sleep(.25)
            debug_port = active.read_text().splitlines()[0]
            with urllib.request.urlopen(f"http://127.0.0.1:{debug_port}/json/list", timeout=5) as response:
                targets = json.load(response)
            target = next(t for t in targets if t["type"] == "page")
            ws = await connect(target["webSocketDebuggerUrl"], open_timeout=10, max_size=16777216)
            await command("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 1100, "deviceScaleFactor": 1, "mobile": False})
            await wait_for("document.body.innerText.includes('Personalized Study Assistant')", "Real browser rendered student landing")
            await wait_for("!!document.querySelector('input[aria-label=\"What would you like help with today?\"]')", "Unified landing input ready")
            await save_screenshot("landing.png")
            await type_into("What would you like help with today?", "Teach me recursion")
            await click("Start")
            await wait_for("document.body.innerText.includes('Personalized Explanation')&&document.body.innerText.includes('Start Adaptive Practice')", "Actual lesson and adaptive practice opened inline")
            await reload_page()
            await wait_for("document.body.innerText.includes('Personalized Explanation')", "Learning workflow recovered after refresh")
            await save_screenshot("learning.png")
            await type_into("What would you like help with today?", "Give me coding practice")
            await click("Start")
            await wait_for("document.body.innerText.includes('Load Coding Exercise')", "Coding workflow opened inline")
            await click("Load Coding Exercise")
            await wait_for("!!document.querySelector('textarea[aria-label=\"Python code\"]')", "Coding editor loaded")
            await save_screenshot("coding.png")
            await type_into("Python code", "def factorial(n):\n    return 1 if n == 0 else n * factorial(n-1)")
            await click("Submit & Evaluate")
            await wait_for("document.body.innerText.includes('Assessment Results')", "Original code assessment displayed")
            await reload_page()
            await wait_for("document.body.innerText.includes('Assessment Results')", "Browser refresh recovered assessment")
            restored = restore(store.load(owner)[1], owner, lambda engine: OfflineOrchestrator(engine))
            assert restored["student"].find_concept("Recursion").attempts == 1
            assert len(restored["orchestrator"].cognitive_engine.evidence_store.get_all_evidence()) == 1
            passed.append("SQLite has exactly one assessed attempt after reload")
            await type_into("What would you like help with today?", "Find research papers")
            await click("Start")
            await wait_for("document.body.innerText.includes('Search academic papers')", "Research workflow opened inline")
            await wait_for("document.body.innerText.includes('Saved results: 1')", "Actual browser search rendered offline provider result")
            await save_screenshot("research.png")
            (directory / "results.json").write_text(json.dumps(dict(status="pass", checks=passed,
                browser=str(browser), coverage="Isolated offline fixtures; no live provider quality claim"), indent=2), encoding="utf-8")
            print(f"PASS: {len(passed)} browser checks; artifacts: {directory.relative_to(ROOT)}")
    except Exception:
        if ws:
            try:
                (directory / "failure_page.txt").write_text(
                    str(await evaluate("location.href+'\\n'+document.body.innerText")), encoding="utf-8")
            except Exception:
                pass
        raise
    finally:
        if ws:
            try:
                await command("Browser.close")
            except Exception:
                pass
            await ws.close()
        for process in (chrome, server):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    if os.getenv("PHSS_BROWSER_SMOKE_DATABASE"):
        serve_fixture()
    else:
        import asyncio
        asyncio.run(smoke())
