#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export_model.py — Exporta YOLOv8n a formato ONNX para ejecución en navegador.

Uso:
    python export_model.py

Genera: web/yolov8n.onnx (~12 MB)
"""

import shutil
from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).parent.resolve()
SRC = BASE_DIR / "yolov8n.pt"
DST = BASE_DIR / "web" / "yolov8n.onnx"


def main():
    if DST.exists():
        print(f"[OK] Modelo ONNX ya existe: {DST}")
        return

    if not SRC.exists():
        print(f"[ERROR] No se encuentra {SRC}")
        print("        Descarga yolov8n.pt desde https://github.com/ultralytics/assets/releases")
        return

    print(f"[INFO] Exportando {SRC.name} → ONNX (opset 17, simplificado)...")
    model = YOLO(str(SRC))
    model.export(format="onnx", imgsz=640, simplify=True, opset=17)

    # Ultralytics genera el .onnx junto al .pt
    exported = SRC.with_suffix(".onnx")
    if not exported.exists():
        print("[ERROR] La exportación no generó el archivo esperado.")
        return

    DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(exported), str(DST))
    size_mb = DST.stat().st_size / (1024 * 1024)
    print(f"[OK] Modelo exportado: {DST} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
