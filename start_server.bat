@echo off
echo Starting Labhatud System...
echo.
call venv\Scripts\activate.bat
python manage.py runserver
