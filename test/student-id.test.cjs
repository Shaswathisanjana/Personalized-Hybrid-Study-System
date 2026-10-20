'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Exercise the real client functions with an in-memory DOM and transport.
// No browser initialization, Python runtime, or MongoDB connection is needed.
function client() {
  const requests = [], elements = { userId: { value: '' }, status: { textContent: '' } };
  const code = fs.readFileSync(path.join(__dirname, '../coding/public/app.js'), 'utf8');
  const boot = "init().catch(error => status('Practice could not open: ' + error.message));";
  assert.equal(code.split(boot).length, 2);
  const context = vm.createContext({
    document: { getElementById: id => elements[id] }, location: { search: '' }, URLSearchParams,
    CodingCore: {}, PracticeDB: { attempts: async () => [], set: async () => {} },
    AbortSignal, localStorage: { setItem() {} },
    fetch: async (url, options) => {
      requests.push({ url, body: options.body ? JSON.parse(options.body) : undefined });
      return { ok: true, json: async () => ({ acknowledgements: [], attempts: [], courses: [], state: {} }) };
    }
  });
  vm.runInContext(code.replace(boot, ''), context);
  // These display functions are outside the validation/transport boundary.
  vm.runInContext('renderHistory = async () => {}; renderCourses = () => {};', context);
  return { requests, elements, run: expression => vm.runInContext(expression, context) };
}

test('sync before student initialization never sends an empty ID, including repeated calls', async () => {
  const c = client();
  await c.run('Promise.all([sync(), sync(), sync()])');
  assert.equal(c.requests.length, 0);
  assert.match(c.elements.status.textContent, /Load student/);
});
test('sync rejects invalid or non-string IDs locally and keeps the current identity', async () => {
  const c = client();
  c.run("activeUser = 'existing_student';");
  await c.run("Promise.all(['', 'Siri Priya', 'siri@example.com', 'x'.repeat(81), null, ['student_1'], {}].map(id => sync(id)))");
  assert.equal(c.requests.length, 0);
  assert.equal(c.run('activeUser'), 'existing_student');
});
test('valid IDs still reach sync and history unchanged, including a background sync for another loaded student', async () => {
  const c = client();
  c.run("activeUser = 'another_student';");
  await c.run("sync('Siri_Priya-7')");
  assert.equal(c.requests[0].url, '/api/coding/sync');
  assert.deepEqual(c.requests[0].body, { userId: 'Siri_Priya-7', attempts: [] });
  assert.equal(c.requests[1].url, '/api/coding/history?userId=Siri_Priya-7');
  assert.equal(c.run('activeUser'), 'another_student');
});
test('Run cannot create attempts without a loaded student or while a different ID is typed', async () => {
  const c = client();
  await c.run('run()');
  assert.match(c.elements.status.textContent, /Load student before running/);
  c.run("activeUser = 'student_1';");
  c.elements.userId.value = 'student_2';
  await c.run('run()');
  assert.match(c.elements.status.textContent, /Load student before running/);
  assert.equal(c.run('activeUser'), 'student_1');
  assert.equal(c.requests.length, 0);
});
