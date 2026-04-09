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
from typing import Generator, Optional

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

    # ── Cámara ─────────────────────────────────────────────────────────────────

    def open_camera(self, source) -> bool:
        """
        Abre una fuente de video.
        source: int (índice webcam), str (ruta archivo o URL RTSP)
        """
        with self._lock:
            self._release_cap()
            try:
                src = int(source) if str(source).isdigit() else source
                cap = cv2.VideoCapture(src)
                if not cap.isOpened():
                    logger.error(f"No se pudo abrir la fuente: {source}")
                    return False
                cap.set(cv2.CAP_PROP_FRAME_WIDTH,  VIDEO_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
                self._cap    = cap
                self._source = source
                self._running = True
                logger.info(f"Cámara abierta: {source}")
                return True
            except Exception as e:
                logger.error(f"Error abriendo cámara {source}: {e}")
                return False

    def close_camera(self) -> None:
        with self._lock:
            self._release_cap()
        logger.info("Cámara cerrada")

    def _release_cap(self) -> None:
        if self._cap and self._cap.isOpened():
            self._cap.release()
        self._cap     = None
        self._running = False

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def read_raw(self) -> Optional[np.ndarray]:
        """Lee un frame crudo de la cámara (sin anotaciones)."""
        with self._lock:
            if not self.is_open:
                return None
            ok, frame = self._cap.read()
            if not ok:
                return None
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
