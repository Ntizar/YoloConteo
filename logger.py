# -*- coding: utf-8 -*-
"""
logger.py — Registro CSV de cruces.
GPS llega del navegador vía POST /api/location, no de IP geolocation.
"""

import os
import csv
import threading
import logging
import re
from datetime import datetime
from typing import Dict, Optional, Tuple

from config import CSV_BASE_DIR, CSV_COLUMNS, SNAPSHOT_FOLDER

logger_py = logging.getLogger(__name__)


class DataLogger:
    """
    Guarda cada cruce en CSV.
    Columnas compatibles con el formato original del proyecto.
    """

    def __init__(self):
        self.latitude: Optional[float]  = None
        self.longitude: Optional[float] = None
        self.location_name: str         = ""
        self.session_id: str            = ""

        self.csv_path: Optional[str]     = None
        self.snapshot_dir: Optional[str] = None
        self._lock = threading.Lock()

        os.makedirs(CSV_BASE_DIR, exist_ok=True)

    # ── Sesión ─────────────────────────────────────────────────────────────────

    def new_session(self) -> None:
        """Crea una nueva carpeta de sesión y el CSV de esta sesión."""
        ts = datetime.now()
        self.session_id = ts.strftime("%Y%m%d_%H%M%S")

        lat_s = f"{self.latitude:.4f}".replace("-", "n") if self.latitude  else "0.0000"
        lon_s = f"{self.longitude:.4f}".replace("-", "n") if self.longitude else "0.0000"
        name  = self._sanitize(self.location_name) or "sesion"

        folder_name = f"{name}_{lat_s}_{lon_s}_{ts.strftime('%Y-%m-%d')}"
        session_dir = os.path.join(CSV_BASE_DIR, folder_name)
        os.makedirs(session_dir, exist_ok=True)

        self.snapshot_dir = os.path.join(session_dir, SNAPSHOT_FOLDER)
        os.makedirs(self.snapshot_dir, exist_ok=True)

        self.csv_path = os.path.join(session_dir, f"registros_{ts.strftime('%H%M%S')}.csv")
        self._init_csv()
        logger_py.info(f"Nueva sesión: {self.csv_path}")

    def _init_csv(self) -> None:
        if self.csv_path and not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=CSV_COLUMNS).writeheader()

    # ── Ubicación (desde el navegador) ────────────────────────────────────────

    def set_location(self, lat: float, lon: float, name: str = "") -> None:
        self.latitude      = lat
        self.longitude     = lon
        self.location_name = name.strip()

    def set_location_name(self, name: str) -> None:
        self.location_name = name.strip()

    def get_location(self) -> Dict:
        return {
            "name": self.location_name,
            "lat":  self.latitude,
            "lng":  self.longitude,
        }

    # ── Registro de cruces ─────────────────────────────────────────────────────

    def log_cross(self, categoria: str, direction: str, counts: Dict) -> None:
        """
        Registra un cruce.
        direction: 'in' (izq→der) o 'out' (der→izq)
        counts: dict devuelto por BidirectionalCounter.get_counts()
        """
        if not self.csv_path:
            return

        now = datetime.now()
        cat_counts = counts.get(categoria, {"in": 0, "out": 0, "total": 0})
        total_dir0  = sum(c["in"]  for c in counts.values())
        total_dir1  = sum(c["out"] for c in counts.values())

        record = {
            "fecha":        now.strftime("%Y-%m-%d"),
            "hora":         now.strftime("%H:%M:%S"),
            "tipo":         categoria,
            "direccion":    0 if direction == "in" else 1,
            "total_tipo":   cat_counts["in"] + cat_counts["out"],
            "total_dir0":   total_dir0,
            "total_dir1":   total_dir1,
            "total_sesion": total_dir0 + total_dir1,
            "ubicacion":    self.location_name,
            "latitude":     self.latitude  if self.latitude  is not None else "",
            "longitude":    self.longitude if self.longitude is not None else "",
            "sesion_id":    self.session_id,
        }

        with self._lock:
            try:
                with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                    csv.DictWriter(f, fieldnames=CSV_COLUMNS).writerow(record)
            except Exception as e:
                logger_py.error(f"Error escribiendo CSV: {e}")

    # ── Exportar resumen ───────────────────────────────────────────────────────

    def export_summary(self, counts: Dict) -> str:
        """Genera CSV de resumen y devuelve la ruta."""
        ts    = datetime.now()
        base  = os.path.dirname(self.csv_path) if self.csv_path else CSV_BASE_DIR
        path  = os.path.join(base, f"resumen_{ts.strftime('%H%M%S')}.csv")

        cols  = CSV_COLUMNS + ["notas"]
        total_dir0 = sum(c["in"]  for c in counts.values())
        total_dir1 = sum(c["out"] for c in counts.values())

        with self._lock:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=cols)
                writer.writeheader()
                for cat, cnt in counts.items():
                    writer.writerow({
                        "fecha":        ts.strftime("%Y-%m-%d"),
                        "hora":         ts.strftime("%H:%M:%S"),
                        "tipo":         cat,
                        "direccion":    "",
                        "total_tipo":   cnt["in"] + cnt["out"],
                        "total_dir0":   cnt["in"],
                        "total_dir1":   cnt["out"],
                        "total_sesion": total_dir0 + total_dir1,
                        "ubicacion":    self.location_name,
                        "latitude":     self.latitude  if self.latitude  is not None else "",
                        "longitude":    self.longitude if self.longitude is not None else "",
                        "sesion_id":    self.session_id,
                        "notas":        "",
                    })
                # Fila total
                writer.writerow({
                    "fecha":        ts.strftime("%Y-%m-%d"),
                    "hora":         ts.strftime("%H:%M:%S"),
                    "tipo":         "TOTAL",
                    "direccion":    "",
                    "total_tipo":   total_dir0 + total_dir1,
                    "total_dir0":   total_dir0,
                    "total_dir1":   total_dir1,
                    "total_sesion": total_dir0 + total_dir1,
                    "ubicacion":    self.location_name,
                    "latitude":     self.latitude  if self.latitude  is not None else "",
                    "longitude":    self.longitude if self.longitude is not None else "",
                    "sesion_id":    self.session_id,
                    "notas":        "dir0=in (izq→der) | dir1=out (der→izq)",
                })

        logger_py.info(f"Resumen exportado: {path}")
        return path

    # ── Snapshot ───────────────────────────────────────────────────────────────

    def save_snapshot(self, frame) -> str:
        """Guarda un frame como JPEG. Devuelve la ruta o ''."""
        if not self.snapshot_dir:
            return ""
        try:
            import cv2
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.snapshot_dir, f"snapshot_{ts}.jpg")
            cv2.imwrite(path, frame)
            return path
        except Exception as e:
            logger_py.error(f"Error guardando snapshot: {e}")
            return ""

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _sanitize(name: str) -> str:
        name = re.sub(r'[<>:"/\\|?*]', "", name)
        name = re.sub(r"[\s,]+", "_", name)
        name = re.sub(r"[^\w\-áéíóúÁÉÍÓÚñÑ]", "", name)
        return name[:50]
