(function (root) {
  'use strict';
  function runPython(question, code, onPhase = () => {}, options = {}) {
    const worker = new Worker(new URL('./worker.mjs', document.baseURI), { type: 'module' });
    let done = false, timer, settle;
    const promise = new Promise(resolve => { settle = resolve; });
    function finish(raw) {
      if (done) return;
      done = true; clearTimeout(timer); worker.terminate(); settle(raw);
    }
    onPhase('Loading Python…');
    timer = setTimeout(() => finish({ interrupted: 'engine_error', message: 'Python startup timed out. Check the offline pack.' }), options.startupMs || 60000);
    worker.onmessage = ({ data }) => {
      if (data.type === 'ready') {
        clearTimeout(timer); onPhase('Running tests…');
        // Startup does not consume the student code's execution budget.
        timer = setTimeout(() => finish({ interrupted: 'timeout' }), options.executionMs || 4000);
        const tests = question.tests.map(t => question.mode === 'function' ? { args: t.args } : { stdin: t.stdin });
        worker.postMessage({ type: 'run', payload: { code, mode: question.mode, tests } });
      } else if (data.type === 'result') finish(data.raw);
      else if (data.type === 'engine_error') finish({ interrupted: 'engine_error', message: data.message });
    };
    worker.onerror = event => { event.preventDefault(); finish({ interrupted: 'engine_error', message: event.message }); };
    worker.onmessageerror = () => finish({ interrupted: 'engine_error', message: 'The worker returned unreadable data.' });
    return { promise, cancel: () => finish({ interrupted: 'cancelled' }) };
  }
  root.PythonRunner = { runPython };
})(globalThis);
