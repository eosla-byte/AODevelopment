@echo off
setlocal
title INSTALADOR AO PLUGIN
cls

echo ========================================================
echo       INSTALADOR - AO DEVELOPMENT PLUGIN (Revit 2024)
echo ========================================================
echo.

:: 1. Definir Rutas
set "SOURCE_DLL=%~dp0bin\Debug\net48\AOdev.dll"
set "SOURCE_ADDIN=%~dp0AOdev_Release.addin"
set "TARGET_DIR=%APPDATA%\Autodesk\Revit\Addins\2024"

echo [DEBUG] Buscando DLL en: "%SOURCE_DLL%"
echo [DEBUG] Destino: "%TARGET_DIR%"
echo.

:: 2. Verificar Origen
if not exist "%SOURCE_DLL%" (
    color 0C
    echo [ERROR CRITICO] No se encontro el archivo DLL.
    echo Buscado en: "%SOURCE_DLL%"
    echo.
    echo SOLUCION:
    echo 1. Abre Visual Studio.
    echo 2. Ve al menu Build -^> Rebuild Solution.
    echo 3. Vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

:: 3. Crear Carpeta Destino
if not exist "%TARGET_DIR%" (
    echo [INFO] Creando carpeta Addins 2024...
    mkdir "%TARGET_DIR%"
)

:: 4. Limpieza (Borrar versiones viejas)
echo [1/3] Limpiando versiones anteriores...
if exist "%TARGET_DIR%\AOdev" (
    rmdir /S /Q "%TARGET_DIR%\AOdev"
)
del /F /Q "%TARGET_DIR%\AOdev*.addin" >nul 2>&1
del /F /Q "%TARGET_DIR%\AOdev.dll" >nul 2>&1

:: 5. Copiar Archivos
echo [2/3] Instalando archivos nuevos...
copy /Y "%SOURCE_DLL%" "%TARGET_DIR%\AOdev.dll"
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo.
    echo [ERROR] No se pudo copiar el DLL.
    echo CAUSA PROBABLE: Revit esta abierto y bloquea el archivo.
    echo SOLUCION: Cierra Revit completamente e intentalo de nuevo.
    echo.
    pause
    exit /b 1
)

copy /Y "%SOURCE_ADDIN%" "%TARGET_DIR%\AOdev.addin"

:: 6. Verificacion Final
echo [3/3] Verificando...
if exist "%TARGET_DIR%\AOdev.dll" (
    color 0A
    echo.
    echo ===========================================
    echo      INSTALACION EXITOSA CORRECTA
    echo ===========================================
    echo Ya puedes abrir Revit.
) else (
    color 0C
    echo [ERROR] Algo fallo en la verificacion final.
)

echo.
pause
