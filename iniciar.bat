@echo off
chcp 65001 >nul
title YoloConteo v2 — Web

:: ── Ir siempre al directorio donde está el bat ────────────────────────────────
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     YoloConteo v2 — Versión Web          ║
echo  ║     Detección en navegador (WebGPU)      ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ── Verificar Python ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.10+ desde https://python.org
    pause
    exit /b 1
)

:: ── Crear entorno virtual si no existe ────────────────────────────────────────
if not exist "venv\" (
    echo [INFO] Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado.
) else (
    echo [OK] Entorno virtual encontrado.
)

:: ── Activar entorno virtual ────────────────────────────────────────────────────
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] No se pudo activar el entorno virtual.
    pause
    exit /b 1
)

:: ── Exportar modelo ONNX si no existe ─────────────────────────────────────────
if not exist "web\yolov8n.onnx" (
    echo.
    echo [INFO] Exportando modelo YOLOv8n a ONNX (primera vez, puede tardar)...
    pip install ultralytics onnx onnxslim onnxruntime --quiet
    if errorlevel 1 (
        echo [ERROR] No se pudieron instalar las dependencias de exportación.
        pause
        exit /b 1
    )
    python export_model.py
    if errorlevel 1 (
        echo [ERROR] No se pudo exportar el modelo.
        pause
        exit /b 1
    )
    echo [OK] Modelo ONNX exportado.
) else (
    echo [OK] Modelo ONNX encontrado.
)

:: ── Arrancar servidor web local ───────────────────────────────────────────────
echo.
echo [INFO] Iniciando servidor web...
echo.
python web\serve.py 8000
echo.
echo [INFO] Servidor detenido.
deactivate
pause
