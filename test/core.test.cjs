const { test, before } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const Core = require('../coding/public/core.js');
const bank = require('../coding/public/data/questions.json');
const solutions = require('../coding/public/data/solutions.json');
const extras = require('../coding/private/extra-tests.json');
const { verifyWithJudge } = require('../coding/judge.cjs');
let python;
before(async () => {
  python = await require('pyodide').loadPyodide({ indexURL: path.dirname(require.resolve('pyodide/package.json')) });
  python.runPython(fs.readFileSync(path.join(__dirname, '../coding/public/harness.py'), 'utf8'));
});
function run(q, code) {
  python.globals.set('_input_json', JSON.stringify({ code, mode: q.mode, tests: q.tests.map(t => q.mode === 'function' ? { args: t.args } : { stdin: t.stdin }) }));
  const raw = JSON.parse(python.runPython('_json.dumps(execute(_json.loads(_input_json)), allow_nan=False)'));
  return { raw, result: Core.evaluate(q, raw) };
}
test('actual Python catches the missing colon with a source location', () => {
  const q = bank.questions[0]; const { result } = run(q, 'for i in range(1, 5)\n    print(i)');
  assert.equal(result.status, 'syntax_error'); assert.equal(result.error.type, 'SyntaxError'); assert.equal(result.error.line, 1); assert.match(result.error.message, /:/);
});
test('all authored solutions pass all public and server-only tests', () => {
  for (const q of bank.questions) {
    const full = { ...q, tests: [...q.tests, ...extras[q.id]] };
    const { result } = run(full, solutions[q.id].code);
    assert.equal(result.status, 'passed', q.id + ' ' + JSON.stringify(result)); assert.equal(result.passed, full.tests.length);
  }
});
test('valid alternative loop is accepted; range endpoint mistake is rejected', () => {
  const q = bank.questions[0];
  assert.equal(run(q, 'n=int(input())\ni=1\nwhile i<=n:\n print(i)\n i+=1').result.status, 'passed');
  assert.equal(run(q, 'n=int(input())\nfor i in range(1,n):\n print(i)').result.status, 'wrong_answer');
});
test('later-case failure cannot become an all-pass result', () => {
  const q = bank.questions.find(q => q.id === 'find-largest');
  const { result } = run(q, 'def solve(nums):\n return max(0, max(nums))');
  assert.equal(result.status, 'wrong_answer'); assert.equal(result.cases[2].status, 'failed'); assert.equal(result.passed, 3);
});
test('runtime errors, non-JSON values, missing solve, and excessive output are diagnosed', () => {
  const q = bank.questions.find(q => q.id === 'sum-array');
  for (const [code, type] of [['def solve(nums):\n return 1/0', 'ZeroDivisionError'], ['def solve(nums):\n return {1,2}', 'ResultEncodingError'], ['print(1)', 'MissingSolveError'], ['def solve(nums):\n print("x"*40000)', 'OutputLimitError']]) {
    const { result } = run(q, code); assert.equal(result.status, 'runtime_error'); assert.equal(result.error.type, type);
  }
});
test('exploration is unverified and JSON Boolean differs from numeric one', () => {
  const q = { ...bank.questions.find(q => q.id === 'palindrome'), tests: [{ args: ['a'] }] };
  assert.equal(run(q, 'def solve(text):\n return True').result.status, 'unverified');
  q.tests[0].expected = true;
  assert.equal(run(q, 'def solve(text):\n return 1').result.status, 'wrong_answer');
});
test('missing or empty judge reports never pass', async () => {
  const q = bank.questions[0]; assert.throws(() => Core.evaluate(q, { syntax: { ok: true }, outcomes: [] }), /Incomplete/);
  let call = 0;
  await assert.rejects(verifyWithJudge(q, 'print(1)', { JUDGE0_URL: 'http://judge.test' }, async () => ({ ok: true, json: async () => ++call === 1 ? { token: '1234567890-token' } : { status: { id: 3 }, stdout: '' } })), /empty/);
});
test('Judge0 uses submission polling and excludes expected answers from executed source', async () => {
  const q = bank.questions[0], raw = run(q, solutions[q.id].code).raw; let calls = 0;
  const returned = await verifyWithJudge(q, solutions[q.id].code, { JUDGE0_URL: 'http://judge.test/' }, async (url, init) => {
    calls++;
    if (calls === 1) { assert.match(url, /wait=false/); const body = JSON.parse(init.body); assert.equal(body.enable_network, false); return { ok: true, json: async () => ({ token: 'test-token-123456' }) }; }
    assert.match(url, /\/submissions\/test-token-123456\?/);
    return { ok: true, json: async () => ({ status: { id: 3 }, stdout: Buffer.from(JSON.stringify(raw)).toString('base64') }) };
  }); assert.deepEqual(returned, raw);
});
test('revision tasks deduplicate evidence and resolve after two distinct successful solutions', () => {
  const q = bank.questions[0];
  const a = (id, success, code = id) => ({ question: q, attemptId: id, code, courseId: 'course-a', createdAt: '2026-01-0' + id + 'T00:00:00Z', result: { status: success ? 'passed' : 'wrong_answer' } });
  const attempts = [a('1', false), a('2', false), a('3', false, '2')];
  let state = Core.project(attempts, bank.questions); assert.equal(state.concepts.loops.sampleCount, 2); assert.equal(state.revisionTasks.length, 1); assert.equal(state.revisionTasks[0].status, 'pending');
  state = Core.project([...attempts, a('4', true), a('5', true)], bank.questions); assert.equal(state.revisionTasks[0].status, 'resolved'); assert.ok(state.concepts.loops.masteryEstimate < 1);
});
test('a verified duplicate replaces local evidence without counting twice', () => {
  const question = bank.questions[0];
  const one = { question, attemptId: 'a', code: 'same code', createdAt: '2026-01-01', result: { status: 'passed' } };
  const two = { ...one, attemptId: 'b', createdAt: '2026-01-02', serverResult: { status: 'wrong_answer' } };
  const c = Core.project([one, two], bank.questions).concepts.loops;
  assert.equal(c.sampleCount, 1); assert.equal(c.provenance.server_verified, 1); assert.equal(c.evidence[0].success, false);
});
test('large integer outputs are not silently rounded into a passing result', () => {
  const q = { ...bank.questions[1], tests: [{ args: [[]], expected: '9007199254740993' }] };
  assert.equal(run(q, 'def solve(nums):\n return 9007199254740993').result.error.type, 'ResultEncodingError');
  assert.equal(run(q, 'def solve(nums):\n return str(9007199254740993)').result.status, 'passed');
});
