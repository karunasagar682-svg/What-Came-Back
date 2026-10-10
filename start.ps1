# WHAT CAME BACK - PowerShell Startup Script
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  WHAT CAME BACK: AI-Powered Returns Recovery Platform" -ForegroundColor Green
Write-Host "  Gadgetbay — CYPHER 4.0 Challenge 10" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# Start Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

# Start Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev -- --host 127.0.0.1 --port 5173"

Write-Host "`nApplication launched successfully!" -ForegroundColor Green
Write-Host "- Web Dashboard:  http://127.0.0.1:5173" -ForegroundColor White
Write-Host "- Swagger Docs:   http://127.0.0.1:8000/docs`n" -ForegroundColor White
