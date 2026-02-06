@echo off
chcp 65001 >nul
title YoloConteo - Sistema de Conteo Bidireccional

cd /d "%~dp0"

echo ============================================================
echo   YoloConteo - Sistema de Conteo Bidireccional
echo   Deteccion de Personas y Vehiculos de Movilidad Personal
echo ============================================================
echo.

:: Definir rutas del entorno virtual
set "VENV_DIR=%~dp0venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"

:: Buscar Python instalado (usar py launcher o ruta directa)
set "SYSTEM_PYTHON="
where py >nul 2>&1
if %errorlevel%==0 (
    set "SYSTEM_PYTHON=py -3"
) else (
    if exist "C:\Users\david.antizar\AppData\Local\Python\bin\python.exe" (
        set "SYSTEM_PYTHON=C:\Users\david.antizar\AppData\Local\Python\bin\python.exe"
    ) else (
        for %%i in (python.exe) do set "SYSTEM_PYTHON=%%~$PATH:i"
    )
)

if "%SYSTEM_PYTHON%"=="" (
    echo [X] No se encontro Python instalado
    echo     Instale Python desde https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python encontrado: %SYSTEM_PYTHON%

:: Verificar si existe el entorno virtual
if exist "%PYTHON_EXE%" (
    echo [OK] Entorno virtual encontrado
) else (
    echo [!] Entorno virtual no encontrado
    echo [*] Creando entorno virtual...
    %SYSTEM_PYTHON% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [X] Error al crear entorno virtual
        echo     Asegurese de tener Python instalado correctamente.
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado
    echo.
    echo [*] Instalando dependencias basicas...
    "%PIP_EXE%" install --upgrade pip
    "%PIP_EXE%" install ultralytics opencv-python Pillow pandas numpy geocoder requests tqdm
    echo.
    echo [*] Instalando deep-sort-realtime...
    "%PIP_EXE%" install deep-sort-realtime
    echo.
    echo [OK] Dependencias instaladas
)

echo.
echo [*] Iniciando aplicacion...
echo.

:: Ejecutar la aplicación usando la ruta completa del Python del venv
"%PYTHON_EXE%" main.py

:: Si hay error, pausar para ver el mensaje
if errorlevel 1 (
    echo.
    echo [X] Error al ejecutar la aplicacion
    echo     Verifique que todas las dependencias esten instaladas.
    echo     Puede intentar: "%PIP_EXE%" install -r requirements.txt
    echo.
    pause
)

pause
