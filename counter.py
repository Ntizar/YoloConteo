# -*- coding: utf-8 -*-
"""
counter.py — Lógica de conteo bidireccional.
Recibe detecciones con track_id (ya asignado por Ultralytics ByteTrack)
y detecta cruces de línea vertical.
"""

import threading
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple

from config import CATEGORY_KEYS, LINE_POSITION_DEFAULT, CROSSING_MARGIN

logger = logging.getLogger(__name__)


@dataclass
class TrackInfo:
    track_id: int
    categoria: str
    historial_x: List[float] = field(default_factory=list)
    cruzado: bool = False
    puede_cruzar: bool = True
    ultimo_lado: str = "ninguno"  # 'izquierda' | 'derecha' | 'ninguno'


class BidirectionalCounter:
    """
    Contador bidireccional que trabaja con los track_id de Ultralytics.
    Detecta el cruce de la línea vertical por posición del centro del bbox.
    """

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        line_position: float = LINE_POSITION_DEFAULT,
        margin: int = CROSSING_MARGIN,
        on_cross: Optional[Callable] = None,
    ):
        self.frame_width  = frame_width
        self.frame_height = frame_height
        self.margin       = margin
        self.on_cross     = on_cross   # callback(categoria, dir_str, track_id)
        self._lock        = threading.Lock()

        self.line_x: int  = int(frame_width * line_position)
        self.line_pos: float = line_position

        self._tracks: Dict[int, TrackInfo] = {}

        # { "persons": {"in": 0, "out": 0}, ... }
        self.counts: Dict[str, Dict[str, int]] = {
            k: {"in": 0, "out": 0} for k in CATEGORY_KEYS
        }

    # ── Configuración dinámica ─────────────────────────────────────────────────

    def set_line_position(self, position: float) -> None:
        """Actualiza posición relativa de la línea (0.0 – 1.0)."""
        position = max(0.02, min(0.98, position))
        with self._lock:
            self.line_pos = position
            self.line_x   = int(self.frame_width * position)

    def update_frame_size(self, width: int, height: int) -> None:
        with self._lock:
            self.frame_width  = width
            self.frame_height = height
            self.line_x       = int(width * self.line_pos)

    # ── Procesamiento de detecciones ───────────────────────────────────────────

    def process(self, detections: List[Dict]) -> None:
        """
        Recibe lista de detecciones con campos:
            track_id, categoria, centro (cx, cy)
        Actualiza contadores si se detecta un cruce.
        """
        with self._lock:
            active_ids = set()
            for det in detections:
                tid = det.get("track_id")
                if tid is None:
                    continue
                categoria = det.get("categoria")
                if categoria not in self.counts:
                    continue
                cx, _cy = det["centro"]
                active_ids.add(tid)
                self._update_track(tid, categoria, cx)

            self._cleanup(active_ids)

    def _update_track(self, tid: int, categoria: str, cx: float) -> None:
        if tid not in self._tracks:
            self._tracks[tid] = TrackInfo(track_id=tid, categoria=categoria)

        track = self._tracks[tid]
        track.historial_x.append(cx)
        if len(track.historial_x) > 60:
            track.historial_x = track.historial_x[-60:]

        self._check_crossing(track)

    def _check_crossing(self, track: TrackInfo) -> None:
        if len(track.historial_x) < 2:
            return

        prev_x = track.historial_x[-2]
        curr_x = track.historial_x[-1]
        line   = self.line_x

        if prev_x < line and curr_x >= line and track.puede_cruzar:
            # left → right  (entrada = "in")
            self.counts[track.categoria]["in"] += 1
            track.puede_cruzar = False
            track.ultimo_lado  = "derecha"
            if self.on_cross:
                self.on_cross(track.categoria, "in", track.track_id)

        elif prev_x > line and curr_x <= line and track.puede_cruzar:
            # right → left  (salida = "out")
            self.counts[track.categoria]["out"] += 1
            track.puede_cruzar = False
            track.ultimo_lado  = "izquierda"
            if self.on_cross:
                self.on_cross(track.categoria, "out", track.track_id)

        else:
            # Resetear cuando el objeto se aleja de la línea
            if abs(curr_x - line) > self.margin:
                track.puede_cruzar = True

    def _cleanup(self, active_ids: set) -> None:
        """Elimina tracks que ya no aparecen en el frame."""
        stale = [tid for tid in self._tracks if tid not in active_ids]
        for tid in stale:
            del self._tracks[tid]

    # ── Consultas ──────────────────────────────────────────────────────────────

    def get_counts(self) -> Dict[str, Dict[str, int]]:
        """Devuelve copia de los contadores actuales con campo 'total' añadido."""
        with self._lock:
            result = {}
            for k, v in self.counts.items():
                result[k] = {"in": v["in"], "out": v["out"], "total": v["in"] + v["out"]}
            return result

    def reset(self) -> None:
        with self._lock:
            self._tracks.clear()
            for k in CATEGORY_KEYS:
                self.counts[k] = {"in": 0, "out": 0}
        logger.info("Contadores reiniciados")

    def get_line_position(self) -> Tuple[int, float]:
        """Devuelve (line_x_pixels, line_pos_relative)."""
        return self.line_x, self.line_pos
