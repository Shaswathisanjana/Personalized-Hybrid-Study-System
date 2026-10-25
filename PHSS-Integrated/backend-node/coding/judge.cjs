'use strict';
const fs = require('node:fs');
const path = require('node:path');
const harness = fs.readFileSync(path.join(__dirname, 'public/harness.py'), 'utf8');
const encode = value => Buffer.from(value, 'utf8').toString('base64');
function decode(value) { return value ? Buffer.from(value, 'base64').toString('utf8') : ''; }

function judgeSource(question, code) {
  const tests = question.tests.map(t => question.mode === 'function' ? { args: t.args } : { stdin: t.stdin });
  const payload = encode(JSON.stringify({ code, mode: question.mode, tests }));
  return harness + '\nimport base64 as _b64\n_payload = _json.loads(_b64.b64decode("' + payload + '"))\nprint(_json.dumps(execute(_payload), allow_nan=False))\n';
}
async function verifyWithJudge(question, code, env = process.env, request = fetch) {
  if (!env.JUDGE0_URL) throw new Error('Server verification is not configured. Local runs still work.');
  const base = env.JUDGE0_URL.replace(/\/+$/, '');
  const headers = { 'Content-Type': 'application/json' };
  if (env.JUDGE0_API_KEY) headers['X-RapidAPI-Key'] = env.JUDGE0_API_KEY;
  if (env.JUDGE0_API_HOST) headers['X-RapidAPI-Host'] = env.JUDGE0_API_HOST;
  if (env.JUDGE0_AUTH_TOKEN) headers['X-Auth-Token'] = env.JUDGE0_AUTH_TOKEN;
  async function json(url, init = {}) {
    const response = await request(url, { ...init, headers, signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error(`Judge service returned HTTP ${response.status}.`);
    return response.json();
  }
  const submission = await json(`${base}/submissions?base64_encoded=true&wait=false`, {
    method: 'POST', body: JSON.stringify({ source_code: encode(judgeSource(question, code)), language_id: Number(env.JUDGE0_PYTHON_LANGUAGE_ID || 71), stdin: '', cpu_time_limit: 4, wall_time_limit: 8, memory_limit: 128000, max_file_size: 1024, enable_network: false })
  });
  if (typeof submission.token !== 'string' || !/^[a-zA-Z0-9-]{10,100}$/.test(submission.token)) throw new Error('Judge did not return a valid submission token.');
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {
    const result = await json(`${base}/submissions/${encodeURIComponent(submission.token)}?base64_encoded=true&fields=status,stdout,stderr,compile_output,message,time,memory`);
    const id = result.status?.id;
    if (id === 1 || id === 2) { await new Promise(resolve => setTimeout(resolve, 700)); continue; }
    if (id === 5) return { interrupted: 'timeout' };
    if (id !== 3) throw new Error(`Judge could not return a complete Python report (${result.status?.description || 'unknown status'}).`);
    const stdout = decode(result.stdout);
    if (!stdout.trim() || stdout.length > 800000) throw new Error('Judge returned an empty or oversized report.');
    try { return JSON.parse(stdout); } catch { throw new Error('Judge returned unreadable output. This run is not verified.'); }
  }
  throw new Error('Judge is still busy. Try server verification later.');
}
module.exports = { judgeSource, verifyWithJudge };
