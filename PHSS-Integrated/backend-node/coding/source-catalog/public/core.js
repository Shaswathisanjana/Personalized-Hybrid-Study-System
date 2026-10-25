(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CodingCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const TOPICS = ['loops', 'arrays', 'strings', 'binary_search', 'two_pointers', 'stacks', 'recursion', 'dynamic_programming', 'sliding_window', 'unclassified'];
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const normalizeOutput = s => String(s).replace(/\r\n/g, '\n').replace(/\n+$/, '');
  function safeNumbers(value) {
    if (typeof value === 'number' && (!Number.isFinite(value) || (Number.isInteger(value) && !Number.isSafeInteger(value)))) throw new Error('Use strings for integers larger than 2^53 - 1; JSON numbers would lose precision.');
    if (value && typeof value === 'object') Object.values(value).forEach(safeNumbers);
  }
  function equal(a, b) {
    if (typeof a !== typeof b || a === null || b === null) return a === b;
    if (Array.isArray(a) || Array.isArray(b)) return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((v, i) => equal(v, b[i]));
    if (typeof a === 'object') return Object.keys(a).length === Object.keys(b).length && Object.keys(a).every(k => has(b, k) && equal(a[k], b[k]));
    return a === b;
  }
  function validateQuestion(q, custom = false) {
    if (!q || typeof q !== 'object') throw new Error('Choose a question.');
    if (!['function', 'stdout'].includes(q.mode)) throw new Error('Choose function or standard input/output mode.');
    if (typeof q.id !== 'string' || q.id.length > 100 || !q.id) throw new Error('Invalid question ID.');
    if (!TOPICS.includes(q.topic)) throw new Error('Choose a supported topic, or unclassified.');
    if (typeof q.title !== 'string' || !q.title.trim() || q.title.length > 200) throw new Error('Title must contain 1–200 characters.');
    if (typeof q.description !== 'string' || q.description.length > 15000) throw new Error('Question text is limited to 15,000 characters.');
    if (!Array.isArray(q.tests) || q.tests.length > 20) throw new Error('Supply up to 20 tests as a JSON array.');
    for (const test of q.tests) {
      safeNumbers(test);
      if (!test || typeof test !== 'object' || Array.isArray(test)) throw new Error('Each test must be an object.');
      if (q.mode === 'function' && !Array.isArray(test.args)) throw new Error('Function tests need an args array, e.g. {"args":[[1,2]],"expected":3}.');
      if (q.mode === 'stdout' && typeof test.stdin !== 'string') throw new Error('Output tests need a stdin string.');
      if (q.mode === 'stdout' && has(test, 'expected') && typeof test.expected !== 'string') throw new Error('Expected standard output must be a string.');
      if (JSON.stringify(test).length > 16000) throw new Error('Each test is limited to 16,000 characters.');
    }
    if (q.validator && !['exact','two_sum'].includes(q.validator)) throw new Error('Unsupported validator.');
    if (custom && !q.id.startsWith('custom:')) throw new Error('Custom IDs must start with custom:.');
    return q;
  }
  function validAnswer(q, test, actual) {
    if (q.validator === 'two_sum') {
      const [nums, target] = test.args;
      return Array.isArray(actual) && actual.length === 2 && actual.every(i => Number.isInteger(i) && i >= 0 && i < nums.length) && actual[0] !== actual[1] && nums[actual[0]] + nums[actual[1]] === target;
    }
    return equal(actual, test.expected);
  }
  function evaluate(q, raw) {
    validateQuestion(q);
    if (!raw || typeof raw !== 'object') throw new Error('Missing execution report.');
    const total = q.tests.filter(t => has(t, 'expected')).length;
    const base = { status: 'engine_error', passed: 0, total, cases: [], error: null };
    if (['timeout', 'cancelled', 'engine_error'].includes(raw.interrupted)) return { ...base, status: raw.interrupted };
    if (!raw.syntax || typeof raw.syntax.ok !== 'boolean') throw new Error('Execution report has no syntax result.');
    if (!raw.syntax.ok) {
      if (!raw.syntax.error || typeof raw.syntax.error.type !== 'string') throw new Error('Missing Python syntax diagnostic.');
      return { ...base, status: 'syntax_error', error: raw.syntax.error };
    }
    const tests = q.tests.length ? q.tests : [q.mode === 'function' ? { args: [] } : { stdin: '' }];
    if (!Array.isArray(raw.outcomes) || raw.outcomes.length !== tests.length) throw new Error('Incomplete test results; this run cannot be graded.');
    const cases = tests.map((test, index) => {
      const actual = raw.outcomes[index];
      if (!actual || typeof actual.ok !== 'boolean' || typeof actual.stdout !== 'string' || typeof actual.stderr !== 'string') throw new Error('Invalid test result.');
      if (!actual.ok && (!actual.error || typeof actual.error.type !== 'string')) throw new Error('Missing runtime diagnostic.');
      const asserted = has(test, 'expected');
      if (actual.ok && q.mode === 'function' && !has(actual, 'value')) throw new Error('Function result is missing.');
      const matches = actual.ok && asserted && (q.mode === 'stdout' ? normalizeOutput(actual.stdout) === normalizeOutput(test.expected) : validAnswer(q, test, actual.value));
      return { index, asserted, status: !actual.ok ? 'runtime_error' : !asserted ? 'observed' : matches ? 'passed' : 'failed', actual, input: q.mode === 'function' ? test.args : test.stdin, ...(asserted ? { expected: test.expected } : {}) };
    });
    const passed = cases.filter(c => c.status === 'passed').length;
    const errorCase = cases.find(c => c.status === 'runtime_error');
    const status = errorCase ? 'runtime_error' : cases.some(c => c.status === 'failed') ? 'wrong_answer' : total === 0 ? 'unverified' : 'passed';
    return { ...base, status, passed, cases, error: errorCase?.actual.error || null };
  }
  function feedback(q, result) {
    const error = result.error;
    if (result.status === 'syntax_error' || result.status === 'runtime_error') {
      const location = error?.line ? ` at line ${error.line}` : '';
      const hints = {
        SyntaxError: 'Python could not parse the code. Inspect the indicated line and the line before it; use the interpreter message to identify the missing or unexpected token.',
        IndentationError: 'Align the statements in this block. Statements inside a loop, function, or condition must be indented.',
        TabError: 'Use spaces consistently; do not mix tabs and spaces for indentation.',
        NameError: 'Check that this name is defined before use and that its spelling matches.',
        TypeError: 'Check the types of the values passed to this operation or function.',
        IndexError: 'Compare the index with the collection length, including empty and last-element cases.',
        KeyError: 'Check whether the key exists before accessing the dictionary.',
        ZeroDivisionError: 'Check whether the divisor can be zero for this input.',
        RecursionError: 'Trace the base case and confirm that each recursive call moves toward it.',
        EOFError: 'The supplied input ended. Check the number of input() calls against the test input.',
        OutputLimitError: 'The output exceeded 32,000 characters. Inspect repeated printing and termination.',
        MissingSolveError: 'Define a top-level solve(...) function, or select standard input/output mode.',
        ResultEncodingError: 'Return JSON-compatible data: strings, finite numbers, booleans, lists, dictionaries, or None.'
      };
      return { title: `${error?.type || 'Python error'}${location}: ${error?.message || ''}`, hint: hints[error?.type] || 'Use the Python traceback and failing input to locate the operation that raised this error.' };
    }
    if (result.status === 'wrong_answer') return { title: `${result.passed}/${result.total} supplied tests passed.`, hint: 'Trace the first failing input and compare the actual result with the expected result. ' + (q.hint || 'Check the problem rules and boundary cases.') };
    if (result.status === 'passed') return { title: `All ${result.total} supplied tests passed.`, hint: 'This is evidence for these inputs. It does not prove correctness for every input or establish time complexity.' };
    if (result.status === 'timeout') return { title: 'Run stopped after the time limit.', hint: 'Inspect loop progress and recursive termination, or reduce unusually large test inputs. A timeout alone does not identify the cause.' };
    if (result.status === 'cancelled') return { title: 'You stopped this run.', hint: 'This run does not affect the learning estimate.' };
    if (result.status === 'unverified') return { title: 'Executed without an expected result.', hint: 'Add expected results to check correctness. Successful execution alone is not a correct solution.' };
    return { title: 'Python could not complete this run.', hint: 'Check the offline pack status and reload. Infrastructure failures do not affect the learning estimate.' };
  }
  function project(attempts, catalog) {
    const concepts = {}, revisionTasks = [], representatives = new Map();
    const sorted = [...attempts].sort((a, b) => String(a.acceptedAt || a.createdAt).localeCompare(String(b.acceptedAt || b.createdAt)) || String(a.attemptId).localeCompare(String(b.attemptId)));
    for (const a of sorted) {
      const q = a.question || catalog.find(q => q.id === a.questionId);
      const r = a.serverResult || a.result;
      if (!q?.tests?.some(t => has(t, 'expected'))) continue;
      if (!q || !r || !['passed', 'syntax_error', 'runtime_error', 'wrong_answer', 'timeout'].includes(r.status)) continue;
      const signature = JSON.stringify([q.id, q.tests, a.code]);
      const existing = representatives.get(signature);
      if (!existing || (!existing.serverResult && a.serverResult)) representatives.set(signature, a);
    }
    for (const a of sorted) {
      const q = a.question || catalog.find(q => q.id === a.questionId);
      if (!q || q.topic === 'unclassified' || !q.tests?.some(t => has(t,'expected'))) continue;
      const r = a.serverResult || a.result;
      if (!r || !['passed', 'syntax_error', 'runtime_error', 'wrong_answer', 'timeout'].includes(r.status)) continue;
      // Re-running the same unchanged solution/tests cannot inflate the estimate.
      const signature = JSON.stringify([q.id, q.tests, a.code]);
      if (representatives.get(signature) !== a) continue;
      const c = concepts[q.topic] ||= { topic: q.topic, evidence: [], provenance: { browser_reported: 0, server_verified: 0 } };
      c.evidence.push({ attemptId: a.attemptId, questionId: q.id, courseId: a.courseId || '', success: r.status === 'passed', kind: r.error?.type || r.status, provenance: a.serverResult ? 'server_verified' : 'browser_reported', at: a.acceptedAt || a.createdAt });
      c.evidence = c.evidence.slice(-20);
    }
    for (const c of Object.values(concepts)) {
      const successes = c.evidence.filter(e => e.success).length;
      c.sampleCount = c.evidence.length;
      c.masteryEstimate = Math.round(100 * (successes + 1) / (c.sampleCount + 2)) / 100;
      c.confidence = c.sampleCount < 5 ? 'low' : c.sampleCount < 12 ? 'moderate' : 'more evidence';
      c.distinctQuestions = new Set(c.evidence.map(e => e.questionId)).size;
      c.evidence.forEach(e => c.provenance[e.provenance]++);
      let failures = [], recovery = [], trigger = null, resolvedAt = null;
      for (const e of c.evidence) {
        if (!e.success) {
          failures.push(e); recovery = [];
          if (failures.length >= 2) { trigger = e; resolvedAt = null; }
        } else {
          recovery.push(e);
          if (recovery.length >= 2) { if (trigger) resolvedAt = e.at; failures = []; }
        }
      }
      if (trigger) {
        const practice = catalog.filter(q => q.topic === c.topic);
        revisionTasks.push({ id: `revision:${c.topic}`, topic: c.topic, title: `Revise ${c.topic.replace(/_/g, ' ')}`, reason: 'At least two distinct unsuccessful solutions were observed. The error category is evidence; it is not a diagnosis of a specific misconception.', instructions: practice[0]?.revision || 'Trace the failing input by hand, review the relevant concept, and retry with expected outputs.', questionIds: practice.map(q => q.id), courseIds: [...new Set(c.evidence.filter(e => !e.success).map(e => e.courseId).filter(Boolean))], status: resolvedAt ? 'resolved' : 'pending', openedAt: trigger.at, resolvedAt, evidenceIds: c.evidence.filter(e => !e.success).map(e => e.attemptId), recoveryRequired: 'Two distinct successful solution attempts after the last failure.' });
      }
    }
    return { version: 1, policy: 'A smoothed personal-practice estimate from at most 20 distinct solutions per topic; not a validated mastery measurement.', concepts, revisionTasks };
  }
  return { TOPICS, has, equal, normalizeOutput, validateQuestion, evaluate, feedback, project };
});
