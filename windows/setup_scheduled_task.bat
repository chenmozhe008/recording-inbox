@echo off
setlocal
set "ROOT=%~dp0.."
set "PY=%ROOT%\asr-venv\Scripts\pythonw.exe"
if not exist "%PY%" set "PY=pythonw.exe"

schtasks /create /tn "recording-inbox" /tr "\"%PY%\" \"%ROOT%\run_launcher.py\"" /sc minute /mo 1 /f
echo.
echo recording-inbox scheduled task installed.
echo Logs: %ROOT%\logs\run.out.log and %ROOT%\logs\run.err.log
endlocal
