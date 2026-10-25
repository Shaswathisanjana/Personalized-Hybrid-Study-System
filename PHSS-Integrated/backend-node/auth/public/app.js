'use strict';
const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const forms = ['loginForm','registerForm','forgotForm','resetForm'];
let resetToken = params.get('token') || '';
let nextPath = params.get('next') || '/';
if (!nextPath.startsWith('/') || nextPath.startsWith('//') || nextPath.includes('\\')) nextPath = '/';
function notice(message, error = false) { $('notice').hidden = !message; $('notice').textContent = message || ''; $('notice').classList.toggle('error', error); }
function show(mode) {
  forms.forEach(id => { $(id).hidden = id !== mode + 'Form'; });
  $('verifyPanel').hidden = mode === 'verify' ? false : true;
  const titles = {
    login: ['Welcome back', 'Log in to continue from where you left off.'],
    register: ['Create your account', 'Join the platform and keep your academic progress in one place.'],
    forgot: ['Reset your password', 'We will send a single-use reset link if the account exists.'],
    reset: ['Choose a new password', 'Use at least 12 characters for your new password.']
  };
  if (titles[mode]) { $('heading').textContent = titles[mode][0]; $('intro').textContent = titles[mode][1]; }
}
async function api(path, body) {
  const response = await fetch(path, { method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin', cache: 'no-store', headers: body === undefined ? {} : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
  return data;
}
function busy(form, state) { const button = form.querySelector('button[type="submit"]'); if (button) { button.disabled = state; button.dataset.original ||= button.textContent; button.textContent = state ? 'Please wait…' : button.dataset.original; } }
document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => { notice(''); show(button.dataset.mode); }));
$('goLogin').addEventListener('click', () => { notice(''); show('login'); });
$('registerForm').addEventListener('submit', async event => {
  event.preventDefault(); notice('');
  if ($('registerPassword').value !== $('registerConfirm').value) return notice('The passwords do not match.', true);
  busy(event.currentTarget, true);
  try {
    const result = await api('/api/auth/register', { name: $('registerName').value.trim(), email: $('registerEmail').value.trim(), password: $('registerPassword').value });
    event.currentTarget?.reset(); show('login'); notice(result.message);
  } catch (error) { notice(error.message, true); }
  finally { busy(event.currentTarget, false); }
});
$('loginForm').addEventListener('submit', async event => {
  event.preventDefault(); notice(''); busy(event.currentTarget, true);
  try {
    await api('/api/auth/login', { email: $('loginEmail').value.trim(), password: $('loginPassword').value });
    location.replace(nextPath);
  } catch (error) { notice(error.message, true); }
  finally { busy(event.currentTarget, false); }
});
$('resendVerification').addEventListener('click', async () => {
  notice('');
  const email = $('loginEmail').value.trim();
  if (!email) return notice('Enter your email address above first.', true);
  try { const result = await api('/api/auth/resend-verification', { email }); notice(result.message); }
  catch (error) { notice(error.message, true); }
});
$('forgotForm').addEventListener('submit', async event => {
  event.preventDefault(); notice(''); busy(event.currentTarget, true);
  try { const result = await api('/api/auth/forgot-password', { email: $('forgotEmail').value.trim() }); notice(result.message); }
  catch (error) { notice(error.message, true); }
  finally { busy(event.currentTarget, false); }
});
$('resetForm').addEventListener('submit', async event => {
  event.preventDefault(); notice('');
  if ($('resetPassword').value !== $('resetConfirm').value) return notice('The passwords do not match.', true);
  busy(event.currentTarget, true);
  try {
    const result = await api('/api/auth/reset-password', { token: resetToken, password: $('resetPassword').value });
    event.currentTarget?.reset(); show('login'); notice(result.message);
  } catch (error) { notice(error.message, true); }
  finally { busy(event.currentTarget, false); }
});
(async function boot() {
  const mode = params.get('mode');
  if (mode === 'verify') {
    show('verify'); $('verifyMessage').textContent = 'Verifying your email…';
    try { const result = await api('/api/auth/verify-email?token=' + encodeURIComponent(params.get('token') || '')); $('verifyMessage').textContent = result.message; }
    catch (error) { $('verifyMessage').textContent = error.message; }
    return;
  }
  if (mode === 'reset') {
    if (!resetToken) { show('login'); notice('The password-reset link is invalid or incomplete.', true); return; }
    show('reset'); return;
  }
  if (mode === 'register') show('register');
  else if (mode === 'forgot') show('forgot');
  else show('login');
  try {
    const result = await api('/api/auth/me');
    if (result.user) location.replace(nextPath);
  } catch (_) { /* A logged-out visitor should see the login form. */ }
})();
