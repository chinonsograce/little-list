@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Setup is needed. Please follow README.md first.
  pause
  exit /b 1
)
if not exist dist\index.html (
  echo The frontend needs to be built. Please follow README.md first.
  pause
  exit /b 1
)
echo Little List is available at http://127.0.0.1:8000
echo Keep this window open while using the app. Press Ctrl+C to stop.
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
