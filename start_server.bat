@echo off
:: Levanta llama-server en localhost:8080 (NO accesible desde la red)
:: Tuneado para Xeon E-2336: 6 cores fisicos

set SCRIPT_DIR=%~dp0
set SERVER_EXE=%SCRIPT_DIR%llama-server\llama-server.exe
set MODEL=%SCRIPT_DIR%models\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf

if not exist "%SERVER_EXE%" (
    echo ERROR: No se encontro llama-server.exe
    echo Correr install.bat primero
    pause & exit /b 1
)

python "%SCRIPT_DIR%verify_model.py"
if errorlevel 1 (
    pause & exit /b 1
)

echo Iniciando llama-server en http://127.0.0.1:8080 ...
echo Presionar Ctrl+C para detener
"%SERVER_EXE%" -m "%MODEL%" --host 127.0.0.1 --port 8080 -c 4096 -t 6
