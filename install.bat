@echo off

set "project_dir=..\adspower_gmail_checker-main"
set "venv_dir=%project_dir%"

rem Create virtual environment
python -m venv "%venv_dir%"

rem Activate virtual environment
call "%venv_dir%\Scripts\activate"

rem Navigate back to the working directory
cd /d "%~dp0"

rem Install requirements
pip install -r "%project_dir%\requirements.txt"

rem Deactivate virtual environment
deactivate

echo Installation complete.
pause
