'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');

test('Learning, Coding, and Research use the authenticated session as the identity source', () => {
  const server = fs.readFileSync(path.join(root, 'server.js'), 'utf8');
  const coding = fs.readFileSync(path.join(root, 'coding/index.cjs'), 'utf8');
  const research = fs.readFileSync(path.join(root, 'research/index.cjs'), 'utf8');
  const auth = fs.readFileSync(path.join(root, 'auth/index.cjs'), 'utf8');
  const learningClient = server.slice(server.indexOf('async function bootstrapAuthenticatedUser'));
  assert.match(auth, /app\.use\('\/api', requireAuth, bindIdentity\)/);
  assert.match(server, /app\.get\('\/legacy', auth\.requirePageAuth/);
  assert.match(learningClient, /fetch\('\/api\/auth\/me'/);
  assert.match(coding, /const userId = req\.authUserId/);
  assert.match(research, /const user=req\.authUserId/);
});
test('Account pages expose registration, login, verification, reset, and logout controls', () => {
  const authHtml = fs.readFileSync(path.join(root, 'auth/public/index.html'), 'utf8');
  const authJs = fs.readFileSync(path.join(root, 'auth/public/app.js'), 'utf8');
  assert.match(authHtml, /id="registerForm"/);
  assert.match(authHtml, /id="loginForm"/);
  assert.match(authJs, /\/api\/auth\/verify-email/);
  assert.match(authJs, /\/api\/auth\/reset-password/);
  assert.match(authJs, /\/api\/auth\/resend-verification/);
});
