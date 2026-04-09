# -*- coding: utf-8 -*-
"""
detector.py — YOLOv8 + Ultralytics ByteTrack.
Reemplaza DeepSort por el tracker built-in de Ultralytics (más rápido, sin deps extra).
"""

import cv2
import numpy as np
import logging
from typing import List, Dict, Optional

from ultralytics import YOLO

from config import (
    YOLO_MODEL_PATH, CONFIDENCE_THRESHOLD, TRACKER,
    COCO_CLASSES, VIDEO_WIDTH, VIDEO_HEIGHT,
    LINE_COLOR_BGR, LINE_THICKNESS,
)

logger = logging.getLogger(__name__)


class YOLODetector:
    """
    Detecta y trackea objetos usando YOLOv8 + ByteTrack (Ultralytics built-in).

    Método principal: track_frame(frame) → List[Dict]
    Cada dict: {track_id, categoria, bbox, centro, confianza, color_bgr}
    """

    def __init__(
        self,
        model_path: str = YOLO_MODEL_PATH,
        confidence: float = CONFIDENCE_THRESHOLD,
    ):
        self.confidence = confidence
        self.model: Optional[YOLO] = None
        self._next_temp_id = 100_000   # IDs temporales cuando tracking no asigna
        self._load_model(model_path)

    def _load_model(self, path: str) -> None:
        try:
            logger.info(f"Cargando modelo YOLO: {path}")
            self.model = YOLO(path)
            logger.info("Modelo cargado correctamente")
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}")
            self.model = None

    # ── Tracking ───────────────────────────────────────────────────────────────

    def track_frame(self, frame: np.ndarray) -> List[Dict]:
        """
        Procesa un frame y devuelve las detecciones trackeadas.
        Solo devuelve objetos cuya clase COCO está en COCO_CLASSES.
        """
        if self.model is None:
            return []

        detections: List[Dict] = []
        try:
            results = self.model.track(
                frame,
                persist=True,
                tracker=TRACKER,
                conf=self.confidence,
                verbose=False,
            )
            if not results:
                return []

            r = results[0]
            if r.boxes is None or len(r.boxes) == 0:
                return []

            clss   = r.boxes.cls.cpu().numpy().astype(int)
            confs  = r.boxes.conf.cpu().numpy()
            boxes  = r.boxes.xyxy.cpu().numpy().astype(int)

            # ByteTrack puede devolver id=None en frames iniciales o a bajo fps
            if r.boxes.id is not None:
                ids = r.boxes.id.cpu().numpy().astype(int)
            else:
                ids = np.arange(
                    self._next_temp_id,
                    self._next_temp_id + len(clss),
                )
                self._next_temp_id += len(clss)

            for tid, cls_id, conf, box in zip(ids, clss, confs, boxes):
                cls_info = COCO_CLASSES.get(cls_id)
                if cls_info is None:
                    continue   # clase no contemplada

                x1, y1, x2, y2 = box
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2

                detections.append({
                    "track_id":  int(tid),
                    "categoria": cls_info["key"],
                    "label":     cls_info["label"],
                    "emoji":     cls_info["emoji"],
                    "bbox":      [x1, y1, x2, y2],
                    "centro":    (cx, cy),
                    "confianza": float(conf),
                    "color_bgr": cls_info["color_bgr"],
                })
        except Exception as e:
            logger.error(f"Error en track_frame: {e}")

        return detections

    # ── Anotación visual ───────────────────────────────────────────────────────

    def draw(
        self,
        frame: np.ndarray,
        detections: List[Dict],
        line_x: int,
    ) -> np.ndarray:
        """Dibuja bboxes, IDs y la línea de conteo sobre el frame."""
        out = frame.copy()
        h, _w = out.shape[:2]

        # Línea de conteo
        cv2.line(out, (line_x, 0), (line_x, h), LINE_COLOR_BGR, LINE_THICKNESS)
        cv2.arrowedLine(out, (line_x - 40, 20), (line_x + 40, 20), (0, 255, 0), 2, tipLength=0.35)
        cv2.arrowedLine(out, (line_x + 40, 45), (line_x - 40, 45), (0, 0, 255), 2, tipLength=0.35)
        cv2.putText(out, "Entrada", (line_x + 5, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        cv2.putText(out, "Salida",  (line_x - 65, 43), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        # Detecciones
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            color = det["color_bgr"]
            label = f"{det['label']} #{det['track_id']} {det['confianza']:.2f}"

            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            cv2.circle(out, det["centro"], 4, color, -1)

            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            bg_y1 = max(y1 - th - 8, 0)
            cv2.rectangle(out, (x1, bg_y1), (x1 + tw + 4, y1), color, -1)
            cv2.putText(out, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        return out

    @property
    def ready(self) -> bool:
        return self.model is not None
