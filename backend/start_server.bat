@echo off
cd /d "%~dp0"
echo Starting AO-Resources Backend...
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause
