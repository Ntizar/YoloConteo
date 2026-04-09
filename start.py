#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
start.py — Arranca YoloConteo v2 Web en cualquier SO.
Uso: python start.py

Exporta el modelo ONNX si no existe y lanza el servidor local.
"""

import os
import platform
import socket
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
WEB_DIR  = BASE_DIR / "web"
VENV_DIR = BASE_DIR / "venv"
IS_WIN   = platform.system() == "Windows"
PYTHON_VENV = VENV_DIR / ("Scripts" if IS_WIN else "bin") / ("python.exe" if IS_WIN else "python")
PIP_VENV    = VENV_DIR / ("Scripts" if IS_WIN else "bin") / ("pip.exe" if IS_WIN else "pip")

PORT = int(os.environ.get("PORT", 8000))


def banner():
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║     YoloConteo v2 — Versión Web          ║")
    print("  ║     Detección en navegador (WebGPU)      ║")
    print("  ╚══════════════════════════════════════════╝")
    print()


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def ensure_venv():
    if PYTHON_VENV.exists():
        print("[OK] Entorno virtual encontrado.")
        return
    print("[INFO] Creando entorno virtual...")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
    print("[OK] Entorno virtual creado.")


def ensure_onnx_model():
    onnx_path = WEB_DIR / "yolov8n.onnx"
    if onnx_path.exists():
        print("[OK] Modelo ONNX encontrado.")
        return
    print("[INFO] Exportando modelo YOLOv8n a ONNX (primera vez)...")
    subprocess.check_call(
        [str(PIP_VENV), "install", "ultralytics", "onnx", "onnxslim", "onnxruntime", "--quiet"],
        cwd=str(BASE_DIR),
    )
    subprocess.check_call(
        [str(PYTHON_VENV), str(BASE_DIR / "export_model.py")],
        cwd=str(BASE_DIR),
    )
    print("[OK] Modelo ONNX exportado.")


def run_server():
    local_ip = get_local_ip()
    print()
    print(f"  ┌─────────────────────────────────────────────┐")
    print(f"  │   http://localhost:{PORT}        (local)      │")
    print(f"  │   http://{local_ip}:{PORT}  (red local)    │")
    print(f"  └─────────────────────────────────────────────┘")
    print()
    print("  Abre la URL en Chrome/Edge (WebGPU habilitado).")
    print("  Pulsa Ctrl+C para detener el servidor.")
    print()

    subprocess.call(
        [str(PYTHON_VENV), str(WEB_DIR / "serve.py"), str(PORT)],
        cwd=str(BASE_DIR),
    )


def main():
    os.chdir(str(BASE_DIR))
    banner()
    ensure_venv()
    ensure_onnx_model()
    run_server()


if __name__ == "__main__":
    main()
