@echo off
title AI Strategy Arena
cd /d "%~dp0"
echo.
echo  ==========================================
echo   AI STRATEGY ARENA
echo   DeepSeek vs GPT-4o-mini
echo   Gorsel mod baslatiliyor...
echo  ==========================================
echo.
python main.py --provider-a deepseek --provider-b openai --turns 100 --seed 42
echo.
echo Oyun bitti. Kapatmak icin bir tuse basin...
pause > nul
