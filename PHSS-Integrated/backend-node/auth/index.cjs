'use strict';

const crypto = require('node:crypto');
const path = require('node:path');
const express = require('express');
const session = require('express-session');
const MongoStore = require('connect-mongo');
const bcrypt = require('bcryptjs');
const nodemailer = require('nodemailer');
const { rateLimit } = require('express-rate-limit');

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const SESSION_DAYS = 7;
const TOKEN_MINUTES = 30;

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}
function randomToken() {
  return crypto.randomBytes(32).toString('base64url');
}
function safeNext(value) {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return '/';
  return value;
}
function sendError(res, status, error) {
  return res.status(status).json({ error });
}
function isAllowedOrigin(origin, host, production) {
  if (!origin) return true;
  try {
    const originUrl = new URL(origin);
    if (originUrl.host === host) return true;
    if (!production) {
      const oHost = originUrl.hostname;
      const rHost = (host || '').split(':')[0];
      if ((oHost === 'localhost' || oHost === '127.0.0.1') &&
          (rHost === 'localhost' || rHost === '127.0.0.1')) {
        return true;
      }
    }
  } catch {}
  return false;
}

function installAuth({ app, mongoose, Student, mongoUri }) {
  const production = process.env.NODE_ENV === 'production';
  const sessionSecret = process.env.SESSION_SECRET;
  if (production && (!sessionSecret || sessionSecret.length < 32)) {
    throw new Error('Production requires SESSION_SECRET with at least 32 characters.');
  }
  if (production && !process.env.APP_BASE_URL) {
    throw new Error('Production requires APP_BASE_URL, e.g. https://your-domain.example.');
  }
  if (production && process.env.APP_BASE_URL && new URL(process.env.APP_BASE_URL).protocol !== 'https:') {
    throw new Error('Production APP_BASE_URL must use HTTPS.');
  }

  const UserSchema = new mongoose.Schema({
    userId: { type: String, required: true, unique: true, index: true },
    name: { type: String, required: true, trim: true, maxlength: 100 },
    email: { type: String, required: true, unique: true, lowercase: true, trim: true, maxlength: 254 },
    passwordHash: { type: String, required: true, select: false },
    emailVerified: { type: Boolean, default: false, index: true },
    role: { type: String, enum: ['student', 'admin'], default: 'student' },
    verificationTokenHash: { type: String, select: false },
    verificationExpiresAt: { type: Date, select: false },
    resetTokenHash: { type: String, select: false },
    resetExpiresAt: { type: Date, select: false },
    createdAt: { type: Date, default: Date.now }
  }, { timestamps: true, versionKey: false });
  const User = mongoose.models.AuthUser || mongoose.model('AuthUser', UserSchema);

  const mailReady = Boolean(process.env.SMTP_HOST && process.env.SMTP_PORT && process.env.SMTP_FROM);
  function mailer() {
    if (!mailReady) throw new Error('Email service is not configured. Set SMTP_HOST, SMTP_PORT, and SMTP_FROM in .env.');
    return nodemailer.createTransport({
      host: process.env.SMTP_HOST,
      port: Number(process.env.SMTP_PORT),
      secure: String(process.env.SMTP_SECURE || '').toLowerCase() === 'true',
      auth: process.env.SMTP_USER ? { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS || '' } : undefined
    });
  }
  function baseUrl() {
    return (process.env.APP_BASE_URL || `http://localhost:${process.env.PORT || 3000}`).replace(/\/$/, '');
  }
  async function sendVerification(user, token) {
    const url = `${baseUrl()}/auth/?mode=verify&token=${encodeURIComponent(token)}`;
    await mailer().sendMail({
      from: process.env.SMTP_FROM,
      to: user.email,
      subject: 'Verify your Personalized Hybrid Study System account',
      text: `Hi ${user.name},\n\nVerify your email using this link. It expires in ${TOKEN_MINUTES} minutes:\n${url}\n\nIf you did not create this account, you can ignore this email.`
    });
  }
  async function sendReset(user, token) {
    const url = `${baseUrl()}/auth/?mode=reset&token=${encodeURIComponent(token)}`;
    await mailer().sendMail({
      from: process.env.SMTP_FROM,
      to: user.email,
      subject: 'Reset your Personalized Hybrid Study System password',
      text: `Hi ${user.name},\n\nReset your password using this single-use link. It expires in ${TOKEN_MINUTES} minutes:\n${url}\n\nIf you did not request this, ignore this email.`
    });
  }

  app.set('trust proxy', production ? 1 : false);
  const sessionStore = MongoStore.create({
  mongoUrl: mongoUri,
  collectionName: 'sessions',
  ttl: SESSION_DAYS * 24 * 60 * 60
});
  app.use(session({
    name: 'phss.sid',
    secret: sessionSecret || crypto.randomBytes(48).toString('hex'),
    resave: false,
    saveUninitialized: false,
    rolling: true,
    store: MongoStore.create({ mongoUrl: mongoUri, collectionName: 'sessions', ttl: SESSION_DAYS * 24 * 60 * 60 }),
    cookie: {
      httpOnly: true,
      secure: production,
      sameSite: 'lax',
      maxAge: SESSION_DAYS * 24 * 60 * 60 * 1000,
      path: '/'
    }
  }));

  const router = express.Router();
  const authLimiter = rateLimit({ windowMs: 15 * 60 * 1000, limit: 10, standardHeaders: true, legacyHeaders: false, message: { error: 'Too many attempts. Please wait and try again.' } });
  const resetLimiter = rateLimit({ windowMs: 60 * 60 * 1000, limit: 5, standardHeaders: true, legacyHeaders: false, message: { error: 'Too many password-reset attempts. Please wait and try again.' } });

  // Same-origin check for browser state-changing requests. SameSite cookies provide an additional layer.
  router.use((req, res, next) => {
    res.set('Cache-Control', 'no-store');
    if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method)) return next();
    const origin = req.get('origin');
    if (!origin) return next(); // Non-browser clients may not send Origin; authentication and rate limits still apply.
    try {
      if (!isAllowedOrigin(origin, req.get('host'), production)) return sendError(res, 403, 'Request origin is not allowed.');
    } catch { return sendError(res, 403, 'Invalid request origin.'); }
    next();
  });

  router.post('/register', authLimiter, async (req, res) => {
    try {
      if (!mailReady && production) return sendError(res, 503, 'Email verification is not configured yet. Configure SMTP settings before accepting registrations.');
      const name = typeof req.body?.name === 'string' ? req.body.name.trim() : '';
      const email = typeof req.body?.email === 'string' ? req.body.email.trim().toLowerCase() : '';
      const password = typeof req.body?.password === 'string' ? req.body.password : '';
      if (name.length < 2 || name.length > 100) return sendError(res, 400, 'Enter a name between 2 and 100 characters.');
      if (!EMAIL_RE.test(email) || email.length > 254) return sendError(res, 400, 'Enter a valid email address.');
      if (password.length < 12 || password.length > 128) return sendError(res, 400, 'Password must be between 12 and 128 characters.');
      if (await User.exists({ email })) return sendError(res, 409, 'An account with this email already exists. Try logging in or resetting your password.');
      const token = randomToken();
      const user = await User.create({
        userId: crypto.randomUUID(), name, email,
        passwordHash: await bcrypt.hash(password, 12),
        emailVerified: !mailReady,
        verificationTokenHash: sha256(token),
        verificationExpiresAt: new Date(Date.now() + TOKEN_MINUTES * 60 * 1000)
      });
      try {
        await Student.findOneAndUpdate(
          { userId: user.userId },
          { $setOnInsert: { userId: user.userId, name: user.name, email: user.email } },
          { upsert: true, new: true }
        );
        if (mailReady) {
          await sendVerification(user, token);
        } else {
          console.log(`[auth][DEV] SMTP not configured. Account auto-verified for local dev. Verification link:\n${baseUrl()}/auth/?mode=verify&token=${encodeURIComponent(token)}`);
        }
      } catch (error) {
        await User.deleteOne({ _id: user._id });
        await Student.deleteOne({ userId: user.userId });
        console.error('[auth] registration email/setup failed:', error.message);
        return sendError(res, 503, 'We could not complete registration because the email service is unavailable. Check the email configuration and try again.');
      }
      return res.status(201).json({
        message: mailReady
          ? 'Account created. Check your email for the verification link before logging in.'
          : 'Account created and verified (development mode). You can now log in.'
      });
    } catch (error) {
      if (error?.code === 11000) return sendError(res, 409, 'An account with this email already exists.');
      console.error('[auth] registration failed:', error.message);
      return sendError(res, 500, 'Registration could not be completed. Please try again.');
    }
  });

  router.post('/resend-verification', authLimiter, async (req, res) => {
    const generic = 'If this email belongs to an unverified account, a new verification link will be sent.';
    try {
      const email = typeof req.body?.email === 'string' ? req.body.email.trim().toLowerCase() : '';
      if (!EMAIL_RE.test(email) || !mailReady) return res.json({ message: generic });
      const user = await User.findOne({ email, emailVerified: false });
      if (user) {
        const token = randomToken();
        user.verificationTokenHash = sha256(token);
        user.verificationExpiresAt = new Date(Date.now() + TOKEN_MINUTES * 60 * 1000);
        await user.save();
        try { await sendVerification(user, token); }
        catch (error) { console.error('[auth] resend verification failed:', error.message); }
      }
      return res.json({ message: generic });
    } catch (error) {
      console.error('[auth] resend verification failed:', error.message);
      return sendError(res, 500, 'Could not request another verification email. Please try again.');
    }
  });

  router.get('/verify-email', async (req, res) => {
    try {
      const token = typeof req.query.token === 'string' ? req.query.token : '';
      if (!token || token.length > 200) return sendError(res, 400, 'Verification link is invalid or expired. Request a new registration link if needed.');
      const user = await User.findOne({ verificationTokenHash: sha256(token), verificationExpiresAt: { $gt: new Date() } }).select('+verificationTokenHash +verificationExpiresAt');
      if (!user) return sendError(res, 400, 'Verification link is invalid or expired.');
      user.emailVerified = true;
      user.verificationTokenHash = undefined;
      user.verificationExpiresAt = undefined;
      await user.save();
      return res.json({ message: 'Email verified. You can now log in.' });
    } catch (error) {
      console.error('[auth] email verification failed:', error.message);
      return sendError(res, 500, 'Email verification failed. Please try again.');
    }
  });

  router.post('/login', authLimiter, async (req, res) => {
    try {
      const email = typeof req.body?.email === 'string' ? req.body.email.trim().toLowerCase() : '';
      const password = typeof req.body?.password === 'string' ? req.body.password : '';
      if (!EMAIL_RE.test(email) || !password) return sendError(res, 400, 'Enter your email and password.');
      const user = await User.findOne({ email }).select('+passwordHash');
      const valid = user ? await bcrypt.compare(password, user.passwordHash) : await bcrypt.compare(password, '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy');
      if (!user || !valid) return sendError(res, 401, 'Email or password is incorrect.');
      if (!user.emailVerified) return sendError(res, 403, 'Verify your email using the link we sent before logging in.');
      await new Promise((resolve, reject) => req.session.regenerate(error => error ? reject(error) : resolve()));
      req.session.userId = user.userId;
      await new Promise((resolve, reject) => req.session.save(error => error ? reject(error) : resolve()));
      return res.json({ message: 'Logged in successfully.', user: { userId: user.userId, name: user.name, email: user.email } });
    } catch (error) {
      console.error('[auth] login failed:', error.message);
      return sendError(res, 500, 'Login could not be completed. Please try again.');
    }
  });

  router.get('/me', async (req, res) => {
    try {
      if (!req.session?.userId) return sendError(res, 401, 'Please log in.');
      const user = await User.findOne({ userId: req.session.userId, emailVerified: true }).lean();
      if (!user) {
        req.session.destroy(() => {});
        return sendError(res, 401, 'Your session is no longer valid. Please log in again.');
      }
      return res.json({ user: { userId: user.userId, name: user.name, email: user.email, role: user.role } });
    } catch (error) {
      console.error('[auth] session lookup failed:', error.message);
      return sendError(res, 500, 'Could not check your session.');
    }
  });

  router.post('/logout', async (req, res) => {
    if (!req.session) return res.json({ message: 'Logged out.' });
    req.session.destroy(error => {
      if (error) return sendError(res, 500, 'Logout failed. Please close your browser after trying again.');
      res.clearCookie('phss.sid', { httpOnly: true, secure: production, sameSite: 'lax', path: '/' });
      return res.json({ message: 'Logged out.' });
    });
  });

  router.post('/forgot-password', resetLimiter, async (req, res) => {
    // Always return the same message to avoid disclosing which email addresses are registered.
    const generic = 'If an account exists for that email, a password-reset link will be sent.';
    try {
      const email = typeof req.body?.email === 'string' ? req.body.email.trim().toLowerCase() : '';
      if (!EMAIL_RE.test(email)) return res.json({ message: generic });
      const user = await User.findOne({ email, emailVerified: true });
      if (user) {
        if (!mailReady) return sendError(res, 503, 'Password reset email is not configured. Contact the site administrator.');
        const token = randomToken();
        user.resetTokenHash = sha256(token);
        user.resetExpiresAt = new Date(Date.now() + TOKEN_MINUTES * 60 * 1000);
        await user.save();
        try { await sendReset(user, token); }
        catch (error) { console.error('[auth] reset email failed:', error.message); return sendError(res, 503, 'Password reset email could not be sent. Please try again later.'); }
      }
      return res.json({ message: generic });
    } catch (error) {
      console.error('[auth] forgot password failed:', error.message);
      return sendError(res, 500, 'Password reset could not be requested. Please try again.');
    }
  });

  router.post('/reset-password', resetLimiter, async (req, res) => {
    try {
      const token = typeof req.body?.token === 'string' ? req.body.token : '';
      const password = typeof req.body?.password === 'string' ? req.body.password : '';
      if (!token || token.length > 200) return sendError(res, 400, 'Reset link is invalid or expired.');
      if (password.length < 12 || password.length > 128) return sendError(res, 400, 'Password must be between 12 and 128 characters.');
      const user = await User.findOne({ resetTokenHash: sha256(token), resetExpiresAt: { $gt: new Date() } }).select('+resetTokenHash +resetExpiresAt +passwordHash');
      if (!user) return sendError(res, 400, 'Reset link is invalid or expired.');
      user.passwordHash = await bcrypt.hash(password, 12);
      user.resetTokenHash = undefined;
      user.resetExpiresAt = undefined;
      await user.save();
      // Invalidate any sessions tied to this account after a password change.
      await mongoose.connection.collection('sessions').deleteMany({ session: { $regex: user.userId } });
      return res.json({ message: 'Password updated. Please log in with your new password.' });
    } catch (error) {
      console.error('[auth] password reset failed:', error.message);
      return sendError(res, 500, 'Password could not be reset. Please try again.');
    }
  });

  app.use('/auth', express.static(path.join(__dirname, 'public'), { index: 'index.html', dotfiles: 'deny', setHeaders(res) { res.set('Cache-Control', 'no-store'); } }));
  app.use('/api/auth', router);

  async function resolveSession(req) {
    if (!req.session?.userId) return null;
    const user = await User.findOne({ userId: req.session.userId, emailVerified: true }).lean();
    return user || null;
  }
  async function requireAuth(req, res, next) {
    if (req.path === '/health' || req.path === '/ai/health') return next();
    try {
      const user = await resolveSession(req);
      if (!user) {
        if (req.session) req.session.destroy(() => {});
        return sendError(res, 401, 'Your session has expired. Please log in again.');
      }
      req.authUser = { userId: user.userId, name: user.name, email: user.email, role: user.role };
      req.authUserId = user.userId;
      next();
    } catch (error) {
      console.error('[auth] request authentication failed:', error.message);
      return sendError(res, 500, 'Could not verify your session.');
    }
  }
  function bindIdentity(req, res, next) {
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method)) {
      const origin = req.get('origin');
      if (origin) {
        try { if (!isAllowedOrigin(origin, req.get('host'), production)) return sendError(res, 403, 'Request origin is not allowed.'); }
        catch { return sendError(res, 403, 'Invalid request origin.'); }
      }
    }
    if (req.authUser) {
      req.authUserId = req.authUser.userId;
      if (req.body && typeof req.body === 'object') req.body.userId = req.authUserId;
      if (req.query && typeof req.query === 'object') req.query.userId = req.authUserId;
    }
    next();
  }
  function requirePageAuth(req, res, next) {
    resolveSession(req).then(user => {
      if (!user) {
        const nextPath = safeNext(req.originalUrl || '/');
        return res.redirect(302, `/auth/?next=${encodeURIComponent(nextPath)}`);
      }
      req.authUser = { userId: user.userId, name: user.name, email: user.email, role: user.role };
      req.authUserId = user.userId;
      next();
    }).catch(error => {
      console.error('[auth] page authentication failed:', error.message);
      res.status(500).send('Could not verify your session. Please try again.');
    });
  }

  app.use('/api', requireAuth, bindIdentity);
  return { User, requireAuth, requirePageAuth, sessionStore };
}

module.exports = { installAuth };
