# -*- coding: utf-8 -*-
"""
Archivo de configuración para la aplicación de conteo bidireccional.
Contiene todas las constantes y parámetros configurables del sistema.
"""

# =============================================================================
# CONFIGURACIÓN DEL MODELO YOLO
# =============================================================================
YOLO_MODEL_PATH = "yolov8n.pt"  # Modelo base, cambiar por modelo personalizado si está disponible

# Mapeo de clases del modelo COCO estándar
# NOTA: El modelo YOLOv8n estándar (COCO) detecta:
# - person (clase 0): Se mapea a 'adulto'
# - bicycle (clase 1): Se mapea a 'bicicleta'
# - motorcycle (clase 3): Se puede usar para patinetes eléctricos grandes
# Para detectar patinetes pequeños, niños específicamente, sillas de ruedas, etc.
# se necesita entrenar un modelo personalizado con esas clases.
COCO_CLASSES = {
    0: 'person',
    1: 'bicycle',
    # Clases adicionales se mapearán desde modelo personalizado
}

# Categorías de la aplicación con sus IDs (sin patinete)
# color_bgr: para OpenCV (BGR), color_hex: para Tkinter
CATEGORIAS = {
    'adulto': {'id': 0, 'nombre': 'Adultos', 'color': (255, 255, 255), 'color_hex': '#ffffff'},
    'nino': {'id': 1, 'nombre': 'Niños', 'color': (200, 200, 200), 'color_hex': '#d0d0d0'},
    'bicicleta': {'id': 2, 'nombre': 'Bicicletas', 'color': (160, 160, 160), 'color_hex': '#a0a0a0'},
    'silla_ruedas': {'id': 3, 'nombre': 'Sillas de Ruedas', 'color': (128, 128, 128), 'color_hex': '#808080'},
    'movilidad_reducida': {'id': 4, 'nombre': 'Movilidad Reducida', 'color': (96, 96, 96), 'color_hex': '#606060'},
}

# Mapeo de clases YOLO a categorías de la aplicación
# Ajustar según el modelo utilizado
CLASE_A_CATEGORIA = {
    'person': 'adulto',
    'pedestrian': 'adulto',
    'child': 'nino',
    'children': 'nino',
    'wheelchair': 'silla_ruedas',
    'bicycle': 'bicicleta',
    'bike': 'bicicleta',
    'mobility aid': 'movilidad_reducida',
    'walker': 'movilidad_reducida',
    'crutches': 'movilidad_reducida',
}
# =============================================================================
# CONFIGURACIÓN DE VIDEO
# =============================================================================
CAMERA_INDEX = 0  # Índice de la webcam (0 = cámara principal)
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
FPS_TARGET = 30

# =============================================================================
# CONFIGURACIÓN DE LA LÍNEA DE CONTEO
# =============================================================================
LINEA_POSICION_DEFAULT = 0.5  # Posición relativa (0.0 a 1.0, 0.5 = centro)
LINEA_COLOR = (0, 255, 255)   # Amarillo (BGR)
LINEA_GROSOR = 3
MARGEN_CRUCE = 30  # Píxeles de margen para detectar cruce

# =============================================================================
# CONFIGURACIÓN DEL TRACKER (DeepSort)
# =============================================================================
TRACKER_MAX_AGE = 30  # Frames máximos sin detección antes de eliminar track
TRACKER_N_INIT = 3    # Frames mínimos para confirmar nuevo track
TRACKER_MAX_IOU_DISTANCE = 0.7

# =============================================================================
# CONFIGURACIÓN DE DATOS Y LOGS
# =============================================================================
CSV_FILENAME = "conteo_bidireccional.csv"
SNAPSHOT_INTERVAL = 300  # Segundos entre snapshots (5 minutos)
SNAPSHOT_FOLDER = "snapshots"

# Columnas del archivo CSV
CSV_COLUMNS = [
    'timestamp',
    'latitude',
    'longitude',
    'ubicacion',
    'categoria',
    'direccion',
    'count_izq_der',
    'count_der_izq'
]

# =============================================================================
# CONFIGURACIÓN DE LA INTERFAZ GRÁFICA
# =============================================================================
WINDOW_TITLE = "Sistema de Conteo Bidireccional - YoloConteo"
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 850

# Colores de la interfaz (en formato hexadecimal para Tkinter)
COLOR_FONDO = "#2C3E50"
COLOR_PANEL = "#34495E"
COLOR_TEXTO = "#ECF0F1"
COLOR_BOTON_INICIAR = "#27AE60"
COLOR_BOTON_PAUSAR = "#F39C12"
COLOR_BOTON_REINICIAR = "#E74C3C"
COLOR_BOTON_EXPORTAR = "#3498DB"

# Fuentes
FUENTE_TITULO = ("Helvetica", 14, "bold")
FUENTE_CONTADOR = ("Helvetica", 24, "bold")
FUENTE_LABEL = ("Helvetica", 10)
FUENTE_PEQUENA = ("Helvetica", 8)

# =============================================================================
# CONFIGURACIÓN DE ALERTAS
# =============================================================================
ALERTA_MOVILIDAD_REDUCIDA = True
ALERTA_DURACION = 3  # Segundos que dura la alerta visual
ALERTA_COLOR = "#FF5733"  # Color de alerta
