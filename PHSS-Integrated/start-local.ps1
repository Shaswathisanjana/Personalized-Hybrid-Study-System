Write-Host 'PHSS Integrated — read SETUP.md for installation and environment configuration.' -ForegroundColor Cyan
Write-Host 'Start MongoDB before continuing.'
Write-Host 'Terminal 1: cd backend-python; .\.venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000'
Write-Host 'Terminal 2: cd backend-node; npm start'
Write-Host 'Build the frontend once first: cd frontend; npm ci; npm run build'
Write-Host 'Open http://127.0.0.1:3000'
