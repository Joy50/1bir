@echo off
setlocal
cd /d "%~dp0"

set "PORT=8000"
set "URL=http://127.0.0.1:%PORT%/"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LAUNCHER=%STARTUP%\1-BIR-start.cmd"

if not exist "%STARTUP%" mkdir "%STARTUP%"

> "%LAUNCHER%" (
  echo @echo off
  echo cd /d "%~dp0"
  echo start "1 BIR Portal" cmd /k python manage.py runserver 127.0.0.1:%PORT%
  echo timeout /t 3 /nobreak ^>nul
  echo start %URL%
)

echo 1 BIR will open automatically when Windows starts.
echo To stop that, delete:
echo   %LAUNCHER%
echo.

start "1 BIR Portal" cmd /k python manage.py runserver 127.0.0.1:%PORT%
timeout /t 3 /nobreak >nul
start %URL%
