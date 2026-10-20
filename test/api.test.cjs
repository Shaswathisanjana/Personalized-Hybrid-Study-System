const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const mongoose = require('mongoose');
const { MongoMemoryServer } = require('mongodb-memory-server');
const bank = require('../coding/public/data/questions.json');
let mongo, http, base, server;
before(async () => {
  mongo = await MongoMemoryServer.create({ binary: { version: '7.0.14' } });
  process.env.MONGO_URI = mongo.getUri(); delete process.env.GEMINI_API_KEY; process.env.CODING_AI_PROVIDER = 'none';
  server = require('../server.js'); await server.connectDB();
  http = await new Promise(resolve => { const s = server.app.listen(0, '127.0.0.1', () => resolve(s)); });
  base = `http://127.0.0.1:${http.address().port}`;
  await server.LearningHistory.create({ userId: 'alice', courseId: 'course-a', topic: 'Python loops', curriculum: [{ title: 'Original lesson', order: 0, completed: true }] });
});
after(async () => { if (http) await new Promise(resolve => http.close(resolve)); await mongoose.disconnect(); if (mongo) await mongo.stop(); });
async function request(url, body) { const response = await fetch(base + url, { method: body ? 'POST' : 'GET', headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined }); return { status: response.status, body: await response.json() }; }
function attempt(id, code = 'n=int(input())\nprint(0)') {
  const q = bank.questions[0];
  return { attemptId: id, questionId: q.id, code, packVersion: bank.version, createdAt: new Date().toISOString(), courseId: 'course-a', raw: { syntax: { ok: true }, outcomes: q.tests.map(() => ({ ok: true, stdout: '0\n', stderr: '' })) } };
}
test('sync retries and concurrent identical submissions store one event', async () => {
  const a = attempt('first-attempt-0001');
  const results = await Promise.all([request('/api/coding/sync', { userId: 'alice', attempts: [a] }), request('/api/coding/sync', { userId: 'alice', attempts: [a] })]);
  assert.deepEqual(results.map(r => r.body.acknowledgements[0].status).sort(), ['duplicate', 'saved']);
  assert.equal(await server.coding.CodingAttempt.countDocuments({ userId: 'alice', attemptId: a.attemptId }), 1);
  const profile = await server.LearnerProfile.findOne({ userId: 'alice' }).lean(); assert.equal(profile.codingState.concepts.loops.sampleCount, 1);
});
test('changed payload with reused ID is rejected without overwriting', async () => {
  const response = await request('/api/coding/sync', { userId: 'alice', attempts: [attempt('first-attempt-0001', 'print(99)')] });
  assert.equal(response.body.acknowledgements[0].status, 'rejected'); assert.match(response.body.acknowledgements[0].error, /different content/);
});
test('a second distinct mistake persists an actionable course revision and preserves lesson progress', async () => {
  await request('/api/coding/sync', { userId: 'alice', attempts: [attempt('second-attempt-002', 'n=int(input())\nprint(-1)')] });
  const course = await server.LearningHistory.findOne({ userId: 'alice', courseId: 'course-a' }).lean();
  assert.equal(course.codingRevisionTasks.length, 1); assert.equal(course.codingRevisionTasks[0].status, 'pending'); assert.equal(course.curriculum[0].completed, true);
  const response = await request('/api/student/alice/dashboard?courseId=course-a'); assert.equal(response.body.codingRevisionTasks.length, 1);
});
test('student history is partitioned and a course owned by another student is rejected', async () => {
  const history = await request('/api/coding/history?userId=bob'); assert.equal(history.body.attempts.length, 0);
  const response = await request('/api/coding/sync', { userId: 'bob', attempts: [attempt('bob-attempt-00001')] }); assert.equal(response.body.acknowledgements[0].status, 'rejected');
});
test('reported scores cannot override evaluated test outputs; no-test exploration gives no mastery evidence', async () => {
  const a = { ...attempt('forged-score-0001'), passedTests: 999, result: { status: 'passed' }, courseId: '' };
  const response = await request('/api/coding/sync', { userId: 'carol', attempts: [a] }); assert.equal(response.status, 200);
  const history = (await request('/api/coding/history?userId=carol')).body; assert.equal(history.attempts[0].result.status, 'wrong_answer'); assert.equal(history.attempts[0].provenance, 'browser_reported');
  const custom = { ...attempt('custom-attempt-01'), courseId: '', questionId: 'custom:one', question: { id: 'custom:one', topic: 'arrays', title: 'Explore', description: '', mode: 'function', tests: [{ args: [] }] }, raw: { syntax: { ok: true }, outcomes: [{ ok: true, value: 3, stdout: '', stderr: '' }] } };
  const saved = await request('/api/coding/sync', { userId: 'carol', attempts: [custom] }); assert.equal(saved.body.acknowledgements[0].status, 'saved'); assert.equal(saved.body.state.concepts.arrays, undefined);
});
test('optional AI disabled is explicit; private tests are not publicly served', async () => {
  const answer = await request('/api/coding/explain', { userId: 'alice', attempt: attempt('explain-attempt-01') }); assert.equal(answer.body.available, false);
  const privateFile = await fetch(base + '/coding/private/extra-tests.json'); assert.equal(privateFile.status, 404);
  const legacy = await request('/api/coding/config'); assert.equal(legacy.body.aiProvider, 'none');
});
