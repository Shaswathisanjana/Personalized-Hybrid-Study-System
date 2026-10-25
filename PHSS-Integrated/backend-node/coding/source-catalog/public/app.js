'use strict';
const $ = id => document.getElementById(id);
const Core = CodingCore, DB = PracticeDB;
const params = new URLSearchParams(location.search);
let catalog, solutions, activeUser = '', selectedQuestion, currentRun = null, latestAttempt = null;
let config = { aiProvider: 'none', serverVerification: false }, draftTimer, lastDraftKey;
const syncLocks = new Map();
const manualVideoTopics = new Set();
let questionLoadVersion = 0, questionLoading = false, selectionQueue = Promise.resolve();
const studentPattern = /^[a-zA-Z0-9_-]{1,80}$/;
function status(message) { $('status').textContent = message; }
function node(tag, text, className) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; }
const pretty = value => typeof value === 'string' ? value : JSON.stringify(value, null, 2);
async function api(url, body, timeout = 15000) {
  const response = await fetch(url, { method: body === undefined ? 'GET' : 'POST', headers: body === undefined ? {} : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(timeout) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
  return data;
}
function draftKey() { return `draft:${activeUser}:${$('source').value === 'custom' ? 'custom' : $('question').value}`; }
function draftValue() { return { code: $('code').value, customId: selectedQuestion?.id?.startsWith('custom:') ? selectedQuestion.id : `custom:${crypto.randomUUID()}`, title: $('customTitle').value, description: $('customDescription').value, topic: $('customTopic').value, mode: $('customMode').value, tests: $('customTests').value, practiceInputs: $('practiceInputs')?.value }; }
async function saveDraft() {
  clearTimeout(draftTimer);
  if (!activeUser || !lastDraftKey) return;
  try { await DB.set(lastDraftKey, draftValue()); $('draftStatus').textContent = 'Draft saved on this browser.'; }
  catch { $('draftStatus').textContent = 'Draft could not be saved. Copy your code before closing this page.'; }
}
function scheduleDraft() {
  clearTimeout(draftTimer); draftTimer = setTimeout(saveDraft, 350);
  if (latestAttempt) {
    $('result').replaceChildren(node('p', 'Code changed since the displayed attempt. Run tests to evaluate this version.', 'note'));
    $('aiResult').replaceChildren(); latestAttempt = null; updateActions();
  }
}
async function loadQuestion() {
  const ticket = ++questionLoadVersion, key = draftKey(), userAtStart = activeUser;
  questionLoading = true;
  const custom = $('source').value === 'custom';
  $('bankLabel').hidden = custom; $('bankProblem').hidden = custom; $('customProblem').hidden = !custom;
  const draft = await DB.get(key);
  if (ticket !== questionLoadVersion || key !== draftKey() || userAtStart !== activeUser) return;
  lastDraftKey = key;
  if (custom) {
    $('customTitle').value = draft?.title || '';
    $('customDescription').value = draft?.description || '';
    $('customTopic').value = draft?.topic || 'unclassified';
    $('customMode').value = draft?.mode || 'function';
    $('customTests').value = draft?.tests || '[{"args":[[1,2,3]],"expected":6}]';
    selectedQuestion = { id: draft?.customId || `custom:${crypto.randomUUID()}` };
    $('code').value = draft?.code ?? 'def solve(nums):\n    # Replace this with your solution.\n    return sum(nums)\n';
  } else {
    selectedQuestion = catalog.questions.find(q => q.id === $('question').value) || catalog.questions[0];
    $('questionTitle').textContent = selectedQuestion.title;
    $('description').textContent = selectedQuestion.description;
    $('constraints').textContent = Array.isArray(selectedQuestion.constraints) ? selectedQuestion.constraints.join(' · ') : selectedQuestion.constraints;
    $('contract').textContent = selectedQuestion.mode === 'function' ? 'Define solve(...) and return your answer. The runner calls it separately for every test.' : 'Read the supplied input with input() and print the requested output.';
    $('samples').textContent = JSON.stringify(selectedQuestion.tests, null, 2);
    $('conceptHint').textContent = selectedQuestion.hint;
    $('code').value = draft?.code ?? selectedQuestion.starterCode;
  }
  questionLoading = false;$('code').disabled=false;$('run').disabled=false;
  if ($('activeProblemLabel')) $('activeProblemLabel').textContent = (custom ? $('customTitle').value || 'Custom question' : selectedQuestion.title) + (selectedQuestion.exploratory ? ' · Exploratory mode — outputs are not graded' : ' · Supplied tests') + (draft ? ' · Your saved draft restored' : ' · Starter code');
  if ($('practiceInputsBox')) {
    $('practiceInputsBox').hidden = !selectedQuestion.exploratory;
    $('practiceInputs').value = draft?.practiceInputs || JSON.stringify(selectedQuestion.tests || [], null, 2);
  }
  if (!custom) await DB.set('selectedProblem:'+activeUser, {questionId:selectedQuestion.id,question:selectedQuestion.exploratory?selectedQuestion:null});
  window.dispatchEvent(new CustomEvent('cacm:problem-loaded', {detail: {questionId:selectedQuestion.id, title:selectedQuestion.title, exploratory:Boolean(selectedQuestion.exploratory)}}));
  $('modeLabel').textContent = `Python · ${custom ? $('customMode').value : selectedQuestion.mode} mode`;
  latestAttempt = null; $('workedSolution').hidden = true; $('workedSolution').open = false; updateActions();
  $('result').replaceChildren(node('p', 'Run your code to see the diagnostic and test results.', 'muted')); $('aiResult').replaceChildren();
}
function questionFromForm() {
  if ($('source').value === 'bank') {
    if (selectedQuestion.exploratory) {
      let tests; try { tests = JSON.parse($('practiceInputs').value); } catch {throw new Error('Practice inputs must be a JSON array.');}
      if (!Array.isArray(tests) || !tests.length) throw new Error('Add at least one practice input and complete the solve adapter before running.');
      const q = {...selectedQuestion, tests: tests.map(t => ({args:t.args}))};
      return Core.validateQuestion(q,true);
    }
    return selectedQuestion;
  }
  let tests;
  try { tests = JSON.parse($('customTests').value); } catch { throw new Error('Tests must be valid JSON. Put strings in double quotes and use \\n for newlines.'); }
  return Core.validateQuestion({ id: selectedQuestion.id, title: $('customTitle').value.trim(), description: $('customDescription').value, topic: $('customTopic').value, mode: $('customMode').value, tests }, true);
}
function setBusy(busy) {
  window.dispatchEvent(new CustomEvent('cacm:run-state',{detail:{busy}}));
  for (const id of ['run', 'loadStudent', 'userId', 'course', 'source', 'question', 'customMode', 'errorExample', 'code', 'practiceInputs']) $(id).disabled = busy;
  $('stop').disabled = !busy; updateActions();
}
function updateActions() {
  $('explain').disabled = Boolean(currentRun) || !latestAttempt || config.aiProvider === 'none';
  $('verify').disabled = Boolean(currentRun) || !latestAttempt || !config.serverVerification || latestAttempt.questionId.startsWith('custom:');
  $('aiConfig').textContent = config.aiProvider === 'none' ? 'Python diagnostics and local hints work without an AI model. Optional AI is disabled.' : `Optional provider: ${config.aiProvider}. AI suggestions can be wrong and never change the test verdict.`;
}
function renderResult(attempt) {
  const solution = solutions[attempt.questionId];
  $('workedSolution').hidden = !solution; $('workedSolution').open = false;
  if (solution) { $('solutionExplanation').textContent = solution.explanation; $('solutionCode').textContent = solution.code; $('solutionComplexity').textContent = solution.complexity; }
  const r = attempt.serverResult || attempt.result, q = attempt.question, info = Core.feedback(q, r);
  const container = $('result'); container.replaceChildren(node('p', q.title + ' · result for saved code at ' + new Date(attempt.createdAt).toLocaleTimeString(), 'small'), node('div', info.title, `verdict ${r.status}`), node('p', info.hint));
  container.append(node('p', attempt.serverResult ? 'Verified by the configured server judge against the supplied bank tests. This is not a LeetCode verdict.' : 'Executed locally in your browser. This is a personal practice report.', 'small'));
  if (['syntax_error', 'runtime_error', 'wrong_answer', 'timeout'].includes(r.status) && CodingRevision.TOPIC_QUERIES[q.topic]) {
    const review = node('a', 'Review this topic in Your next learning steps ↓', 'review-topic-link');
    review.href = '#learningSteps'; container.append(review);
  }
  if (attempt.raw?.message) container.append(node('p', attempt.raw.message, 'small'));
  if (r.error) {
    const details = node('details'); details.append(node('summary', 'Python diagnostic'), node('pre', r.error.traceback || `${r.error.type}: ${r.error.message}`));
    details.open = true; container.append(details);
  }
  for (const c of r.cases) {
    const details = node('details', undefined, 'test');
    details.open = c.status !== 'passed'; details.append(node('summary', `Test ${c.index + 1} · ${c.status.replace(/_/g, ' ')}`));
const displayedInput =
  q.mode === 'function' && Array.isArray(c.input)
    ? c.input.map(value => pretty(value)).join('\n')
    : pretty(c.input);

details.append(node('p', 'Input'), node('pre', displayedInput));
    if (c.asserted) details.append(node('p', 'Expected'), node('pre', pretty(c.expected)));
    details.append(node('p', q.mode === 'function' ? 'Returned value' : 'Printed output'), node('pre', q.mode === 'function' ? pretty(c.actual.value) ?? '(no return value)' : c.actual.stdout || '(empty output)'));
    if (q.mode === 'function' && c.actual.stdout) details.append(node('p', 'Printed output'), node('pre', c.actual.stdout));
    if (c.actual.stderr) details.append(node('p', 'Standard error'), node('pre', c.actual.stderr));
    if (c.actual.error) details.append(node('pre', `${c.actual.error.type}: ${c.actual.error.message}`));
    container.append(details);
  }
}
async function run() {
  if (currentRun || questionLoading) return;
  if (!studentPattern.test(activeUser) || $('userId').value.trim() !== activeUser) {
    status('Enter your Student ID and click Load student before running code.');
    return;
  }
  let q;
  try { q = structuredClone(questionFromForm()); if (!$('code').value.trim() || $('code').value.length > 20000) throw new Error('Enter up to 20,000 characters of Python code.'); }
  catch (error) { status(error.message); return; }
  const attempt = { userId: activeUser, attemptId: crypto.randomUUID(), courseId: $('course').value, questionId: q.id, question: q, code: $('code').value, createdAt: new Date().toISOString(), packVersion: catalog.version, synced: false };
  await saveDraft(); $('aiResult').replaceChildren();
  currentRun = PythonRunner.runPython(q, attempt.code, status); setBusy(true);
  try {
    attempt.raw = await currentRun.promise;
    attempt.result = Core.evaluate(q, attempt.raw);
    latestAttempt = attempt; renderResult(attempt);
    window.dispatchEvent(new CustomEvent('cacm:run-completed', {detail:{attempt}}));
    try {
      await DB.saveAttempt(attempt);
      status('Attempt saved on this laptop.');
      await renderHistory();
      if (navigator.onLine) void sync(activeUser);
    } catch (error) { status('Run complete, but local storage failed. Copy your code and results before closing this page.'); }
  } catch (error) { status(error.message); }
  finally { currentRun = null; setBusy(false); }
}
function renderState(state, pending) {
  $('stateSource').textContent = `${pending ? 'Includes local attempts waiting to sync. ' : 'Saved learning state. '}Estimate uses distinct tested solutions; it is not a calibrated mastery score.`;
  const tasks = $('revisions'); tasks.replaceChildren();
  const relevant = state.revisionTasks.filter(t => t.status === 'pending');
  if (!relevant.length) tasks.append(node('p', 'No pending revision task. Keep practising; repeated mistakes will add a review here.', 'muted'));
  for (const t of relevant) {
    const card = node('div', undefined, 'task'); card.append(node('h3', t.title), node('p', t.instructions), node('p', t.recoveryRequired, 'small'));
    if (t.questionIds.length) {
      const button = node('button', 'Practise this topic');
      button.addEventListener('click', async () => { if (currentRun) return; await saveDraft(); $('source').value = 'bank'; $('question').value = t.questionIds[0]; await loadQuestion(); $('code').focus(); }); card.append(button);
    }
    const videos = node('div'); card.append(videos); tasks.append(card);
    CodingRevision.mount(videos, videoOptions(t.topic, t.questionIds));
  }
  const concepts = $('concepts'); concepts.replaceChildren();
  for (const c of Object.values(state.concepts)) {
    const row = node('div', undefined, 'concept'); row.append(node('strong', c.topic.replace(/_/g, ' ')), node('span', `${Math.round(c.masteryEstimate * 100)}% estimate · ${c.sampleCount} distinct solutions · evidence: ${c.confidence}`));
    row.append(node('p', `${c.provenance.browser_reported} local reports · ${c.provenance.server_verified} server-verified reports`, 'small')); concepts.append(row);
    if (CodingRevision.TOPIC_QUERIES[c.topic] && !relevant.some(t => t.topic === c.topic)) {
      const button = node('button', 'Find revision videos', 'secondary');
      const videos = node('div');
      row.append(button, videos);
      const open = () => { manualVideoTopics.add(activeUser + ':' + c.topic); button.hidden = true; CodingRevision.mount(videos, videoOptions(c.topic)); };
      button.addEventListener('click', open);
      if (manualVideoTopics.has(activeUser + ':' + c.topic)) open();
    }
  }
}
function videoOptions(topic, practiceIds = []) {
  return {
    topic,
    getContext: () => {
      const currentTopic = $('source').value === 'custom' ? $('customTopic').value : selectedQuestion?.topic;
      return { topic, userId: activeUser, courseId: $('course').value,
        questionId: currentTopic === topic ? selectedQuestion?.id : practiceIds[0] || catalog.questions.find(q => q.topic === topic)?.id || '' };
    },
    beforeNavigate: async () => {
      if (currentRun) { status('Finish or stop the current run before opening a lesson.'); return false; }
      await saveDraft(); return true;
    }
  };
}
async function renderHistory() {
  const userId = activeUser;
  const local = await DB.attempts(userId), remote = await DB.get(`remote:${userId}`);
  if (userId !== activeUser) return;
  const merged = new Map((remote?.attempts || []).map(a => [a.attemptId, a]));
  for (const a of local) merged.set(a.attemptId, { ...merged.get(a.attemptId), ...a, serverResult: merged.get(a.attemptId)?.serverResult || a.serverResult });
  const all = [...merged.values()].sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)));
  window.dispatchEvent(new CustomEvent('cacm:attempts', {detail: {userId, attempts: all}}));
  const pending = local.filter(a => !a.synced);
  const state = pending.length || !remote?.state ? Core.project(all, catalog.questions) : remote.state;
  renderState(state, pending.length > 0);
  $('syncStatus').textContent = `${local.length} attempts stored on this browser · ${pending.length} waiting to sync${remote?.fetchedAt ? ' · last contact ' + new Date(remote.fetchedAt).toLocaleString() : ''}`;
  const list = $('history'); list.replaceChildren();
  if (!all.length) list.append(node('p', 'Your attempts will appear here.', 'muted'));
  for (const a of all.slice(0, 100)) {
    const row = node('div', undefined, 'attempt'), button = node('button', a.question?.title || a.questionId, 'link-button');
    button.addEventListener('click', async () => {
      if(currentRun)return;await saveDraft();
      if(!catalog.questions.some(q=>q.id===a.questionId)) {catalog.questions.push(a.question);$('question').add(new Option(a.question.title,a.questionId));}
      $('source').value='bank';$('question').value=a.questionId;await loadQuestion();$('code').value=a.code;
      latestAttempt=a;renderResult(a);updateActions();$('result').scrollIntoView({behavior:'smooth',block:'start'});
    }); row.append(button);
    const localCopy = local.find(v => v.attemptId === a.attemptId);
    const syncLabel = localCopy ? localCopy.synced ? 'synced' : localCopy.syncError ? 'sync needs attention' : 'saved locally' : 'on server';
    row.append(node('div', `${new Date(a.createdAt).toLocaleString()} · ${(a.serverResult || a.result)?.status?.replace(/_/g, ' ')} · ${syncLabel}`, 'attempt-meta'));
    if (localCopy?.syncError) row.append(node('p', localCopy.syncError, 'small'));
    const source = node('details'); source.append(node('summary', 'Saved code'), node('pre', a.code)); row.append(source); list.append(row);
  }
}
function renderCourses(courses, desired) {
  const select = $('course'), old = desired ?? select.value;
  select.replaceChildren(new Option('Independent practice', ''));
  courses.forEach(c => select.add(new Option(c.topic, c.courseId)));
  if ([...select.options].some(o => o.value === old)) select.value = old;
  updateModuleLinks();
}
function updateModuleLinks() {
  const query = new URLSearchParams({ userId: activeUser || $('userId').value || 'student_1' });
  if ($('course').value) query.set('courseId', $('course').value);
  $('homeLink').href = '/?' + query + '#home';
  $('learningLink').href = '/?' + query + '#dashboard';
  $('dashboardLink').href = '/?' + query + '#dashboard';
}
async function sync(userId = activeUser) {
  if (typeof userId !== 'string' || !studentPattern.test(userId)) {
    status('Enter a valid Student ID and click Load student before syncing. Use letters, digits, underscores, or hyphens; no spaces.');
    return;
  }
  // A run may have been saved after the in-flight sync took its queue snapshot.
  while (syncLocks.has(userId)) await syncLocks.get(userId);
  const work = (async () => {
    try {
      const attempts = (await DB.attempts(userId)).filter(a => !a.synced).sort((a, b) => a.createdAt.localeCompare(b.createdAt));
      // Rebuild the roadmap even when older attempts were already acknowledged.
      if (!attempts.length) await api('/api/coding/sync', { userId, attempts: [] });
      for (const a of attempts) {
        const response = await api('/api/coding/sync', { userId, attempts: [a] });
        const ack = response.acknowledgements.find(v => v.attemptId === a.attemptId);
        if (!ack) throw new Error('Server did not acknowledge this attempt. It remains on your laptop.');
        if (['saved', 'duplicate'].includes(ack.status)) { a.synced = true; a.acceptedAt = ack.acceptedAt; delete a.syncError; }
        else a.syncError = ack.error;
        await DB.saveAttempt(a);
      }
      const remote = await api('/api/coding/history?userId=' + encodeURIComponent(userId));
      remote.fetchedAt = new Date().toISOString(); await DB.set(`remote:${userId}`, remote);
      try { localStorage.setItem('cacm.codingUpdated', JSON.stringify({ userId, at: remote.fetchedAt })); } catch (_) {}
      if (activeUser === userId) {
        renderCourses(remote.courses);
        const remaining = (await DB.attempts(userId)).filter(a => !a.synced).length;
        status(remaining ? `Connected. ${remaining} local attempt(s) need attention; see their messages in history.` : 'Connected. Attempts and revision tasks are up to date.');
      }
    } catch (error) {
      if (activeUser === userId) status('Sync unavailable. Local attempts stay saved. ' + error.message);
    } finally { if (activeUser === userId) await renderHistory(); }
  })();
  syncLocks.set(userId, work);
  try { await work; } finally { syncLocks.delete(userId); }
}
async function loadStudent(initial = false) {
  const next = $('userId').value.trim();
  if (!studentPattern.test(next)) { status('Use 1–80 letters, digits, underscores, or hyphens for the student ID.'); return; }
  if (currentRun) return;
  await saveDraft(); activeUser = next; await DB.set('lastStudent', next);
  const savedSelection = await DB.get('selectedProblem:'+next);
  if (savedSelection && !(initial && params.get('question'))) {
    if (savedSelection.question && !catalog.questions.some(q=>q.id===savedSelection.questionId)) {
      catalog.questions.push(savedSelection.question);$('question').add(new Option(savedSelection.question.title,savedSelection.questionId));
    }
    if (catalog.questions.some(q=>q.id===savedSelection.questionId))$('question').value=savedSelection.questionId;
  }
  try { localStorage.setItem('cacm.activeStudent', next); } catch (_) {}
  const remote = await DB.get(`remote:${next}`);
  renderCourses(remote?.courses || [], initial ? params.get('courseId') || '' : '');
  await loadQuestion(); await renderHistory();
  status('Loaded student ' + next + '.');
  if (navigator.onLine) {
    await sync(next);
    if (initial && params.get('courseId')) renderCourses((await DB.get(`remote:${next}`))?.courses || [], params.get('courseId'));
  }
}
async function packStatus(repair = false) {
  if (!('serviceWorker' in navigator)) return false;
  const registration = await navigator.serviceWorker.getRegistration('/coding/');
  if (!registration?.active) return false;
  const channel = new MessageChannel();
  return new Promise(resolve => {
    const timer = setTimeout(() => { channel.port1.close(); resolve(false); }, repair ? 180000 : 5000);
    channel.port1.onmessage = ({ data }) => { clearTimeout(timer); channel.port1.close(); resolve(Boolean(data.ready)); };
    registration.active.postMessage({ type: repair ? 'REPAIR_PACK' : 'PACK_STATUS' }, [channel.port2]);
  });
}
async function downloadPack() {
  $('downloadPack').disabled = true; $('packStatus').textContent = 'Downloading the app and Python runtime. Keep this tab open…';
  try {
    if (!isSecureContext || !('serviceWorker' in navigator)) throw new Error('Use http://localhost:3000 or an HTTPS address.');
    const registration = await navigator.serviceWorker.register('./sw.js', { scope: './', updateViaCache: 'none' });
    await registration.update();
    if (registration.installing || registration.waiting) {
      const worker = registration.installing || registration.waiting;
      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('Download is taking too long. Check the connection and try again.')), 180000);
        const check = () => {
          if (worker.state === 'activated') { clearTimeout(timer); resolve(); }
          else if (worker.state === 'redundant') { clearTimeout(timer); reject(new Error('The pack download failed. Keep the server running and try again.')); }
        };
        worker.addEventListener('statechange', check); check();
      });
    }
    if (!await packStatus() && !await packStatus(true)) throw new Error('Some offline files are missing. Keep the server running and retry the download.');
    const persistent = navigator.storage?.persist ? await navigator.storage.persist() : false;
    $('packStatus').textContent = 'Offline pack ready.' + (persistent ? ' Persistent storage granted.' : ' Export important attempts; browser storage can be cleared.');
    status('Offline pack ready. Bookmark this /coding/ page, then try disconnecting and reloading it.');
  } catch (error) { $('packStatus').textContent = error.message; }
  finally { $('downloadPack').disabled = false; }
}
function updateConnection() { $('connection').textContent = navigator.onLine ? 'Network available' : 'Offline · local practice'; }
async function init() {
  const response = await fetch('./data/questions.json'); if (!response.ok) throw new Error('Question pack is missing.'); catalog = await response.json();
  const solutionsResponse = await fetch('./data/solutions.json'); if (!solutionsResponse.ok) throw new Error('Worked solutions are missing.'); solutions = await solutionsResponse.json();
  catalog.questions.forEach(q => $('question').add(new Option(`${q.title} · ${q.topic.replace(/_/g, ' ')}`, q.id)));
  if (catalog.questions.some(q => q.id === params.get('question'))) $('question').value = params.get('question');
  if (params.get('source') === 'custom') $('source').value = 'custom';
  window.addEventListener('cacm:external-only',({detail})=>{
    questionLoading=true;$('code').disabled=true;$('run').disabled=true;
    if($('activeProblemLabel'))$('activeProblemLabel').textContent=detail.title+' · No local execution available. Your previous draft is preserved.';
  });
  window.addEventListener('cacm:selection-pending', ({detail}) => {
    if(currentRun)return;
    questionLoading=true;$('code').disabled=true;$('run').disabled=true;
    if($('activeProblemLabel'))$('activeProblemLabel').textContent='Loading '+detail.title+' — editor will switch with this selection.';
    latestAttempt=null;$('result').replaceChildren(node('p','Select and load this problem before running.'));updateActions();
  });
  window.addEventListener('cacm:open-problem', event => {
    selectionQueue = selectionQueue.catch(() => {}).then(async () => {
      try {
        if (currentRun) throw new Error('Stop the current run before opening another problem.');
        const incoming = event.detail.question;
        if (incoming) {
          Core.validateQuestion(incoming,true);
          if (!catalog.questions.some(q=>q.id===incoming.id)) {
            catalog.questions.push(incoming);$('question').add(new Option(incoming.title+' · exploratory',incoming.id));
          }
        }
        const id = event.detail.questionId;
        if (!catalog.questions.some(q=>q.id===id)) throw new Error('Question unavailable. Update the offline pack.');
        await saveDraft();$('source').value='bank';$('question').value=id;
        await loadQuestion();
        if (event.detail.focus) {$('code').scrollIntoView({behavior:'smooth',block:'center'});$('code').focus();}
        status('Selected '+selectedQuestion.title+'. Edit your code below and run this problem.');
      } catch(e){status(e.message);}
    });
  });
  if ($('resetProblem')) $('resetProblem').onclick = async () => {
    if(currentRun || questionLoading)return;
    $('code').value=selectedQuestion.starterCode || 'def solve(*args):\n    pass\n';
    latestAttempt=null;$('result').replaceChildren(node('p','Starter restored. Run this code to see new results.'));updateActions();await saveDraft();
  };
  Core.TOPICS.forEach(topic => $('customTopic').add(new Option(topic.replace(/_/g, ' '), topic)));
  let sharedStudent = '';
  try { sharedStudent = localStorage.getItem('cacm.activeStudent') || ''; } catch (_) {}
  $('userId').value = params.get('userId') || sharedStudent || await DB.get('lastStudent') || 'student_1';
  $('course').addEventListener('change', updateModuleLinks);
  // Finish saving and syncing before opening a server-backed learning path.
  for (const id of ['homeLink', 'learningLink', 'dashboardLink']) $(id).addEventListener('click', async event => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (currentRun) { status('Finish or stop this run before opening another page.'); return; }
    await saveDraft();
    if (!navigator.onLine) { status('Your code and attempts are saved here. Reconnect to sync and open the learning path.'); return; }
    if (id !== 'homeLink') await sync(activeUser);
    const target = new URL($(id).href);
    if (id !== 'homeLink' && (await DB.attempts(activeUser)).some(a => !a.synced)) target.searchParams.set('codingPending', '1');
    location.href = target.href;
  });
  $('run').addEventListener('click', run); $('stop').addEventListener('click', () => currentRun?.cancel());
  $('loadStudent').addEventListener('click', () => loadStudent().catch(e => status(e.message)));
  for (const id of ['question', 'source']) $(id).addEventListener('change', async () => { await saveDraft(); loadQuestion().catch(e => status(e.message)); });
  for (const id of ['code', 'customTitle', 'customDescription', 'customTopic', 'customTests', 'customMode', 'practiceInputs']) $(id).addEventListener('input', scheduleDraft);
  $('customMode').addEventListener('change', () => { $('modeLabel').textContent = `Python · ${$('customMode').value} mode`; });
  $('code').addEventListener('keydown', event => { if (event.key !== 'Tab') return; event.preventDefault(); const el = event.target; el.setRangeText('    ', el.selectionStart, el.selectionEnd, 'end'); scheduleDraft(); });
  $('errorExample').addEventListener('click', async () => { await saveDraft(); $('source').value = 'bank'; $('question').value = 'print-through-n'; await loadQuestion(); $('code').value = 'n = int(input())\nfor i in range(1, n + 1)\n    print(i)\n'; scheduleDraft(); });
  $('sync').addEventListener('click', () => sync()); $('downloadPack').addEventListener('click', downloadPack);
  $('export').addEventListener('click', async () => {
    const data = { version: 1, userId: activeUser, exportedAt: new Date().toISOString(), attempts: await DB.attempts(activeUser) };
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    const link = node('a'); link.href = url; link.download = `python-attempts-${activeUser}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $('explain').addEventListener('click', async () => {
    const attempt = latestAttempt; $('explain').disabled = true; $('aiResult').textContent = 'Preparing an optional AI suggestion…';
    try {
      // Server history omits raw reports. Use the locally saved copy if present.
      const local = (await DB.attempts(activeUser)).find(a => a.attemptId === attempt.attemptId);
      if (!local) throw new Error('Run this saved code again locally to request an explanation.');
      const answer = await api('/api/coding/explain', { userId: activeUser, attempt: local }, 55000);
      const box = node('div', undefined, 'ai'); box.append(node('strong', 'AI suggestion · unverified'), node('p', answer.explanation || answer.message), node('p', answer.nextStep || ''));
      if (latestAttempt?.attemptId === attempt.attemptId) $('aiResult').replaceChildren(box);
    } catch (error) { if (latestAttempt?.attemptId === attempt.attemptId) $('aiResult').textContent = error.message; } finally { updateActions(); }
  });
  $('verify').addEventListener('click', async () => {
    const attempt = latestAttempt; const userId = activeUser; $('verify').disabled = true; status('Syncing and requesting server verification…');
    try {
      await sync(userId);
      const data = await api('/api/coding/verify', { userId, attemptId: attempt.attemptId }, 75000);
      const local = (await DB.attempts(userId)).find(a => a.attemptId === attempt.attemptId);
      if (local) { local.serverResult = data.result; await DB.saveAttempt(local); }
      if (activeUser === userId && latestAttempt?.attemptId === attempt.attemptId) { latestAttempt.serverResult = data.result; renderResult(latestAttempt); }
      await sync(userId);
    } catch (error) { status(error.message + ' Your local result remains available.'); } finally { updateActions(); }
  });
  window.addEventListener('online', () => { updateConnection(); void renderHistory(); void sync(); });
  window.addEventListener('offline', () => { updateConnection(); void renderHistory(); });
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') void saveDraft(); });
  // Startup succeeds offline without fetching any API or loading an AI model.
  updateConnection(); void loadStudent(true).then(()=>{window.CACM_WORKSPACE_READY=true;window.dispatchEvent(new Event('cacm:workspace-ready'));}).catch(e => status(e.message));
  $('packStatus').textContent = await packStatus() ? 'Offline pack ready.' : 'Download once while connected for offline use.';
  try { config = await api('/api/coding/config'); } catch { config = await DB.get('config') || config; }
  await DB.set('config', config); updateActions();
}
init().catch(error => status('Practice could not open: ' + error.message));
