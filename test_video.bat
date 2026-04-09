@echo off
chcp 65001 >nul
title YoloConteo v2 — Test con video

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   YoloConteo v2 — Modo de prueba con archivo MP4    ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  Este modo arranca el servidor usando TU PROPIO video
echo  como fuente, sin necesitar una webcam fisica.
echo.

:: ── Verificar entorno virtual ─────────────────────────────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Entorno virtual no encontrado.
    echo [INFO]  Ejecuta primero iniciar.bat para crearlo.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

:: ── Buscar un video de prueba ─────────────────────────────────────────────────
set VIDEO_FILE=

:: Comprobar si el usuario paso el video como argumento
if not "%~1"=="" (
    set VIDEO_FILE=%~1
    goto :found_video
)

:: Buscar un .mp4 en el directorio actual
for %%f in (*.mp4 *.avi *.mov *.mkv) do (
    set VIDEO_FILE=%%f
    goto :found_video
)

echo [AVISO] No se encontro ningun video en este directorio.
echo.
echo  Opciones:
echo    1. Arrastra un archivo .mp4 a esta ventana y pulsa Enter:
set /p VIDEO_FILE=  Video: 

if "%VIDEO_FILE%"=="" (
    echo [ERROR] No se especifico ningun video. Saliendo.
    pause
    exit /b 1
)

:found_video
echo [OK] Usando video: %VIDEO_FILE%
echo.

:: ── Arrancar el servidor con auto-start via variable de entorno ───────────────
echo [INFO] Arrancando servidor en http://localhost:8000
echo [INFO] El video se iniciara automaticamente al abrir la UI.
echo.
echo  1. El servidor arrancara en unos segundos.
echo  2. Abre http://localhost:8000 en el navegador.
echo  3. En "Fuente de video" elige "URL personalizada" y escribe:
echo.
echo       %VIDEO_FILE%
echo.
echo  4. Pulsa "Iniciar".
echo.
echo  Pulsa Ctrl+C para detener.
echo.

:: Pasar la ruta del video como variable de entorno
set YOLOCONTEO_DEFAULT_SOURCE=%VIDEO_FILE%
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

deactivate
pause
