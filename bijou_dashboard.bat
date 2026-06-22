@echo off
REM Start Bijou AI Operations Dashboard on Windows

cd /d "C:\Users\W3jde\Movies\Hub\Projects\w3j\bijou-ops-dashboard"

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -r requirements.txt

start http://localhost:8765
uvicorn main:app --host 0.0.0.0 --port 8765 --reload
