@echo off
title AO Development - Build & Install
cls
echo ========================================================
echo       AUTO-BUILD & INSTALL - AO PLUGINS
echo ========================================================
echo.

:: 1. Build Solution
echo [1/2] Compilando Solucion (Release)...
dotnet build "AOdev.csproj" -c Release
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo.
    echo [ERROR] La compilacion fallo.
    echo Asegurate de tener .NET SDK instalado y que los archivos no esten bloqueados.
    pause
    exit /b 1
)

echo.
echo [INFO] Compilacion Exitosa.
echo.

:: 2. Run Installer Script
echo [2/2] Iniciando Instalacion...
call install_plugin.bat
