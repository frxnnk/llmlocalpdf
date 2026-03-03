@echo off
:: Detiene llama-server. Usa PID file si existe (run.bat), sino fallback a taskkill por nombre.

set SCRIPT_DIR=%~dp0
set PID_FILE=%SCRIPT_DIR%llama-server.pid

if exist "%PID_FILE%" (
    set /p SERVER_PID=<"%PID_FILE%"
    taskkill /PID %SERVER_PID% /F >nul 2>&1
    if %errorlevel% equ 0 (
        echo llama-server detenido (PID: %SERVER_PID%).
    ) else (
        echo Proceso PID %SERVER_PID% ya no estaba corriendo.
    )
    del "%PID_FILE%"
) else (
    taskkill /IM llama-server.exe /F >nul 2>&1
    if %errorlevel% equ 0 (
        echo llama-server detenido.
    ) else (
        echo No habia llama-server corriendo.
    )
)
