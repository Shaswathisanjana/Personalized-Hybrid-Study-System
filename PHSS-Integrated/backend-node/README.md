# Personalized Hybrid Study System

The platform combines three workspaces:

- **Learning Agent:** course/lesson generation, YouTube resources, quizzes, and progress tracking.
- **Coding Agent:** Python practice, browser execution, test evaluation, coding-attempt history, and revision recommendations.
- **Research Agent:** arXiv paper retrieval, evidence extraction, embeddings/clustering, candidate research gaps, and downloadable reports.

This version adds account authentication and protects the existing workspaces with authenticated sessions.

## Authentication features

- Email/password registration and login.
- Unique email addresses and bcrypt password hashing.
- Email verification before first login.
- Server-side sessions stored in MongoDB, using an HTTP-only SameSite cookie.
- Logout, password-reset emails, expiring single-use reset tokens, and resend-verification support.
- Rate limits on sensitive authentication endpoints.
- Backend identity derived from the signed-in session; client-supplied `userId` values are ignored for protected APIs.
- Student dashboard and admin analytics authorization checks.
- Legacy Student ID records are left untouched rather than automatically assigned to whoever registers first.

## 1. Requirements

- Node.js 20+ (Node.js 22 LTS recommended)
- MongoDB (local or managed)
- Python 3.10+ for the Research Agent
- An SMTP provider for email verification and password-reset messages
- Gemini and YouTube API keys if you want those optional integrations

## 2. Configure the environment

In Windows PowerShell, from the folder containing `server.js` and `package.json`:

```powershell
npm install
Copy-Item .env.example .env
```

Open `.env` and set at least:

```dotenv
NODE_ENV=development
PORT=3000
HOST=127.0.0.1
MONGO_URI=mongodb://127.0.0.1:27017/ai_tutor
SESSION_SECRET=replace-with-a-random-secret-at-least-32-characters-long
APP_BASE_URL=http://localhost:3000
SMTP_HOST=your.smtp.host
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=your-smtp-username
SMTP_PASS=your-smtp-password
SMTP_FROM=Personalized Hybrid Study System <no-reply@your-domain.example>
```

Also keep your existing `GEMINI_API_KEY`, `YOUTUBE_API_KEY`, `GEMINI_MODEL`, `RESEARCH_GEMINI_MODEL`, `RESEARCH_PYTHON`, and `CODING_AI_PROVIDER` values if those integrations are used. Never commit `.env` or put API secrets in frontend files.

For local development, `APP_BASE_URL` must match the URL you open in the browser (`http://localhost:3000`). For production, set `NODE_ENV=production`, use a strong unique `SESSION_SECRET`, set `APP_BASE_URL` to the public **HTTPS** URL, configure SMTP, and use a hosting platform that terminates HTTPS correctly. The app binds to `0.0.0.0` by default in production.

## 3. Install the Research Agent dependencies

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r research/requirements.txt
```

If your environment uses another Python executable, set `RESEARCH_PYTHON` in `.env` to its full path.

## 4. Start and use the platform

```powershell
npm start
```

Open `http://localhost:3000/auth/`.

1. Select **Create an account** and register with an email address you can access.
2. Open the verification email and click its link.
3. Return to the login page and sign in.
4. Use the Learning, Coding, and Research workspaces. Refreshing the page should preserve your session.
5. Use **Log out** to end the session. The next visit should return to login.
6. Test **Forgot password?** and **Resend verification email** after configuring SMTP.

## 5. How account identity works

The backend creates a random account ID after registration. It creates the corresponding Student record and uses that account ID to partition learning history, video progress, quiz scores, coding attempts, learner state, and research output folders. APIs ignore user IDs supplied by the browser and use the authenticated account instead.

Existing records with legacy IDs such as `student_1` remain in MongoDB, unchanged. They are **not automatically attached** to new accounts, because a typed ID is not proof of ownership. If you need to preserve a legacy student's records, verify ownership and perform a reviewed, one-time migration for that account. Do not add a public endpoint that lets users claim arbitrary legacy IDs.

The `/api/admin/analytics` endpoint requires a user with the `admin` role. New registrations always receive the `student` role. Assign admin role only through a trusted database/administrative process.

## 6. Security and deployment checklist

Before public launch:

- Use HTTPS and production environment variables; do not use a weak/default session secret.
- Use a managed MongoDB database with backups, restricted credentials, and monitoring.
- Test registration, verification, login, refresh persistence, logout, password reset, and verification resend.
- Create two accounts and confirm neither can access the other's courses, progress, coding attempts, or research reports by editing URL parameters or request bodies.
- Confirm email delivery and recovery links work on the deployed HTTPS domain.
- Keep dependencies updated and add deployment-specific logging, alerting, backup/restore tests, and abuse monitoring.
- Treat this as an authentication integration baseline, not a substitute for a professional security review before public launch.

## 7. Useful checks

```powershell
node --check server.js
node --check auth/index.cjs
node --check coding/index.cjs
node --check research/index.cjs
npm test
```

The Research Agent searches arXiv and generates exploratory evidence-linked candidate gaps; those are not proof that a gap is novel. Coding practice executes Python locally in the browser; optional server-side verification depends on Judge0 configuration.
