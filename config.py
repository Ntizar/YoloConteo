# -*- coding: utf-8 -*-
"""
Configuración centralizada — YoloConteo v2 Web App
Categorías: 6 clases COCO fiables (sin heurísticas rotas)
"""

# ── Modelo YOLO ────────────────────────────────────────────────────────────────
YOLO_MODEL_PATH = "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.5
TRACKER = "bytetrack.yaml"   # Incluido en Ultralytics, sin dependencias extra

# ── Categorías detectables (solo COCO estándar fiables) ───────────────────────
# IDs COCO: 0=person, 1=bicycle, 2=car, 3=motorcycle, 5=bus, 7=truck
COCO_CLASSES = {
    0: {"key": "persons",     "label": "Personas",   "emoji": "👤", "color_bgr": (0, 255, 0)},
    1: {"key": "bicycles",    "label": "Bicicletas",  "emoji": "🚲", "color_bgr": (0, 165, 255)},
    2: {"key": "cars",        "label": "Coches",      "emoji": "🚗", "color_bgr": (0, 200, 255)},
    3: {"key": "motorcycles", "label": "Motos",       "emoji": "🏍️", "color_bgr": (255, 100, 0)},
    5: {"key": "buses",       "label": "Autobuses",   "emoji": "🚌", "color_bgr": (0, 0, 255)},
    7: {"key": "trucks",      "label": "Camiones",    "emoji": "🚛", "color_bgr": (0, 140, 255)},
}

# Acceso rápido: key → config
CATEGORY_KEYS = [cls["key"] for cls in COCO_CLASSES.values()]

# ── Video / streaming ──────────────────────────────────────────────────────────
VIDEO_WIDTH  = 640
VIDEO_HEIGHT = 480
MJPEG_FPS_DEFAULT     = 15
MJPEG_QUALITY_DEFAULT = 60    # JPEG quality 0-100
MJPEG_FPS_MAX         = 30
MJPEG_QUALITY_MAX     = 95

# ── Línea de conteo ───────────────────────────────────────────────────────────
LINE_POSITION_DEFAULT = 0.5   # 0.0 → 1.0 (fracción del ancho)
LINE_COLOR_BGR = (0, 255, 255)
LINE_THICKNESS = 3
CROSSING_MARGIN = 30          # píxeles de margen para resetear la bandera

# ── CSV ────────────────────────────────────────────────────────────────────────
CSV_BASE_DIR = "datos"
CSV_COLUMNS = [
    "fecha", "hora", "tipo", "direccion",
    "total_tipo", "total_dir0", "total_dir1", "total_sesion",
    "ubicacion", "latitude", "longitude", "sesion_id",
]

# ── Snapshots ─────────────────────────────────────────────────────────────────
SNAPSHOT_INTERVAL = 300       # segundos
SNAPSHOT_FOLDER   = "snapshots"

# ── WebSocket ─────────────────────────────────────────────────────────────────
WS_PUSH_INTERVAL = 0.5        # segundos entre mensajes al cliente
