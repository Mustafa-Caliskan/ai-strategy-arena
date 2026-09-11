@echo off
title AI Strategy Arena v2.0
echo ========================================================
echo   AI STRATEGY ARENA v2.0 - CANLI BENCHMARK VE HARITA
echo ========================================================
echo.
echo Tarayici aciliyor: http://localhost:8000 ...
start http://localhost:8000
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
