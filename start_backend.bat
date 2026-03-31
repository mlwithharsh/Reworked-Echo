@echo off
setlocal
echo Starting ECHO V1 Backend...

REM Detect and activate local venv if it exists
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
)

cd echo_backend
python app.py
pause
