/* Real-browser navigation checks. Success responses for learning/history are
   fixtures; missing-key API responses are tested against the actual server.
   No live Gemini, YouTube, or MongoDB service is exercised by this test. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
// Empty values also prevent server.js's dotenv loader from restoring real keys.
process.env.GEMINI_API_KEY = '';
process.env.YOUTUBE_API_KEY = '';
process.env.CODING_AI_PROVIDER = 'none';
const { app } = require('../server.js');

(async () => {
  let http, browser;
  try {
    http = await new Promise((resolve, reject) => {
      const server = app.listen(0, '127.0.0.1', () => resolve(server));
      server.on('error', reject);
    });
    const base = `http://127.0.0.1:${http.address().port}`;
    for (const endpoint of ['recommend', 'quiz']) {
      const response = await fetch(`${base}/api/agent/${endpoint}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: 'navigation_student', topic: 'Python' })
      });
      assert.equal(response.status, 503);
      assert.match((await response.json()).error, /GEMINI_API_KEY/);
    }
    const youtube = await fetch(base + '/api/youtube/search?q=Python');
    assert.equal(youtube.status, 503);
    assert.match((await youtube.json()).error, /YOUTUBE_API_KEY/);
    console.log('PASS: missing learning keys return actionable errors without querying MongoDB.');

    browser = await chromium.launch({ headless: true, ...(process.env.TEST_CHROMIUM_PATH ? { executablePath: process.env.TEST_CHROMIUM_PATH } : {}) });
    const context = await browser.newContext({ viewport: { width: 1440, height: 1080 } });
    const page = await context.newPage();
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    let youtubeRequests = 0, missingGemini = false, missingYouTube = false;
    let submittedCourse, releaseCourse;
    const courses = [{ courseId: 'navigation-course', topic: 'Python loops', status: 'active', progress: 0, completedLessons: 0, totalLessons: 1, curriculum: [{ title: 'Loops', searchQuery: 'Python loops', description: 'Learn to repeat a step.', completed: false }] }];
    const dashboard = { courses, history: [], quizScores: [], codingRevisionTasks: [], selectedCourseId: courses[0].courseId, curriculum: courses[0].curriculum, currentTopic: 'Python loops', learningMode: 'course', courseStatus: 'active', currentLesson: 0, courseProgress: 0, totalVideos: 0, completedVideos: 0, averageProgress: 0, totalWatchTimeMinutes: 0, rewardPoints: 0 };
    await page.route('https://www.youtube.com/**', route => { youtubeRequests++; return route.abort('internetdisconnected'); });
    await page.route('**/api/**', async route => {
      const request = route.request(), url = new URL(request.url());
      let json;
      if (url.pathname === '/api/agent/recommend') {
        if (missingGemini) return route.continue();
        submittedCourse = request.postDataJSON();
        if (releaseCourse) await new Promise(resolve => { releaseCourse = resolve; });
        json = { courseId: courses[0].courseId, courseTitle: 'Python loops', lessons: courses[0].curriculum };
      } else if (url.pathname === '/api/youtube/search') {
        if (missingYouTube) return route.continue();
        json = url.searchParams.has('lessonTopic') ? [] : [{ videoId: 'test-video', title: 'Python loops explained', channelTitle: 'Test channel' }];
      } else if (url.pathname.includes('/dashboard')) json = dashboard;
      else if (url.pathname === '/api/coding/config') json = { aiProvider: 'none', serverVerification: false };
      else if (url.pathname === '/api/coding/sync') json = { acknowledgements: [], state: { concepts: {}, revisionTasks: [] } };
      else if (url.pathname === '/api/coding/history') json = { attempts: [], courses, state: { concepts: {}, revisionTasks: [] } };
      else if (url.pathname.startsWith('/api/progress/resume/')) json = { currentTime: 0 };
      else return route.fulfill({ status: 404, json: { error: 'No test fixture for this route.' } });
      return route.fulfill({ status: 200, json });
    });

    async function active(id) {
      await page.waitForFunction(id => document.querySelector('.view.active')?.id === id, id);
      assert.equal(await page.locator('.view.active').count(), 1);
    }
    const out = path.join(__dirname, '../test-results'); fs.mkdirSync(out, { recursive: true });
    await page.goto(base + '/?userId=navigation_student');
    await active('startView');
    assert.equal(await page.locator('.choice').count(), 4);
    assert.equal(youtubeRequests, 0);
    await page.screenshot({ path: path.join(out, 'home-desktop.png'), fullPage: true });
    await page.locator('#courseChoice').click(); await active('learningView');
    assert.equal(await page.locator('#primarySearchButton').innerText(), 'Plan my course');
    await page.locator('#topicInput').fill('Python loops'); await page.locator('#topicInput').press('Enter');
    await page.waitForFunction(() => document.getElementById('status').textContent.includes('No videos were found'));
    assert.deepEqual(submittedCourse, { topic: 'Python loops', userId: 'navigation_student' });
    assert.equal(await page.locator('.recommendation').count(), 1);
    assert.equal(youtubeRequests, 0);
    console.log('PASS: home loads without YouTube; course entry and Enter submit the selected student and topic.');

    await page.locator('#homeButton').click(); await page.locator('#topicChoice').click(); await active('learningView');
    assert.equal(await page.locator('#primarySearchButton').innerText(), 'Find videos');
    await page.locator('#topicInput').fill('Python loops'); await page.locator('#primarySearchButton').click();
    await page.locator('.video-card').waitFor(); await page.locator('.video-card').focus(); await page.keyboard.press('Enter');
    await page.waitForFunction(() => document.getElementById('status').textContent.includes('Could not load the YouTube player'));
    assert.equal(youtubeRequests, 1);
    await page.locator('#homeButton').click(); await active('startView');
    console.log('PASS: topic entry/search and keyboard video selection work; failed YouTube loading leaves navigation usable.');

    missingGemini = true;
    await page.locator('#courseChoice').click(); await page.locator('#topicInput').fill('Python'); await page.locator('#primarySearchButton').click();
    await page.waitForFunction(() => document.getElementById('status').textContent.includes('GEMINI_API_KEY'));
    assert.equal(await page.locator('#primarySearchButton').isDisabled(), false);
    assert.equal(await page.locator('.recommendation').count(), 0);
    missingGemini = false; missingYouTube = true;
    await page.locator('#homeButton').click(); await page.locator('#topicChoice').click();
    await page.locator('#topicInput').fill('Python'); await page.locator('#primarySearchButton').click();
    await page.waitForFunction(() => document.getElementById('status').textContent.includes('YOUTUBE_API_KEY'));
    missingYouTube = false;
    console.log('PASS: visible real missing-key errors; no fake generated course.');

    await page.locator('#homeButton').click(); await page.locator('#courseChoice').click();
    releaseCourse = true; await page.locator('#topicInput').fill('Delayed course'); await page.locator('#primarySearchButton').click();
    await page.waitForFunction(() => document.getElementById('primarySearchButton').disabled);
    await page.locator('#homeButton').click(); await page.locator('#topicChoice').click();
    assert.equal(typeof releaseCourse, 'function'); releaseCourse(); releaseCourse = null;
    await page.waitForLoadState('networkidle');
    assert.equal(await page.locator('#workspaceTitle').innerText(), 'Learn one topic');
    assert.equal(await page.locator('.recommendation').count(), 0);
    console.log('PASS: a late course response cannot replace another workspace.');

    await page.locator('#homeButton').click(); await page.locator('#historyChoice').click(); await active('dashboardView');
    await page.locator('.course-card').first().waitFor();
    await page.locator('.lesson-row').first().click(); await active('learningView');
    await page.waitForFunction(() => document.getElementById('status').textContent.includes('No videos were found'));
    assert.equal(await page.locator('#primarySearchButton').innerText(), 'Plan my course');
    await page.locator('#codingButton').click(); await page.waitForURL('**/coding/**');
    await page.waitForFunction(() => document.getElementById('course').value === 'navigation-course');
    assert.equal(await page.locator('#userId').inputValue(), 'navigation_student');
    await page.locator('#code').fill('# Draft saved before returning home');
    await page.locator('#homeLink').click(); await active('startView');
    assert.equal(await page.locator('#studentId').inputValue(), 'navigation_student');
    await page.locator('#codingChoice').click(); await page.waitForURL('**/coding/**');
    await page.waitForFunction(() => document.getElementById('code').value.includes('Draft saved before returning home'));
    await page.locator('#source').selectOption('custom'); await page.locator('#customDescription').waitFor();
    await page.locator('#dashboardLink').click(); await active('dashboardView');
    await page.locator('.course-card').first().waitFor();
    assert.equal(await page.locator('#studentId').inputValue(), 'navigation_student');
    console.log('PASS: dashboard/resume, coding entry, pasted-question form, saved draft, and return links retain the student.');

    await page.locator('#homeButton').click(); await page.locator('#topicChoice').click();
    await page.goBack(); await active('startView'); await page.goForward(); await active('learningView');
    await page.locator('#homeButton').click();
    await page.locator('#studentId').fill('another_student'); await page.locator('#studentId').press('Tab');
    await page.locator('#codingChoice').click(); await page.waitForURL('**/coding/**');
    await page.waitForFunction(() => document.getElementById('userId').value === 'another_student');
    await page.locator('#learningLink').click(); await active('dashboardView');
    assert.equal(await page.locator('#studentId').inputValue(), 'another_student');
    await page.locator('#learningPath').waitFor();
    await page.locator('#homeButton').click();
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({ path: path.join(out, 'home-mobile.png'), fullPage: true });
    await page.locator('#learningButton').click(); await active('dashboardView');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.deepEqual(errors, []);
    console.log('PASS: all top navigation controls, Back/Forward, student switching, mobile layout; no page script errors.');
  } finally {
    if (browser) await browser.close();
    if (http) await new Promise(resolve => http.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
