# Run PHSS Integrated locally

Use Python 3.11 or 3.12, Node.js 20 or newer, and a running MongoDB server. Extract the ZIP to a normal writable folder. Commands below use PowerShell.

## 1. Configure

Copy `backend-node/.env.example` to `backend-node/.env` and `backend-python/env.example` to `backend-python/.env`.

Set the same `MONGO_URI` in both, and match the Python `MONGO_DATABASE` to the URI's database (default: ai_tutor). Set a random `PHSS_SERVICE_KEY` identically in both files. Set a separate, random Node `SESSION_SECRET` of at least 32 characters. Generate secrets with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

Set `GROQ_API_KEY` and/or `GEMINI_API_KEY` in Python. The shared assistant supports either. Set Node `GEMINI_API_KEY` for the retained legacy learning features and coding explanations when that provider is enabled. Set Node `YOUTUBE_API_KEY` for its dedicated YouTube search. The new learning material links also offer ordinary YouTube search without that key. Provider model names are configurable; choose a model available to your account.

For local development, leave SMTP settings blank to use the existing development-only auto-verification. For production, configure valid SMTP credentials and HTTPS; email verification and reset require SMTP. Never commit either .env file.

Judge0 is optional. Configure Node `JUDGE0_URL` and `JUDGE0_API_KEY` to obtain server-verified coding evidence; otherwise local runs remain provisional in shared CACM.

## 2. Install and build

From the extracted PHSS-Integrated directory:

```powershell
cd backend-python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cd ..\backend-node
npm ci
cd ..\frontend
npm ci
npm run build
```

The research embedding model downloads on first use. Its first report can take longer than subsequent reports.

## 3. Start two terminals

Terminal 1:

```powershell
cd backend-python
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
cd backend-node
npm start
```

Open http://127.0.0.1:3000 and register an account. Keep that hostname consistent throughout login and practice. For frontend development, run `npm run dev` in a third terminal in frontend, and open http://127.0.0.1:5173.

On Linux/macOS use `source .venv/bin/activate` instead of the PowerShell activation command.

## 4. Try the connected flow

1. Ask “Teach me binary search and then give me a coding problem”. Expect Learning followed by Coding, a direct explanation, a saved roadmap and an interview-workspace link.
2. Submit a roadmap quiz. Refresh the CACM panel to inspect graded evidence.
3. Open Coding, choose a company and problem, run code and sync. Browser results appear as provisional in shared CACM; use server verification when Judge0 is configured.
4. Generate a research report. Ask a specific doubt about its method in the shared bar, or choose Learn this topic / Code this topic. The loaded report is included as context.
5. If no suitable video is available, create a lesson-video script, review its transcript, render WebM and download it.

No website is publicly deployed by extracting this project. Configure and validate external services before deployment.
