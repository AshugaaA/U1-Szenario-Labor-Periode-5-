@echo off
setlocal
set "TASK_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%TASK_PYTHON%" (
  "%TASK_PYTHON%" "%~dp0refresh_data.py"
) else (
  python "%~dp0refresh_data.py"
)
if errorlevel 1 (
  echo Daten konnten nicht aktualisiert werden. Die Fehlermeldung oben pruefen.
) else (
  echo Daten aktualisiert. Bitte das Dashboard im Browser neu laden.
)
pause
