@echo off
echo ===================================================
echo AI-ASSISTED PLACEMENT CONTROL TOWER
echo Starting Full-Stack Local Development Servers...
echo ===================================================

echo [*] Starting FastAPI Backend on http://localhost:8000
start cmd /k "backend\venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [*] Starting Vite Frontend on http://localhost:5173
cd frontend
start cmd /k "npm run dev"

echo.
echo [!] Services launched!
echo     - Control Tower UI: http://localhost:5173
echo     - API Swagger Docs: http://localhost:8000/docs
echo.
pause
