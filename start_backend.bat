@echo off
setlocal
echo Starting HELIX V1 Backend...

REM Detect and activate local venv if it exists
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
)

cd helix_backend
python -m uvicorn fullstack.main:app --host 0.0.0.0 --port 8000 --reload
pause
