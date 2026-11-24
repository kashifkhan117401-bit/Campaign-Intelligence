# Launch Campaign Intelligence Backend (port 8000) and Frontend (port 5173) in separate PowerShell windows
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$root'; .\backend\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000"
)

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$root'; npm.cmd --prefix frontend run dev"
)

Write-Host "Started Campaign Intelligence backend (http://127.0.0.1:8000) and frontend (http://localhost:5173)."
