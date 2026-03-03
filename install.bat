@echo off
:: Setup inicial: crear venv, instalar dependencias, descargar modelo

echo ==========================================
echo  Instalacion - Pipeline Oficios Judiciales
echo ==========================================
echo.

set SCRIPT_DIR=%~dp0

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado o no esta en el PATH.
    echo Descargar de https://www.python.org/downloads/
    echo Marcar "Add Python to PATH" durante la instalacion.
    pause & exit /b 1
)

:: Mostrar version
echo Python encontrado:
python --version
echo.

:: Crear venv si no existe
if not exist "%SCRIPT_DIR%venv" (
    echo [1/4] Creando entorno virtual...
    python -m venv "%SCRIPT_DIR%venv"
) else (
    echo [1/4] Entorno virtual ya existe.
)

:: Activar venv
call "%SCRIPT_DIR%venv\Scripts\activate.bat"

echo [2/4] Instalando dependencias Python...
pip install --upgrade pip
pip install -r "%SCRIPT_DIR%requirements.txt"

echo.
echo [3/4] Descargando llama.cpp server y modelo...
python "%SCRIPT_DIR%setup_llm.py"

echo.
echo [4/4] Creando carpetas de trabajo...
if not exist "%SCRIPT_DIR%input" mkdir "%SCRIPT_DIR%input"
if not exist "%SCRIPT_DIR%output" mkdir "%SCRIPT_DIR%output"

echo.
echo ==========================================
echo  Instalacion completa!
echo  1. Poner PDFs en la carpeta "input"
echo  2. Ejecutar start_server.bat
echo  3. Ejecutar process.bat
echo ==========================================
pause
