Set-Location $PSScriptRoot
if (-not (Test-Path .\frontend\dist\index.html)) { throw 'Run npm.cmd --prefix frontend run build first.' }
& .\.venv\Scripts\python.exe -B -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
