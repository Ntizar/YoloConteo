# -*- coding: utf-8 -*-
"""
stream.py — Generador MJPEG adaptativo.
Produce frames JPEG codificados para multipart/x-mixed-replace.
Ancho de banda por defecto: ~15fps × 60% quality ≈ 225 KB/s vs los ~2.4 MB/s originales.
"""

import cv2
import time
import logging
import threading
from pathlib import Path
from typing import Callable, Generator, Optional

import numpy as np

from config import (
    VIDEO_WIDTH, VIDEO_HEIGHT,
    MJPEG_FPS_DEFAULT, MJPEG_QUALITY_DEFAULT,
    MJPEG_FPS_MAX, MJPEG_QUALITY_MAX,
    SNAPSHOT_INTERVAL,
)

logger = logging.getLogger(__name__)


class MJPEGStream:
    """
    Encapsula la captura de video y expone generate() como generador
    compatible con StreamingResponse de FastAPI.
    Soporta cámaras (índice int / URL RTSP) y archivos de video locales.
    """

    def __init__(self, fps: int = MJPEG_FPS_DEFAULT, quality: int = MJPEG_QUALITY_DEFAULT):
        self.fps     = min(max(1, fps), MJPEG_FPS_MAX)
        self.quality = min(max(10, quality), MJPEG_QUALITY_MAX)
        self._lock   = threading.Lock()

        self._cap: Optional[cv2.VideoCapture] = None
        self._source = None   # int o str
        self._running = False

        # Frame procesado (con anotaciones) puesto aquí por el pipeline principal
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_raw:   Optional[np.ndarray] = None   # raw para snaps

        # ── Metadatos de archivo de video ──────────────────────────────────────
        self.is_video_file: bool = False   # True cuando la fuente es un archivo
        self._total_frames: int  = 0
        self._current_frame: int = 0
        self._video_fps: float   = 25.0   # FPS nativos del video
        self._on_video_end: Optional[Callable] = None  # callback al terminar

    # ── Cámara / archivo ───────────────────────────────────────────────────────

    def open_camera(self, source, on_video_end: Optional[Callable] = None) -> bool:
        """
        Abre una fuente de video.
        source: int (índice webcam), str (ruta archivo local, URL RTSP, …)
        on_video_end: callback sin argumentos llamado cuando un archivo de video termina.
        """
        with self._lock:
            self._release_cap()
            try:
                src = int(source) if str(source).isdigit() else source
                cap = cv2.VideoCapture(src)
                if not cap.isOpened():
                    logger.error(f"No se pudo abrir la fuente: {source}")
                    return False

                # Determinar si es archivo de video local
                is_file = isinstance(src, str) and Path(src).is_file()
                self.is_video_file = is_file

                if is_file:
                    # Leer metadatos del video
                    self._total_frames  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    self._video_fps     = cap.get(cv2.CAP_PROP_FPS) or 25.0
                    self._current_frame = 0
                    self._on_video_end  = on_video_end
                    logger.info(
                        f"Archivo de video abierto: {src}  "
                        f"({self._total_frames} frames @ {self._video_fps:.1f} fps)"
                    )
                else:
                    # Cámara en vivo: forzar resolución preferida
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  VIDEO_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
                    self.is_video_file  = False
                    self._total_frames  = 0
                    self._current_frame = 0
                    self._on_video_end  = None
                    logger.info(f"Cámara abierta: {source}")

                self._cap    = cap
                self._source = source
                self._running = True
                return True
            except Exception as e:
                logger.error(f"Error abriendo fuente {source}: {e}")
                return False

    def close_camera(self) -> None:
        with self._lock:
            self._release_cap()
        logger.info("Fuente de video cerrada")

    def _release_cap(self) -> None:
        if self._cap and self._cap.isOpened():
            self._cap.release()
        self._cap          = None
        self._running      = False
        self.is_video_file = False
        self._total_frames = 0
        self._current_frame = 0

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def video_progress(self) -> float:
        """Progreso del video de 0.0 a 1.0 (0 si es cámara en vivo)."""
        if not self.is_video_file or self._total_frames <= 0:
            return 0.0
        return min(1.0, self._current_frame / self._total_frames)

    def read_raw(self) -> Optional[np.ndarray]:
        """Lee un frame crudo de la fuente (sin anotaciones).
        Para archivos de video controla la velocidad de lectura según los FPS nativos.
        Devuelve None al terminar el video (llama a on_video_end).
        """
        with self._lock:
            if not self.is_open:
                return None
            ok, frame = self._cap.read()
            if not ok:
                # Fin de archivo de video
                if self.is_video_file:
                    callback = self._on_video_end
                    self._release_cap()
                    if callback:
                        # Llamar fuera del lock para evitar deadlocks
                        threading.Thread(target=callback, daemon=True).start()
                return None
            if self.is_video_file:
                self._current_frame += 1
            self._latest_raw = frame
            return frame.copy()

    def put_annotated(self, frame: np.ndarray) -> None:
        """Recibe el frame ya anotado por el pipeline (detector + counter)."""
        with self._lock:
            self._latest_frame = frame

    # ── MJPEG generator ────────────────────────────────────────────────────────

    def generate(self) -> Generator[bytes, None, None]:
        """
        Generador MJPEG para StreamingResponse.
        Emite el último frame anotado disponible.
        Para archivos de video usa los FPS nativos del video como límite superior.
        """
        interval = 1.0 / self.fps
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]

        while True:
            t0 = time.monotonic()

            with self._lock:
                frame = self._latest_frame

            if frame is not None:
                ok, buf = cv2.imencode(".jpg", frame, encode_params)
                if ok:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n"
                        + buf.tobytes()
                        + b"\r\n"
                    )
            else:
                # Emitir imagen de "sin señal"
                placeholder = self._no_signal_frame()
                ok, buf = cv2.imencode(".jpg", placeholder, encode_params)
                if ok:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n"
                        + buf.tobytes()
                        + b"\r\n"
                    )

            elapsed = time.monotonic() - t0
            remaining = interval - elapsed
            if remaining > 0:
                time.sleep(remaining)

    def get_raw_frame(self) -> Optional[np.ndarray]:
        """Devuelve el último frame crudo (para snapshots)."""
        with self._lock:
            return self._latest_raw.copy() if self._latest_raw is not None else None

    @staticmethod
    def _no_signal_frame() -> np.ndarray:
        """Frame negro con texto cuando no hay cámara."""
        img = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
        cv2.putText(
            img, "Sin senal de video", (VIDEO_WIDTH // 2 - 130, VIDEO_HEIGHT // 2),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 80, 80), 2, cv2.LINE_AA,
        )
        return img
