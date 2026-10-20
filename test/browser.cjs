/* Real browser + disposable MongoDB integration test. No AI keys are required. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const { MongoMemoryServer } = require('mongodb-memory-server');
const mongoose = require('mongoose');
const fixtureMode = process.env.TEST_API_FIXTURE === '1';
(async () => {
  let mongo, http, browser;
  try {
    if (!fixtureMode) {
      mongo = await MongoMemoryServer.create({ binary: { version: '7.0.14' } });
      process.env.MONGO_URI = mongo.getUri();
    }
    process.env.GEMINI_API_KEY = '';
    process.env.YOUTUBE_API_KEY = '';
    process.env.CODING_AI_PROVIDER = 'none';
    const server = require('../server.js');
    if (!fixtureMode) {
      await server.connectDB();
      await server.LearningHistory.create({ userId: 'browser_student', courseId: 'course-browser', topic: 'Python and DSA', curriculum: [{ title: 'Python foundations', order: 0 }] });
    }
    http = await new Promise(resolve => { const s = server.app.listen(0, '127.0.0.1', () => resolve(s)); });
    const base = `http://127.0.0.1:${http.address().port}`;
    browser = await chromium.launch({ headless: true, ...(process.env.TEST_CHROMIUM_PATH ? { executablePath: process.env.TEST_CHROMIUM_PATH } : {}) });
    const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
    const page = await context.newPage(); const errors = [];
    const fixtureAttempts = new Map(); let fixtureOffline = false;
    let videoRequests = 0, videoMode = 'success';
    if (fixtureMode) {
      // A transport fixture tests browser queue behavior without claiming a real
      // MongoDB write. The separate api.test.cjs covers actual MongoDB integration.
      console.log('MODE: browser tests use a simulated API; MongoDB is not exercised.');
      const Core = require('../coding/public/core.js');
      const bank = require('../coding/public/data/questions.json');
      const { validateAttempt } = require('../coding/index.cjs');
      const { buildLearningPath } = require('../coding/roadmap.cjs');
      const courses = [{ courseId: 'course-browser', topic: 'Python and DSA', status: 'active', curriculum: [{ title: 'Python foundations', completed: false }], progress: 0, completedLessons: 0, totalLessons: 1 }];
      await page.route('https://www.youtube.com/**', route => route.abort('internetdisconnected'));
      await page.route('**/api/**', async route => {
        if (fixtureOffline) return route.abort('internetdisconnected');
        const url = new URL(route.request().url()), body = route.request().postDataJSON();
        const userId = body?.userId || url.searchParams.get('userId') || 'browser_student';
        const stored = () => [...fixtureAttempts.values()].filter(a => a.userId === userId);
        let response;
        if (url.pathname === '/api/youtube/search') {
          videoRequests++;
          assert.match(url.searchParams.get('q'), /Python/);
          assert.equal(url.searchParams.has('userId'), false);
          if (videoMode === 'missing-key') return route.continue();
          response = videoMode === 'empty' ? [] : [
            { videoId: 'dsaLoops001', title: 'Python loops: range and boundaries (test fixture)', channelTitle: 'Test fixture' },
            { videoId: 'dsaLoops002', title: 'Trace a while loop (test fixture)', channelTitle: 'Test fixture' },
            { videoId: 'dsaLoops003', title: 'Loop practice walkthrough (test fixture)', channelTitle: 'Test fixture' }
          ];
        }
        else if (url.pathname === '/api/coding/config') response = { aiProvider: 'none', serverVerification: false };
        else if (url.pathname === '/api/coding/sync') {
          const acknowledgements = body.attempts.map(a => {
            const valid = validateAttempt(a), key = `${userId}:${a.attemptId}`, duplicate = fixtureAttempts.has(key);
            if (!duplicate) fixtureAttempts.set(key, { ...valid, userId, acceptedAt: new Date().toISOString() });
            return { attemptId: a.attemptId, status: duplicate ? 'duplicate' : 'saved', acceptedAt: fixtureAttempts.get(key).acceptedAt };
          });
          response = { acknowledgements, state: Core.project(stored(), bank.questions) };
        } else if (url.pathname === '/api/coding/history') response = { attempts: stored(), state: Core.project(stored(), bank.questions), courses: userId === 'browser_student' ? courses : [] };
        else if (url.pathname.includes('/dashboard')) response = { courses, selectedCourseId: 'course-browser', curriculum: courses[0].curriculum, history: [], quizScores: [], currentTopic: 'Python and DSA', learningMode: 'course', courseStatus: 'active', currentLesson: 0, courseProgress: 0, ...buildLearningPath(courses[0], Core.project(stored(), bank.questions).revisionTasks) };
        else return route.fulfill({ status: 404, json: { error: 'No fixture for this API.' } });
        return route.fulfill({ status: 200, json: response });
      });
    }
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/coding/?userId=browser_student&courseId=course-browser');
    await page.waitForFunction(() => document.getElementById('course').value === 'course-browser');
    async function run(code, expected) {
      if (code !== null) await page.locator('#code').fill(code);
      await page.locator('#run').click();
      await page.waitForFunction(() => !document.getElementById('run').disabled, null, { timeout: 75000 });
      assert.match(await page.locator('#result').innerText(), expected);
    }
    await page.locator('#errorExample').click();
    await page.waitForFunction(() => document.getElementById('code').value.includes('range(1, n + 1)\n'));
    await run(null, /SyntaxError at line 2: expected ':'/);
    console.log('PASS: real browser Python catches missing colon.');
    if (fixtureMode) {
      assert.equal(await page.locator('#revisions .task').count(), 0);
      assert.equal(videoRequests, 0);
      await page.locator('#concepts').getByRole('button', { name: 'Find revision videos' }).click();
      await page.locator('#concepts .watch-revision').first().waitFor();
      assert.equal(await page.locator('#concepts .watch-revision').count(), 3);
      console.log('PASS: a single failure allows an explicit video request without automatically labelling the topic weak.');
    }
    await run('n=int(input())\nfor i in range(1,n):\n    print(i)', /supplied tests passed/);
    await page.waitForFunction(() => document.querySelector('#revisions .task'));
    if (fixtureMode) {
      await page.locator('#learningLink').click();
      await page.locator('#nextLearningStep').waitFor();
      assert.match(await page.locator('#nextLearningStep').innerText(), /Revise loops/);
      assert.deepEqual(await page.locator('#learningPath > *').evaluateAll(nodes => nodes.map(n => n.classList.contains('coding-revision-step') ? 'revision' : 'lesson')), ['revision', 'lesson']);
      assert.equal(await page.locator('#learningPath .lesson-row').getAttribute('data-lesson-index'), '0');
      await page.locator('.course-card').first().click();
      await page.locator('#nextLearningStep .coding-revision-step').waitFor();
      await page.locator('#codingButton').click();
      await page.waitForFunction(() => document.getElementById('course').value === 'course-browser');
      console.log('PASS: Coding → Learning path makes revision the next step; selecting the course retains revision and original lesson indices.');
      await page.locator('#revisions .watch-revision').first().waitFor();
      assert.equal(await page.locator('#revisions .watch-revision').count(), 3);
      assert.equal(videoRequests, 1);
      await page.locator('#sync').click();
      await page.waitForLoadState('networkidle');
      assert.equal(videoRequests, 1);
      const countBeforeLesson = await page.evaluate(async () => (await PracticeDB.attempts('browser_student')).length);
      const draftBeforeLesson = await page.locator('#code').inputValue();
      await page.locator('#revisions .watch-revision').first().click();
      await page.waitForURL(/#topic$/);
      await page.locator('#codingRevisionContext').waitFor();
      assert.equal(await page.locator('#workspaceTitle').innerText(), 'Review loops');
      assert.equal(await page.locator('#studentId').inputValue(), 'browser_student');
      await page.locator('#returnToCoding').click();
      await page.waitForURL('**/coding/**');
      await page.waitForFunction(() => document.getElementById('course').value === 'course-browser');
      assert.equal(await page.locator('#code').inputValue(), draftBeforeLesson);
      assert.equal(await page.evaluate(async () => (await PracticeDB.attempts('browser_student')).length), countBeforeLesson);
      await page.locator('#revisions .watch-revision').first().waitFor();
      assert.equal(videoRequests, 1);
      videoMode = 'missing-key';
      await page.locator('#revisions').getByRole('button', { name: 'Refresh videos' }).click();
      await page.waitForFunction(() => document.querySelector('#revisions .revision-videos').textContent.includes('YOUTUBE_API_KEY'));
      assert.equal(await page.locator('#run').isEnabled(), true);
      assert.equal(await page.locator('#revisions .watch-revision').count(), 3);
      videoMode = 'empty';
      await page.locator('#revisions').getByRole('button', { name: 'Refresh videos' }).click();
      await page.waitForFunction(() => document.querySelector('#revisions .revision-videos').textContent.includes('No matching videos'));
      assert.equal(await page.locator('#revisions .watch-revision').count(), 0);
      videoMode = 'success';
      await page.locator('#revisions').getByRole('button', { name: 'Refresh videos' }).click();
      await page.locator('#revisions .watch-revision').first().waitFor();
      await page.setViewportSize({ width: 390, height: 844 });
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.setViewportSize({ width: 1440, height: 1050 });
      console.log('PASS: repeated failures show cached topic videos; lesson handoff preserves student, course, and draft; missing keys and empty results are visible.');
    }
    const correct = 'n=int(input())\nfor i in range(1,n+1):\n    print(i)';
    await run(correct, /All 4 supplied tests passed/);
    await page.locator('#downloadPack').click();
    await page.waitForFunction(() => document.getElementById('packStatus').textContent.includes('Offline pack ready.'), null, { timeout: 180000 });
    console.log('PASS: complete app and runtime cached.');
    await page.evaluate(async () => { for (const key of await caches.keys()) if (key.startsWith('cacm-python-pack-')) { const cache = await caches.open(key); await cache.delete('/coding/harness.py'); } });
    await page.locator('#downloadPack').click();
    await page.waitForFunction(() => document.getElementById('packStatus').textContent.includes('Offline pack ready.'), null, { timeout: 30000 });
    console.log('PASS: missing cached asset is repaired.');
    fixtureOffline = true; await context.setOffline(true); await page.reload();
    await page.waitForFunction(() => document.getElementById('code').value.includes('n+1'));
    if (fixtureMode) {
      await page.waitForFunction(() => document.querySelector('#revisions .revision-videos')?.dataset.videoState === 'offline');
      assert.equal(await page.locator('#revisions .watch-revision').count(), 3);
      assert.equal(await page.locator('#revisions .watch-revision[href]').count(), 0);
      assert.match(await page.locator('#revisions').innerText(), /Connect to the internet to watch/);
      console.log('PASS: offline revision cards retain cached video titles and explain that playback needs internet.');
      await page.locator('#learningLink').click();
      assert.match(await page.locator('#status').innerText(), /Reconnect to sync/);
      assert.match(page.url(), /\/coding\//);
    }
    await run(correct + '\n# Offline retry', /All 4 supplied tests passed/);
    assert.equal(await page.locator('#revisions .task').count(), 0);
    assert.match(await page.locator('#connection').innerText(), /Offline/);
    console.log('PASS: offline reload, execution, and saved draft.');
    await run('while True:\n    pass', /Run stopped after the time limit/);
    await run(correct + '\n# After timeout', /All 4 supplied tests passed/);
    console.log('PASS: infinite loop stopped; a later run succeeds.');
    const localCount = await page.evaluate(async () => (await PracticeDB.attempts('browser_student')).length);
    assert.ok(localCount >= 6);
    await page.reload(); await page.waitForFunction(() => document.querySelectorAll('#history .attempt').length >= 6);
    fixtureOffline = false; await context.setOffline(false); await page.locator('#sync').click();
    await page.waitForFunction(async () => (await PracticeDB.attempts('browser_student')).every(a => a.synced), null, { timeout: 30000 });
    const countServer = async () => fixtureMode ? [...fixtureAttempts.values()].filter(a => a.userId === 'browser_student').length : server.coding.CodingAttempt.countDocuments({ userId: 'browser_student' });
    assert.equal(await countServer(), localCount);
    await page.locator('#sync').click();
    assert.equal(await countServer(), localCount);
    console.log('PASS: queued attempts sync once after reconnect.');
    if (fixtureMode) {
      await page.locator('#learningLink').click(); await page.locator('#nextLearningStep').waitFor();
      assert.match(await page.locator('#nextLearningStep').innerText(), /Python foundations/);
      assert.equal(await page.locator('#learningPath .coding-revision-step').count(), 0);
      await page.locator('#codingButton').click();
      await page.waitForFunction(() => document.getElementById('course').value === 'course-browser');
      console.log('PASS: synced successful retries remove resolved revision and restore the next course lesson.');
    }
    await page.locator('#source').selectOption('custom');
    await page.locator('#customTitle').fill('Sum from an external practice sheet');
    await page.locator('#customDescription').fill('Return the sum of the integers in nums.');
    await page.locator('#customTopic').selectOption('arrays');
    await page.locator('#customTests').fill('[{"args":[[1,2,3]],"expected":6},{"args":[[]],"expected":0}]');
    await run('def solve(nums):\n    return sum(nums)', /All 2 supplied tests passed/);
    if (fixtureMode) {
      const arrays = page.locator('#concepts .concept').filter({ has: page.getByText('arrays', { exact: true }) });
      await arrays.getByRole('button', { name: 'Find revision videos' }).click();
      await arrays.locator('.watch-revision').first().click(); await page.waitForURL(/#topic$/);
      await page.locator('#returnToCoding').click(); await page.waitForURL('**/coding/**');
      await page.waitForFunction(() => document.getElementById('customTitle').value === 'Sum from an external practice sheet');
      assert.equal(await page.locator('#source').inputValue(), 'custom');
      assert.equal(await page.locator('#customDescription').inputValue(), 'Return the sum of the integers in nums.');
      assert.match(await page.locator('#code').inputValue(), /return sum\(nums\)/);
      console.log('PASS: external-question video review returns to the custom question and its saved code.');
    }
    console.log('PASS: pasted question with caller-supplied tests.');
    await page.locator('#userId').fill('other_student'); await page.locator('#loadStudent').click();
    await page.waitForFunction(() => document.getElementById('history').textContent.includes('Your attempts will appear here.'));
    assert.equal(await page.locator('#history .attempt').count(), 0);
    console.log('PASS: local student histories are separate.');
    await page.locator('#userId').fill('browser_student'); await page.locator('#loadStudent').click();
    await page.waitForFunction(() => document.querySelectorAll('#history .attempt').length >= 7);
    await page.locator('#source').selectOption('bank');
    await page.locator('#question').selectOption('print-through-n');
    await run('for i in range(1, 5)\n    print(i)', /SyntaxError at line 1/);
    const out = path.join(__dirname, '../test-results'); fs.mkdirSync(out, { recursive: true });
    await page.screenshot({ path: path.join(out, 'practice-desktop.png'), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({ path: path.join(out, 'practice-mobile.png'), fullPage: true });
    await page.goto(base + '/');
    await page.locator('#studentId').fill('browser_student'); await page.locator('#dashboardButton').click();
    await page.waitForFunction(() => document.getElementById('dashboard').textContent.includes('Original lesson') || document.getElementById('dashboard').textContent.includes('Python foundations'));
    if (fixtureMode) {
      await page.getByRole('link', { name: 'Find topic videos' }).first().click();
      await page.locator('#codingRevisionContext').waitFor();
      await page.locator('#searchResults .video-card').first().waitFor();
      assert.match(await page.locator('#workspaceTitle').innerText(), /Review loops/);
      console.log('PASS: the Learning dashboard also opens video revision for coding difficulties.');
    }
    await page.locator('#codingButton').click(); await page.waitForURL('**/coding/**');
    assert.match(page.url(), /userId=browser_student/);
    assert.deepEqual(errors, []);
    console.log('PASS: existing dashboard and Coding practice navigation; no page script errors.');
  } finally {
    if (browser) await browser.close();
    if (http) await new Promise(resolve => http.close(resolve));
    await mongoose.disconnect(); if (mongo) await mongo.stop();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
