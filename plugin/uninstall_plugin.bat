@echo off
title DESINSTALADOR COMPLETO - AO PLUGIN
cls
echo ========================================================
echo       DESINSTALACION LIMPIA - AO DEVELOPMENT PLUGIN
echo ========================================================
echo.

set "TARGET_DIR=%APPDATA%\Autodesk\Revit\Addins\2024"

echo [INFO] Buscando en: "%TARGET_DIR%"
echo.

:: 1. Eliminar carpeta de binarios
if exist "%TARGET_DIR%\AOdev" (
    echo [BORRANDO] Carpeta AOdev...
    rmdir /S /Q "%TARGET_DIR%\AOdev"
) else (
    echo [INFO] Carpeta AOdev no existe (ya estaba limpia).
)

:: 2. Eliminar archivos .addin
if exist "%TARGET_DIR%\AOdev.addin" (
    echo [BORRANDO] AOdev.addin...
    del /F /Q "%TARGET_DIR%\AOdev.addin"
)

if exist "%TARGET_DIR%\AOdev_Release.addin" (
    echo [BORRANDO] AOdev_Release.addin...
    del /F /Q "%TARGET_DIR%\AOdev_Release.addin"
)

echo.
echo ========================================================
echo       LIMPIEZA COMPLETADA
echo ========================================================
echo Ya no deberia quedar rastro del plugin en Revit 2024.
echo.
pause
