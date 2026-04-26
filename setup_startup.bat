@echo off
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBS=%~dp0start_listener.vbs
copy /Y "%VBS%" "%STARTUP%\jarvis_wakeup.vbs"
echo.
echo Jarvis wake word listener added to Windows startup.
echo It will auto-start next time you log in.
echo.
echo To start it NOW without rebooting, run:
echo   python "%~dp0wakeup.py"
pause
