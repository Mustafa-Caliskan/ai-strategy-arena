@echo off
title AI Strategy Arena - Headless
cd /d "%~dp0"
echo.
echo  ==========================================
echo   HEADLESS TEST - 10 oyun batch
echo   DeepSeek vs GPT (konsol ciktisi)
echo  ==========================================
echo.
python main.py --headless --provider-a deepseek --provider-b openai --turns 50 --batch 5
echo.
pause > nul
