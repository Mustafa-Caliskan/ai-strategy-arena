@echo off
title AI Strategy Arena - Test Modu
cd /d "%~dp0"
echo.
echo  ==========================================
echo   AI STRATEGY ARENA - TEST MODU
echo   Random AI vs Random AI (API gerekmez)
echo   Gorsel mod
echo  ==========================================
echo.
python main.py --provider-a random --provider-b random --turns 50 --seed 42
echo.
pause > nul
