@echo off
:: Procesa PDFs: lee de input\, escribe en output\
:: Uso: process.bat
::   o: process.bat ruta\a\pdfs ruta\salida

set SCRIPT_DIR=%~dp0

:: Activar venv si existe
if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" (
    call "%SCRIPT_DIR%venv\Scripts\activate.bat"
)

set INPUT_DIR=%~1
set OUTPUT_DIR=%~2
if "%INPUT_DIR%"=="" set INPUT_DIR=%SCRIPT_DIR%input
if "%OUTPUT_DIR%"=="" set OUTPUT_DIR=%SCRIPT_DIR%output

if not exist "%INPUT_DIR%" (
    echo ERROR: No existe la carpeta de entrada: %INPUT_DIR%
    pause & exit /b 1
)

:: Verificar que llama-server esta corriendo
curl -s http://127.0.0.1:8080/health >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: llama-server no esta corriendo.
    echo Ejecutar start_server.bat primero (en otra ventana).
    pause & exit /b 1
)

echo Procesando PDFs de: %INPUT_DIR%
echo Salida en: %OUTPUT_DIR%

python "%SCRIPT_DIR%process_pdfs.py" --input "%INPUT_DIR%" --output "%OUTPUT_DIR%" --workers 1

echo.
echo Listo. Resultados en: %OUTPUT_DIR%
pause
