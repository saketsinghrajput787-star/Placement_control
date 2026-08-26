$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Root) { $Root = Get-Location }

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "AI-ASSISTED PLACEMENT CONTROL TOWER" -ForegroundColor Green
Write-Host "Starting Full-Stack Local Development Servers..." -ForegroundColor Cyan
Write-Host "==================================================="

# Start Backend
Write-Host "[*] Starting FastAPI Backend on http://localhost:8000" -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\backend'; .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# Start Frontend
Write-Host "[*] Starting Vite React Frontend on http://localhost:5173" -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Root\frontend'; npm run dev"

Write-Host "`n[+] Control Tower launched successfully!" -ForegroundColor Green
Write-Host "    - Frontend Dashboard : http://localhost:5173" -ForegroundColor White
Write-Host "    - FastAPI Swagger API: http://localhost:8000/docs" -ForegroundColor White
Write-Host "    - Default Credentials: coordinator@university.edu / admin123`n" -ForegroundColor Gray
