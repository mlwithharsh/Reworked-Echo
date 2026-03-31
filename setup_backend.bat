@echo off
setlocal
echo Setting up ECHO V1 Backend Dependencies...

REM Detect and activate local venv if it exists
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
)

cd echo_backend
python -m pip install -r requirements.txt
echo [SUCCESS] Setup complete. You can now run start_backend.bat.
pause
