@echo off
echo ========================================================
echo   WHAT CAME BACK: AI-Powered Returns Recovery Platform
echo   Gadgetbay - CYPHER 4.0 Challenge 10
echo ========================================================
echo.

echo [1/2] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "What Came Back - Backend API" cmd /k "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo [2/2] Starting Vite Frontend on http://127.0.0.1:5173 ...
start "What Came Back - Frontend Web" cmd /k "cd frontend && npm run dev -- --host 127.0.0.1 --port 5173"

echo.
echo Application successfully launched!
echo - Web Dashboard:  http://127.0.0.1:5173
echo - API & Swagger:  http://127.0.0.1:8000/docs
echo ========================================================
pause
