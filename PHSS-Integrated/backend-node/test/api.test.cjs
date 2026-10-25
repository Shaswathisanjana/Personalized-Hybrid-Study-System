const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const { MongoMemoryServer } = require('mongodb-memory-server');
const bank = require('../coding/public/data/questions.json');
let mongo, http, base, server, aliceCookie, bobCookie;

async function rawRequest(url, body, cookie) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (cookie) headers.Cookie = cookie;
  const response = await fetch(base + url, {
    method: body === undefined ? 'GET' : 'POST',
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    redirect: 'manual'
  });
  const text = await response.text();
  let parsed; try { parsed = JSON.parse(text); } catch { parsed = text; }
  return { status: response.status, body: parsed, response };
}
async function createAccount(userId, name, email) {
  await server.AuthUser.create({ userId, name, email, passwordHash: await bcrypt.hash('test-password-123', 4), emailVerified: true });
  await server.Student.findOneAndUpdate({ userId }, { $setOnInsert: { userId, name, email } }, { upsert: true });
  const login = await rawRequest('/api/auth/login', { email, password: 'test-password-123' }, null);
  assert.equal(login.status, 200, JSON.stringify(login.body));
  const setCookie = login.response.headers.get('set-cookie');
  assert.ok(setCookie, 'login should set a session cookie');
  return setCookie.split(';')[0];
}

before(async () => {
  mongo = await MongoMemoryServer.create({ binary: { version: '7.0.14' } });
  process.env.MONGO_URI = mongo.getUri();
  process.env.NODE_ENV = 'test';
  process.env.SESSION_SECRET = 'test-secret-with-more-than-thirty-two-characters';
  process.env.APP_BASE_URL = 'http://127.0.0.1:3000';
  delete process.env.GEMINI_API_KEY; process.env.CODING_AI_PROVIDER = 'none';
  server = require('../server.js'); await server.connectDB();
  http = await new Promise(resolve => { const s = server.app.listen(0, '127.0.0.1', () => resolve(s)); });
  base = `http://127.0.0.1:${http.address().port}`;
  aliceCookie = await createAccount('alice', 'Alice Student', 'alice@example.com');
  bobCookie = await createAccount('bob', 'Bob Student', 'bob@example.com');
  await server.LearningHistory.create({ userId: 'alice', courseId: 'course-a', topic: 'Python loops', curriculum: [{ title: 'Original lesson', order: 0, completed: true }] });
});
after(async () => { if (http) await new Promise(resolve => http.close(resolve)); await server?.sessionStore?.close(); await mongoose.disconnect(); if (mongo) await mongo.stop(); });
async function request(url, body, cookie = aliceCookie) { return rawRequest(url, body, cookie); }
function attempt(id, code = 'n=int(input())\nprint(0)') {
  const q = bank.questions[0];
  return { attemptId: id, questionId: q.id, code, packVersion: bank.version, createdAt: new Date().toISOString(), courseId: 'course-a', raw: { syntax: { ok: true }, outcomes: q.tests.map(() => ({ ok: true, stdout: '0\n', stderr: '' })) } };
}

test('protected APIs reject requests without a login session', async () => {
  const response = await request('/api/coding/history?userId=alice', undefined, null);
  assert.equal(response.status, 401);
});
test('login session identity overrides a forged userId in the request', async () => {
  const response = await request('/api/coding/sync', { userId: 'bob', attempts: [attempt('first-attempt-0001')] });
  assert.equal(response.status, 200);
  assert.equal(await server.coding.CodingAttempt.countDocuments({ userId: 'alice', attemptId: 'first-attempt-0001' }), 1);
  assert.equal(await server.coding.CodingAttempt.countDocuments({ userId: 'bob', attemptId: 'first-attempt-0001' }), 0);
});
test('changed payload with reused ID is rejected without overwriting', async () => {
  const response = await request('/api/coding/sync', { userId: 'bob', attempts: [attempt('first-attempt-0001', 'print(99)')] });
  assert.equal(response.body.acknowledgements[0].status, 'rejected'); assert.match(response.body.acknowledgements[0].error, /different content/);
});
test('a second distinct mistake persists an actionable course revision and preserves lesson progress', async () => {
  await request('/api/coding/sync', { userId: 'not-alice', attempts: [attempt('second-attempt-002', 'n=int(input())\nprint(-1)')] });
  const course = await server.LearningHistory.findOne({ userId: 'alice', courseId: 'course-a' }).lean();
  assert.equal(course.codingRevisionTasks.length, 1); assert.equal(course.codingRevisionTasks[0].status, 'pending'); assert.equal(course.curriculum[0].completed, true);
  const response = await request('/api/student/not-alice/dashboard?courseId=course-a'); assert.equal(response.body.codingRevisionTasks.length, 1);
});
test('different authenticated accounts have isolated coding history', async () => {
  const aliceHistory = await request('/api/coding/history?userId=bob', undefined, aliceCookie);
  const bobHistory = await request('/api/coding/history?userId=alice', undefined, bobCookie);
  assert.ok(aliceHistory.body.attempts.some(a => a.userId === 'alice'));
  assert.equal(bobHistory.body.attempts.length, 0);
  const forgedDashboard = await request('/api/student/alice/dashboard', undefined, bobCookie);
  assert.equal(forgedDashboard.body.userId, 'bob');
});
test('reported scores cannot override evaluated test outputs; no-test exploration gives no mastery evidence', async () => {
  const a = { ...attempt('forged-score-0001'), passedTests: 999, result: { status: 'passed' }, courseId: '' };
  const response = await request('/api/coding/sync', { userId: 'carol', attempts: [a] }); assert.equal(response.status, 200);
  const history = (await request('/api/coding/history?userId=carol')).body; assert.equal(history.attempts[0].result.status, 'wrong_answer'); assert.equal(history.attempts[0].provenance, 'browser_reported');
  const custom = { ...attempt('custom-attempt-01'), courseId: '', questionId: 'custom:one', question: { id: 'custom:one', topic: 'arrays', title: 'Explore', description: '', mode: 'function', tests: [{ args: [] }] }, raw: { syntax: { ok: true }, outcomes: [{ ok: true, value: 3, stdout: '', stderr: '' }] } };
  const saved = await request('/api/coding/sync', { userId: 'carol', attempts: [custom] }); assert.equal(saved.body.acknowledgements[0].status, 'saved'); assert.equal(saved.body.state.concepts.arrays, undefined);
});
test('admin analytics are denied to ordinary students and private tests are not served', async () => {
  const analytics = await request('/api/admin/analytics'); assert.equal(analytics.status, 403);
  const privateFile = await fetch(base + '/coding/private/extra-tests.json', { headers: { Cookie: aliceCookie }, redirect: 'manual' }); assert.equal(privateFile.status, 404);
  const answer = await request('/api/coding/explain', { userId: 'bob', attempt: attempt('explain-attempt-01') }); assert.equal(answer.body.available, false);
  const config = await request('/api/coding/config'); assert.equal(config.body.aiProvider, 'none');
});
