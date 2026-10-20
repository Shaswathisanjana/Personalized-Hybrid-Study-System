'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { tasksForCourse, buildLearningPath } = require('../coding/roadmap.cjs');
const task = { id: 'revision:loops', topic: 'loops', title: 'Revise loops', status: 'pending', courseIds: [] };
const course = { courseId: 'python-a', topic: 'Python', curriculum: [
  { title: 'Variables', completed: true }, { title: 'Loops', completed: false }, { title: 'Functions', completed: false }
] };

test('coding revision becomes the next step without changing lesson progress or indices', () => {
  const before = JSON.stringify(course);
  const result = buildLearningPath(course, [task]);
  assert.deepEqual(result.learningPath.map(s => s.kind), ['lesson', 'coding_revision', 'lesson', 'lesson']);
  assert.equal(result.nextStep.id, task.id);
  assert.deepEqual(result.learningPath.filter(s => s.kind === 'lesson').map(s => s.lessonIndex), [0, 1, 2]);
  assert.equal(result.learningPath[0].completed, true);
  assert.equal(JSON.stringify(course), before);
});
test('resolved revision restores the original next lesson; completed courses can still need review', () => {
  assert.equal(buildLearningPath(course, [{ ...task, status: 'resolved' }]).nextStep.lessonIndex, 1);
  const completed = { ...course, curriculum: course.curriculum.map(l => ({ ...l, completed: true })) };
  assert.equal(buildLearningPath(completed, [task]).nextStep.id, task.id);
  assert.equal(buildLearningPath(completed, []).nextStep, null);
});
test('explicit course IDs win; independent practice matches related courses without leaking to unrelated courses', () => {
  const linked = { ...task, courseIds: ['python-a'] };
  assert.equal(tasksForCourse([linked], course).length, 1);
  assert.equal(tasksForCourse([linked], { ...course, courseId: 'python-b' }).length, 0);
  assert.equal(tasksForCourse([task], { topic: 'Data structures and algorithms' }).length, 1);
  assert.equal(tasksForCourse([task], { topic: 'Photography', curriculum: [{ title: 'Exposure' }] }).length, 0);
  assert.equal(tasksForCourse([task], { topic: 'Basics', curriculum: [{ title: 'For loops' }] }).length, 1);
});
test('students without a generated course still have an actionable coding revision path', () => {
  const result = buildLearningPath(undefined, [task]);
  assert.equal(result.learningPath.length, 1);
  assert.equal(result.nextStep.id, task.id);
});

// Real Express routes and reducer; in-memory model methods stand in for MongoDB.
// This verifies the wiring, not MongoDB persistence or index behavior.
test('sync → shared profile → course → dashboard preserves ownership, same-title course IDs and recovery', async t => {
  process.env.GEMINI_API_KEY = ''; process.env.CODING_AI_PROVIDER = 'none';
  const server = require('../server.js');
  const bank = require('../coding/public/data/questions.json');
  const attempts = [], profiles = new Map();
  const courses = [
    { ...structuredClone(course), userId: 'roadmap_test', quizScores: [], courseStatus: 'active', learningMode: 'course' },
    { ...structuredClone(course), courseId: 'python-b', userId: 'roadmap_test', quizScores: [], courseStatus: 'active', learningMode: 'course' },
    { courseId: 'photo', topic: 'Photography', userId: 'photo_test', quizScores: [], curriculum: [] }
  ];
  const originalCurriculum = JSON.stringify(courses[0].curriculum);
  const match = (item, filter) => Object.entries(filter).every(([key, value]) => item[key] === value);
  function query(read) {
    let sorting, count;
    const value = () => {
      let result = structuredClone(read());
      if (Array.isArray(result) && sorting) result.sort((a, b) => {
        for (const [key, direction] of Object.entries(sorting)) {
          if (a[key] > b[key]) return direction;
          if (a[key] < b[key]) return -direction;
        }
        return 0;
      });
      if (Array.isArray(result) && count !== undefined) result = result.slice(0, count);
      return result;
    };
    return { sort(s) { sorting = s; return this; }, limit(n) { count = n; return this; }, select() { return this; }, lean() { return Promise.resolve(value()); }, then(resolve, reject) { return Promise.resolve(value()).then(resolve, reject); } };
  }
  t.mock.method(server.coding.CodingAttempt, 'find', filter => query(() => attempts.filter(a => match(a, filter))));
  t.mock.method(server.coding.CodingAttempt, 'findOne', filter => query(() => attempts.find(a => match(a, filter)) || null));
  t.mock.method(server.coding.CodingAttempt, 'create', async item => {
    const stored = { ...structuredClone(item), acceptedAt: new Date(Date.UTC(2026, 9, 4, 0, 0, attempts.length)) };
    attempts.push(stored); return { toObject: () => structuredClone(stored) };
  });
  t.mock.method(server.LearnerProfile, 'findOne', filter => query(() => profiles.get(filter.userId) || null));
  t.mock.method(server.LearnerProfile, 'updateOne', async (filter, update) => { profiles.set(filter.userId, { userId: filter.userId, ...structuredClone(update.$set) }); });
  t.mock.method(server.LearningHistory, 'find', filter => query(() => courses.filter(c => match(c, filter))));
  t.mock.method(server.LearningHistory, 'exists', async filter => courses.some(c => match(c, filter)));
  t.mock.method(server.LearningHistory, 'updateOne', async (filter, update) => { Object.assign(courses.find(c => match(c, filter)), structuredClone(update.$set)); });
  t.mock.method(server.UserProgress, 'find', () => query(() => []));
  const http = await new Promise(resolve => { const listener = server.app.listen(0, '127.0.0.1', () => resolve(listener)); });
  t.after(() => new Promise(resolve => http.close(resolve)));
  const base = `http://127.0.0.1:${http.address().port}`;
  async function request(url, body) {
    const response = await fetch(base + url, { method: body ? 'POST' : 'GET', headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
    assert.equal(response.status, 200); return response.json();
  }
  const q = bank.questions[0];
  let sequence = 0;
  function report(passed, courseId = '') {
    sequence++;
    return { attemptId: `roadmap-attempt-${sequence}`, questionId: q.id, packVersion: bank.version, courseId,
      code: `# Report fixture ${sequence}`, createdAt: new Date(Date.UTC(2026, 9, 4, 0, 0, sequence)).toISOString(),
      raw: { syntax: { ok: true }, outcomes: q.tests.map(test => ({ ok: true, stdout: passed ? test.expected : 'wrong', stderr: '' })) } };
  }
  const sync = (userId, items) => request('/api/coding/sync', { userId, attempts: items });
  const dashboard = (userId = 'roadmap_test', courseId = 'python-a') => request(`/api/student/${userId}/dashboard?courseId=${courseId}`);
  const first = report(false);
  await sync('roadmap_test', [first, first]);
  assert.equal((await dashboard()).nextStep.kind, 'lesson', 'duplicate retries are not two independent mistakes');
  await sync('roadmap_test', [report(false)]);
  const failed = await dashboard();
  assert.equal(failed.nextStep.topic, 'loops');
  assert.equal(failed.codingRevisionTasks.length, 1);
  assert.equal(courses[0].codingRevisionTasks[0].status, 'pending');
  assert.equal(failed.courseProgress, 33);
  assert.equal((await dashboard('roadmap_test', 'python-b')).selectedCourseId, 'python-b', 'same-title courses remain addressable');
  assert.equal((await dashboard('someone_else', '')).nextStep, null, 'another student cannot see this profile');
  assert.equal((await sync('someone_else', [report(false, 'python-a')])).acknowledgements[0].status, 'rejected');
  await sync('roadmap_test', [report(true)]);
  assert.equal((await dashboard()).nextStep.kind, 'coding_revision');
  await sync('roadmap_test', [report(true)]);
  assert.equal((await dashboard()).nextStep.lessonIndex, 1);
  assert.equal(courses[0].codingRevisionTasks[0].status, 'resolved');
  assert.equal(JSON.stringify(courses[0].curriculum), originalCurriculum);
  await sync('photo_test', [report(false), report(false)]);
  const photo = await dashboard('photo_test', 'photo');
  assert.equal(photo.codingRevisionTasks.length, 0);
  assert.equal(photo.independentRevisionTasks[0].topic, 'loops');
  await sync('no_course', [report(false), report(false)]);
  assert.equal((await dashboard('no_course', '')).nextStep.topic, 'loops');
  // Rebuild previously accepted evidence after a repair, without asking for new runs.
  profiles.delete('roadmap_test');
  await sync('roadmap_test', []);
  assert.equal((await dashboard()).nextStep.lessonIndex, 1);
});
