# -*- coding: utf-8 -*-
"""
main.py — FastAPI: sirve frontend + MJPEG + WebSocket + API REST.

Arrancar:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Acceder desde móvil:
    http://<IP-local>:8000
"""

import asyncio
import json
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel, Field

from config import (
    MJPEG_FPS_DEFAULT, MJPEG_QUALITY_DEFAULT,
    WS_PUSH_INTERVAL, SNAPSHOT_INTERVAL,
)
from counter  import BidirectionalCounter
from detector import YOLODetector
from logger   import DataLogger
from stream   import MJPEGStream

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("main")


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(application: FastAPI):
    _start_pipeline()
    task = asyncio.create_task(_ws_broadcaster())
    yield
    _stop_event.set()
    task.cancel()
    mjpeg.close_camera()


# ── FastAPI ────────────────────────────────────────────────────────────────────
app = FastAPI(title="YoloConteo v2", version="2.0.0", lifespan=lifespan)

BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ── Componentes globales ───────────────────────────────────────────────────────
detector    = YOLODetector()
mjpeg       = MJPEGStream(fps=MJPEG_FPS_DEFAULT, quality=MJPEG_QUALITY_DEFAULT)
data_logger = DataLogger()
ws_clients: list[WebSocket] = []

# Estado de la sesión
_state = {
    "status":       "stopped",   # stopped | running | paused
    "fps":          0.0,
    "line_pos":     0.5,
}
_state_lock = threading.Lock()

counter = BidirectionalCounter(
    on_cross=lambda cat, direction, tid: _on_cross(cat, direction, tid),
)

# ── Callback de cruce ──────────────────────────────────────────────────────────

def _on_cross(categoria: str, direction: str, track_id: int) -> None:
    counts = counter.get_counts()
    data_logger.log_cross(categoria, direction, counts)


# ── Pipeline de video (hilo separado) ─────────────────────────────────────────

_pipeline_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_snapshot_last = time.monotonic()


def _video_pipeline() -> None:
    """Hilo: lee frames, detecta, trackea, anota, actualiza mjpeg."""
    global _snapshot_last

    fps_counter = 0
    fps_last    = time.monotonic()
    _frame_size_synced = False

    while not _stop_event.is_set():
        with _state_lock:
            status = _state["status"]

        if status != "running":
            time.sleep(0.05)
            continue

        if not mjpeg.is_open:
            time.sleep(0.1)
            continue

        frame = mjpeg.read_raw()
        if frame is None:
            time.sleep(0.01)
            continue

        # Sincronizar dimensiones reales del frame con el counter
        if not _frame_size_synced:
            h, w = frame.shape[:2]
            counter.update_frame_size(w, h)
            _frame_size_synced = True
            logger.info(f"Frame size synced: {w}x{h}")

        # Detección + tracking
        detections = detector.track_frame(frame)

        # Conteo
        counter.process(detections)

        # Dibujar anotaciones
        line_x, _ = counter.get_line_position()
        annotated  = detector.draw(frame, detections, line_x)
        mjpeg.put_annotated(annotated)

        # FPS
        fps_counter += 1
        now = time.monotonic()
        if now - fps_last >= 1.0:
            with _state_lock:
                _state["fps"] = round(fps_counter / (now - fps_last), 1)
            fps_counter = 0
            fps_last    = now

        # Snapshot automático
        if now - _snapshot_last >= SNAPSHOT_INTERVAL:
            raw = mjpeg.get_raw_frame()
            if raw is not None:
                data_logger.save_snapshot(raw)
            _snapshot_last = now


def _start_pipeline() -> None:
    global _pipeline_thread, _stop_event
    if _pipeline_thread and _pipeline_thread.is_alive():
        return
    _stop_event.clear()
    _pipeline_thread = threading.Thread(target=_video_pipeline, daemon=True)
    _pipeline_thread.start()


# ── WebSocket broadcaster ─────────────────────────────────────────────────────

async def _ws_broadcaster() -> None:
    """Tarea asyncio: envía estado y contadores a todos los WS conectados."""
    while True:
        await asyncio.sleep(WS_PUSH_INTERVAL)
        if not ws_clients:
            continue

        with _state_lock:
            status = _state["status"]
            fps    = _state["fps"]

        payload = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "fps":       fps,
            "status":    status,
            "location":  data_logger.get_location(),
            "counts":    counter.get_counts(),
            "line_pos":  counter.line_pos,
        }
        msg = json.dumps(payload, ensure_ascii=False)

        dead = []
        for ws in ws_clients:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            ws_clients.remove(ws)



# ── Rutas ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/video_feed")
async def video_feed(fps: int = MJPEG_FPS_DEFAULT, quality: int = MJPEG_QUALITY_DEFAULT):
    fps     = min(max(1, fps), 30)
    quality = min(max(10, quality), 95)
    mjpeg.fps     = fps
    mjpeg.quality = quality
    return StreamingResponse(
        mjpeg.generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/status")
async def api_status():
    with _state_lock:
        st = dict(_state)
    return {**st, "counts": counter.get_counts(), "location": data_logger.get_location()}


# ── Modelos Pydantic ───────────────────────────────────────────────────────────

class StartBody(BaseModel):
    source: str = Field(default="0", description="Webcam index, RTSP URL, or file path")


class LineBody(BaseModel):
    position: float = Field(..., ge=0.02, le=0.98)


class LocationBody(BaseModel):
    lat:  Optional[float] = None
    lng:  Optional[float] = None
    name: Optional[str]   = ""


class CameraBody(BaseModel):
    source: str


# ── Control endpoints ──────────────────────────────────────────────────────────

@app.post("/api/start")
async def api_start(body: StartBody):
    if not mjpeg.is_open or str(body.source) != str(mjpeg._source):
        ok = mjpeg.open_camera(body.source)
        if not ok:
            raise HTTPException(status_code=400, detail=f"No se pudo abrir: {body.source}")

    data_logger.new_session()
    _start_pipeline()

    with _state_lock:
        _state["status"] = "running"

    return {"status": "running"}


@app.post("/api/pause")
async def api_pause():
    with _state_lock:
        if _state["status"] == "running":
            _state["status"] = "paused"
        elif _state["status"] == "paused":
            _state["status"] = "running"
        status = _state["status"]
    return {"status": status}


@app.post("/api/reset")
async def api_reset():
    counter.reset()
    return {"status": "reset"}


@app.post("/api/export")
async def api_export():
    counts = counter.get_counts()
    path   = data_logger.export_summary(counts)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=500, detail="No se pudo generar el resumen")
    return FileResponse(path, filename=os.path.basename(path), media_type="text/csv")


@app.post("/api/stop")
async def api_stop():
    with _state_lock:
        _state["status"] = "stopped"
    mjpeg.close_camera()
    return {"status": "stopped"}


@app.post("/api/line-position")
async def api_line_position(body: LineBody):
    counter.set_line_position(body.position)
    with _state_lock:
        _state["line_pos"] = body.position
    return {"line_pos": body.position}


@app.post("/api/location")
async def api_location(body: LocationBody):
    if body.lat is not None and body.lng is not None:
        data_logger.set_location(body.lat, body.lng, body.name or "")
    elif body.name:
        data_logger.set_location_name(body.name)
    return data_logger.get_location()


@app.post("/api/camera")
async def api_camera(body: CameraBody):
    was_running = False
    with _state_lock:
        was_running = _state["status"] == "running"
        _state["status"] = "stopped"

    mjpeg.close_camera()
    ok = mjpeg.open_camera(body.source)
    if not ok:
        raise HTTPException(status_code=400, detail=f"No se pudo abrir: {body.source}")

    if was_running:
        with _state_lock:
            _state["status"] = "running"

    return {"source": body.source, "status": _state["status"]}


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.append(ws)
    try:
        while True:
            # Mantener el socket vivo recibiendo pings (o cualquier mensaje)
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if ws in ws_clients:
            ws_clients.remove(ws)
