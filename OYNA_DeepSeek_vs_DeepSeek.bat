@echo off
title AI Strategy Arena
cd /d "%~dp0"
echo.
echo  ==========================================
echo   AI STRATEGY ARENA
echo   DeepSeek vs DeepSeek
echo  ==========================================
echo.
python main.py --provider-a deepseek --provider-b deepseek --turns 100 --seed 42
echo.
pause > nul
