@echo off
REM Check if the venv exists
if not exist venv (
    echo Virtual environment not found. Creating one...
    python -m venv venv
)

REM Activate the virtual environment
call venv\Scripts\activate

REM Install required packages
echo Installing required packages...
pip install -r requirements.txt

REM Run the Python script
python amade_pyqt_console.py


