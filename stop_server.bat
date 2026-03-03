@echo off
:: Mata todos los procesos llama-server
taskkill /IM llama-server.exe /F 2>nul
if %errorlevel% equ 0 (
    echo llama-server detenido.
) else (
    echo No habia llama-server corriendo.
)
