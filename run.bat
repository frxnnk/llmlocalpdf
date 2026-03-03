@echo off
:: Orquesta el ciclo completo: server → procesar PDFs → cleanup
:: Uso: poner PDFs en input\ y ejecutar este script

set SCRIPT_DIR=%~dp0

echo ==========================================
echo  Pipeline Oficios Judiciales
echo ==========================================
echo.

:: --- Pre-checks ---

:: Verificar que install.bat fue corrido
if not exist "%SCRIPT_DIR%llama-server\llama-server.exe" (
    echo No se encontro llama-server.exe.
    echo Ejecutando install.bat primero...
    echo.
    call "%SCRIPT_DIR%install.bat"
    if %errorlevel% neq 0 exit /b 1
)

:: Activar venv
if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" (
    call "%SCRIPT_DIR%venv\Scripts\activate.bat"
) else (
    echo ERROR: No se encontro el entorno virtual.
    echo Ejecutar install.bat primero.
    pause & exit /b 1
)

:: Verificar que hay PDFs en input/
if not exist "%SCRIPT_DIR%input" mkdir "%SCRIPT_DIR%input"
dir /b "%SCRIPT_DIR%input\*.pdf" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: No hay archivos PDF en la carpeta input\
    echo Copiar los PDFs a: %SCRIPT_DIR%input\
    pause & exit /b 1
)

:: Contar PDFs
set PDF_COUNT=0
for %%f in ("%SCRIPT_DIR%input\*.pdf") do set /a PDF_COUNT+=1
echo Encontrados %PDF_COUNT% PDF(s) en input\
echo.

:: --- Iniciar servidor LLM ---

:: Si ya esta corriendo, no levantar otro
curl -s http://127.0.0.1:8080/health >nul 2>&1
if %errorlevel% equ 0 (
    echo Servidor LLM ya esta corriendo.
    set SERVER_WAS_RUNNING=1
) else (
    set SERVER_WAS_RUNNING=0
    echo Iniciando servidor LLM (esto tarda ~30 segundos)...
    start "" /min "%SCRIPT_DIR%start_server.bat"

    :: Esperar a que el servidor responda (health check con reintentos)
    set RETRIES=0
    set MAX_RETRIES=30
    :wait_loop
    timeout /t 3 /nobreak >nul
    curl -s http://127.0.0.1:8080/health >nul 2>&1
    if %errorlevel% equ 0 goto server_ready
    set /a RETRIES+=1
    echo   Esperando servidor... (%RETRIES%/%MAX_RETRIES%)
    if %RETRIES% lss %MAX_RETRIES% goto wait_loop

    echo ERROR: El servidor no respondio despues de 90 segundos.
    echo Revisar la ventana del servidor por errores.
    taskkill /IM llama-server.exe /F >nul 2>&1
    pause & exit /b 1
)

:server_ready
echo Servidor LLM listo.
echo.

:: --- Procesar PDFs ---

echo Procesando %PDF_COUNT% PDF(s)...
echo.
python "%SCRIPT_DIR%process_pdfs.py" --input "%SCRIPT_DIR%input" --output "%SCRIPT_DIR%output" --workers 1
set PROCESS_EXIT=%errorlevel%

:: --- Cleanup ---

:: Solo matar el servidor si nosotros lo levantamos
if %SERVER_WAS_RUNNING% equ 0 (
    echo.
    echo Deteniendo servidor LLM...
    taskkill /IM llama-server.exe /F >nul 2>&1
)

:: --- Resumen ---

echo.
echo ==========================================
if %PROCESS_EXIT% equ 0 (
    echo  Listo! Resultados en: %SCRIPT_DIR%output\
) else (
    echo  Proceso termino con errores (codigo: %PROCESS_EXIT%)
    echo  Revisar logs en: %SCRIPT_DIR%logs\
)
echo ==========================================

:: Abrir carpeta de resultados
if %PROCESS_EXIT% equ 0 explorer "%SCRIPT_DIR%output"

pause
