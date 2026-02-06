# 🛠️ Guía de Desarrollo - YoloConteo

> **Documentación técnica para agentes y desarrolladores**  
> Sistema de Conteo Bidireccional de Personas y Vehículos de Movilidad Personal

---

## 📋 Índice

1. [Arquitectura General](#-arquitectura-general)
2. [Flujo de Datos](#-flujo-de-datos)
3. [Módulos y Responsabilidades](#-módulos-y-responsabilidades)
4. [Guía de Modificaciones](#-guía-de-modificaciones)
5. [Patrones y Convenciones](#-patrones-y-convenciones)
6. [Dependencias entre Módulos](#-dependencias-entre-módulos)
7. [Configuración](#-configuración)
8. [Troubleshooting](#-troubleshooting)

---

## 🏗️ Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                 │
│                    (YoloConteoApp)                              │
│         Orquestador principal - Integra todos los módulos       │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────────┐
│ detector_yolo │   │ bidirectional_  │   │    data_logger      │
│     .py       │   │   counter.py    │   │       .py           │
│               │   │                 │   │                     │
│ Detección     │   │ Tracking +      │   │ Guardado CSV +      │
│ YOLO v8       │   │ Conteo cruces   │   │ GPS + Snapshots     │
└───────────────┘   └─────────────────┘   └─────────────────────┘
        │                     │                     │
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   gui_nueva.py  │
                    │    (GUI)        │
                    │                 │
                    │ Interfaz Tkinter│
                    │ Dashboard       │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ selector_       │
                    │ ubicacion.py    │
                    │ (Opcional)      │
                    │ Mapa interactivo│
                    └─────────────────┘
```

---

## 🔄 Flujo de Datos

### Flujo Principal de Procesamiento

```
1. CAPTURA
   Webcam → cv2.VideoCapture → Frame (numpy array BGR)
                                    │
2. DETECCIÓN                        │
   Frame ──────────────────────────►│
        DetectorYOLO.detectar()     │
        └── YOLO v8 inferencia      │
        └── Mapeo clases → categorías
        └── Return: List[Dict] detecciones
                                    │
3. TRACKING + CONTEO                ▼
   Detecciones ─────────────────────►
        BidirectionalCounter.procesar_detecciones()
        └── DeepSort tracking (asigna IDs)
        └── Verificación cruce de línea
        └── Actualización contadores
        └── Callback: _on_cruce_detectado()
                                    │
4. REGISTRO                         ▼
   Cruce detectado ─────────────────►
        DataLogger.registrar_cruce()
        └── Escribir CSV
        └── Snapshot si corresponde
                                    │
5. VISUALIZACIÓN                    ▼
   Frame procesado ─────────────────►
        GUI.actualizar_frame()
        └── Dibujar bounding boxes
        └── Actualizar contadores
        └── Mostrar FPS/timestamp
```

### Estructura de una Detección

```python
deteccion = {
    'bbox': [x1, y1, x2, y2],    # Coordenadas bounding box
    'categoria': 'adulto',        # Categoría mapeada
    'confianza': 0.85,            # Nivel de confianza
    'clase_original': 'person',   # Clase YOLO original
    'centro': (cx, cy),           # Centro del bbox
    'ancho': 100,                 # Ancho del bbox
    'alto': 200,                  # Alto del bbox
    'track_id': 5                 # ID de tracking (después de procesar)
}
```

---

## 📁 Módulos y Responsabilidades

### 1. `config.py` - Configuración Central

**Propósito:** Almacena TODAS las constantes y parámetros configurables.

| Sección | Variables Clave | Descripción |
|---------|-----------------|-------------|
| **Modelo YOLO** | `YOLO_MODEL_PATH` | Ruta al modelo .pt |
| **Categorías** | `CATEGORIAS`, `CLASE_A_CATEGORIA` | Definición y mapeo de categorías |
| **Video** | `CAMERA_INDEX`, `VIDEO_WIDTH/HEIGHT` | Configuración de cámara |
| **Línea** | `LINEA_POSICION_DEFAULT`, `MARGEN_CRUCE` | Parámetros de la línea de conteo |
| **Tracker** | `TRACKER_MAX_AGE`, `TRACKER_N_INIT` | Configuración DeepSort |
| **Datos** | `CSV_FILENAME`, `SNAPSHOT_INTERVAL` | Rutas y tiempos de guardado |
| **GUI** | `WINDOW_WIDTH/HEIGHT`, colores | Aspecto visual |

**⚠️ Regla:** Modificar parámetros aquí, NO en los módulos.

---

### 2. `detector_yolo.py` - Detección de Objetos

**Clase principal:** `DetectorYOLO`

```python
class DetectorYOLO:
    """
    Métodos principales:
    - __init__(model_path, confidence_threshold, categorias, clase_a_categoria)
    - detectar(frame) -> List[Dict]           # Detección principal
    - dibujar_detecciones(frame, detecciones) # Dibuja bboxes
    - actualizar_umbral_confianza(umbral)     # Cambia threshold
    - liberar()                               # Libera recursos
    """
```

**Para agregar nuevas categorías:**
1. Agregar en `config.py` → `CATEGORIAS`
2. Agregar mapeo en `config.py` → `CLASE_A_CATEGORIA`
3. El detector las procesará automáticamente

**Para usar modelo personalizado:**
```python
# En config.py
YOLO_MODEL_PATH = "mi_modelo_custom.pt"

# Si el modelo tiene nuevas clases, agregar mapeos:
CLASE_A_CATEGORIA = {
    'mi_nueva_clase': 'nueva_categoria',
    # ...
}
```

---

### 3. `bidirectional_counter.py` - Tracking y Conteo

**Clases principales:**

```python
class Direccion(Enum):
    IZQUIERDA_A_DERECHA = "izq_der"
    DERECHA_A_IZQUIERDA = "der_izq"
    NINGUNA = "ninguna"

@dataclass
class TrackInfo:
    track_id: int
    categoria: str
    ultima_posicion_x: float
    posicion_inicial_x: float
    cruzado: bool
    direccion_cruce: Optional[Direccion]
    # ...

class BidirectionalCounter:
    """
    Métodos principales:
    - procesar_detecciones(detecciones, frame) -> List[Dict]
    - actualizar_posicion_linea(posicion_relativa)
    - obtener_contadores() -> Dict
    - obtener_total_cruces() -> Dict
    - reiniciar_contadores()
    - dibujar_linea_conteo(frame, color, grosor)
    """
```

**Lógica de cruce:**
```
1. Objeto detectado → DeepSort asigna track_id
2. Se registra posición inicial (lado de la línea)
3. Se actualiza posición en cada frame
4. Si cruza la línea (cambia de lado):
   - Se determina dirección (izq→der o der→izq)
   - Se incrementa contador correspondiente
   - Se dispara callback_cruce
   - Se marca como "cruzado" para no contar doble
```

---

### 4. `data_logger.py` - Persistencia de Datos

**Clases principales:**

```python
class DataLogger:
    """
    Métodos principales:
    - registrar_cruce(categoria, direccion, contadores)
    - guardar_snapshot(frame, prefijo)
    - exportar_resumen(contadores, ruta)
    - obtener_coordenadas() -> Tuple[float, float]
    - establecer_ubicacion_manual(nombre)
    - establecer_coordenadas(lat, lon)
    """

class SnapshotScheduler:
    """
    Gestiona capturas automáticas cada X segundos.
    - actualizar_frame(frame)
    - verificar_y_guardar()
    """
```

**Estructura de carpetas generada:**
```
datos/
└── 2026-01-30_40.4165_n3.7026/    # Fecha + Coordenadas
    ├── conteo_102917.csv          # Registro de cruces
    ├── conteo_102949.csv
    └── snapshots/                 # Capturas automáticas
        ├── snapshot_102917.jpg
        └── snapshot_103000.jpg
```

**Formato CSV:**
```csv
timestamp,fecha,hora,latitude,longitude,ubicacion,categoria,direccion,count_izq_der,count_der_izq,total_categoria
```

---

### 5. `gui_nueva.py` - Interfaz Gráfica

**Clase principal:** `GUI`

```python
class GUI:
    """
    Componentes visuales:
    - Video canvas (responsive)
    - Panel de contadores (ContadorCard)
    - Controles (Iniciar, Pausar, Reiniciar, Exportar)
    - Sliders (posición línea, confianza)
    - Display GPS/Ubicación
    
    Callbacks a configurar:
    - callback_iniciar
    - callback_pausar
    - callback_reiniciar
    - callback_exportar
    - callback_cerrar
    - callback_slider_linea
    - callback_slider_confianza
    - callback_cambiar_ubicacion
    """
```

**Para modificar la interfaz:**

| Modificación | Archivo/Método |
|--------------|----------------|
| Colores | `config.py` → `COLOR_FONDO`, `COLOR_PANEL` |
| Dimensiones | `config.py` → `WINDOW_WIDTH`, `WINDOW_HEIGHT` |
| Nuevo botón | `gui_nueva.py` → `_construir_interfaz()` |
| Nueva tarjeta | Crear subclase de `ContadorCard` |
| Nuevo panel | Agregar en `main_container` grid |

---

### 6. `selector_ubicacion.py` - Mapa Interactivo (Opcional)

**Clase principal:** `SelectorUbicacion`

```python
@dataclass
class UbicacionInfo:
    latitud: float
    longitud: float
    direccion: str
    calle: str
    numero: str
    ciudad: str
    codigo_postal: str
    pais: str

class SelectorUbicacion:
    """
    Ventana modal con mapa OpenStreetMap.
    Permite seleccionar ubicación haciendo clic.
    """
```

**Dependencias opcionales:**
- `tkintermapview` - Mapa interactivo
- `geopy` - Geocodificación inversa

---

### 7. `main.py` - Orquestador Principal

**Clase principal:** `YoloConteoApp`

```python
class YoloConteoApp:
    """
    RESPONSABILIDADES:
    1. Inicializar todos los componentes
    2. Configurar callbacks entre módulos
    3. Gestionar ciclo de vida de la aplicación
    4. Bucle principal de video
    5. Coordinar comunicación entre módulos
    
    FLUJO DE INICIALIZACIÓN:
    1. DataLogger (obtiene GPS)
    2. DetectorYOLO (carga modelo)
    3. BidirectionalCounter (inicializa tracker)
    4. SnapshotScheduler
    5. GUI
    6. Configurar callbacks
    
    MÉTODOS CALLBACK PRINCIPALES:
    - _on_cruce_detectado()  # Cuando algo cruza la línea
    - _on_iniciar()          # Botón iniciar
    - _on_pausar()           # Botón pausar
    - _on_reiniciar()        # Botón reiniciar
    - _on_exportar()         # Botón exportar
    - _on_cerrar()           # Detener captura
    - _on_cambio_linea()     # Slider línea
    - _on_cambio_confianza() # Slider confianza
    """
```

---

## 📝 Guía de Modificaciones

### Agregar Nueva Categoría de Detección

```python
# 1. config.py - Agregar categoría
CATEGORIAS = {
    # ... existentes ...
    'carrito_bebe': {
        'id': 6, 
        'nombre': 'Carritos de Bebé', 
        'color': (0, 128, 255),      # BGR para OpenCV
        'color_hex': '#FF8000'        # Hex para Tkinter
    },
}

# 2. config.py - Agregar mapeo de clases YOLO
CLASE_A_CATEGORIA = {
    # ... existentes ...
    'stroller': 'carrito_bebe',
    'baby carriage': 'carrito_bebe',
}

# ¡Listo! El resto se actualiza automáticamente
```

### Modificar Lógica de Conteo

```python
# bidirectional_counter.py

# Para cambiar cómo se detecta un cruce:
def _verificar_cruce_linea(self, track_id: int, ...) -> Optional[Direccion]:
    # Modificar lógica aquí
    pass

# Para cambiar qué hacer cuando hay un cruce:
def _registrar_cruce(self, track_id: int, direccion: Direccion):
    # Agregar lógica adicional aquí
    pass
```

### Agregar Nuevo Control en GUI

```python
# gui_nueva.py → _construir_interfaz()

# Ejemplo: Agregar botón de captura manual
self.btn_captura = tk.Button(
    controls_frame,
    text="📷 Capturar",
    command=self._on_captura_manual,
    bg="#3d5afe",
    fg="white"
)
self.btn_captura.pack(side="left", padx=5)

# Agregar callback
def _on_captura_manual(self):
    if self.callback_captura:
        self.callback_captura()
```

### Cambiar Fuente de Video

```python
# main.py → _inicializar_webcam()

# Para usar archivo de video en vez de webcam:
self.captura = cv2.VideoCapture("video.mp4")

# Para usar stream RTSP:
self.captura = cv2.VideoCapture("rtsp://ip:puerto/stream")

# Para usar URL HTTP:
self.captura = cv2.VideoCapture("http://ip:puerto/video")
```

### Agregar Nuevo Formato de Exportación

```python
# data_logger.py

def exportar_json(self, contadores: Dict, ruta: str) -> Optional[str]:
    """Exporta datos en formato JSON."""
    import json
    datos = {
        'timestamp': datetime.now().isoformat(),
        'ubicacion': {
            'nombre': self.ubicacion_nombre,
            'lat': self.latitude,
            'lon': self.longitude
        },
        'contadores': contadores
    }
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    return ruta
```

---

## 🎯 Patrones y Convenciones

### Convenciones de Código

```python
# Nombres de archivos: snake_case
detector_yolo.py
bidirectional_counter.py

# Clases: PascalCase
class DetectorYOLO:
class BidirectionalCounter:

# Métodos privados: prefijo _
def _procesar_frame(self):
def _inicializar_tracker(self):

# Constantes: MAYUSCULAS_SNAKE
YOLO_MODEL_PATH = "..."
VIDEO_WIDTH = 640

# Type hints obligatorios
def detectar(self, frame: np.ndarray) -> List[Dict]:
```

### Patrón de Callbacks

```python
# Definir callback en clase receptora
class GUI:
    def __init__(self):
        self.callback_iniciar = None
    
    def establecer_callbacks(self, iniciar=None, ...):
        self.callback_iniciar = iniciar

# Configurar en main.py
def _configurar_callbacks(self):
    self.gui.establecer_callbacks(
        iniciar=self._on_iniciar,
        # ...
    )

# Invocar callback cuando corresponda
def _on_boton_iniciar(self):
    if self.callback_iniciar:
        self.callback_iniciar()
```

### Patrón Thread-Safe

```python
# Usar locks para datos compartidos
self.lock_frame = threading.Lock()

# Al escribir
with self.lock_frame:
    self.frame_actual = frame.copy()

# Al leer
with self.lock_frame:
    frame = self.frame_actual.copy() if self.frame_actual is not None else None
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)

# Niveles de uso
logger.debug("Detalles técnicos")      # Solo desarrollo
logger.info("Operaciones normales")     # Flujo normal
logger.warning("Situaciones anómalas")  # Algo inesperado
logger.error("Errores recuperables")    # Fallo que no detiene app
logger.critical("Errores fatales")      # App debe detenerse
```

---

## 🔗 Dependencias entre Módulos

```
config.py ◄───────────────────────────────────────┐
    │                                              │
    │ importa                                      │ importa
    ▼                                              │
detector_yolo.py ◄──────┬──────────────────────────┤
                        │                          │
                        │ importa                  │
                        ▼                          │
bidirectional_counter.py ◄─────────────────────────┤
                        │                          │
                        │ importa                  │
                        ▼                          │
data_logger.py ◄───────────────────────────────────┤
                        │                          │
                        │                          │
selector_ubicacion.py ◄────────────────────────────┤
                        │                          │
                        │ importa                  │
                        ▼                          │
gui_nueva.py ◄──────────┴──────────────────────────┤
                                                   │
                        importa todo               │
                        ▼                          │
main.py ───────────────────────────────────────────┘
```

### Orden de Modificación Recomendado

1. **config.py** - Siempre primero si cambian parámetros
2. **Módulo específico** - El que implementa la funcionalidad
3. **main.py** - Si cambian interfaces o callbacks
4. **gui_nueva.py** - Si hay cambios visuales

---

## ⚙️ Configuración Rápida

### Variables de Entorno Implícitas

```python
# El sistema detecta automáticamente:
- GPU CUDA disponible → usa GPU
- Sin GPU → usa CPU
- DeepSort no instalado → usa tracker simple
- geocoder no disponible → sin GPS automático
- tkintermapview no disponible → sin mapa
```

### Ajustes de Rendimiento

```python
# config.py

# Para equipos lentos:
VIDEO_WIDTH = 480
VIDEO_HEIGHT = 360
FPS_TARGET = 15
YOLO_MODEL_PATH = "yolov8n.pt"  # Modelo nano (más rápido)

# Para equipos potentes:
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
FPS_TARGET = 60
YOLO_MODEL_PATH = "yolov8l.pt"  # Modelo large (más preciso)
```

### Configuración de Detección

```python
# detector_yolo.py → __init__

confidence_threshold = 0.5  # Subir para menos falsos positivos
                            # Bajar para más detecciones

# config.py
MARGEN_CRUCE = 30  # Píxeles de tolerancia para cruce
                   # Mayor = más tolerante a movimiento errático
```

---

## 🔧 Troubleshooting

### Problema: "No se detectan objetos"

```python
# Verificar:
1. ¿Modelo cargado correctamente?
   → Ver logs: "Modelo YOLO cargado correctamente"

2. ¿Threshold muy alto?
   → Bajar confidence_threshold en detector_yolo.py

3. ¿Clases no mapeadas?
   → Verificar CLASE_A_CATEGORIA en config.py
   → Imprimir detecciones raw para ver clases originales
```

### Problema: "Conteo doble"

```python
# Verificar:
1. TRACKER_MAX_AGE muy alto → objeto se pierde y reaparece como nuevo
2. MARGEN_CRUCE muy pequeño → múltiples cruces detectados
3. DeepSort no instalado → tracker simple menos preciso

# Solución típica:
TRACKER_MAX_AGE = 15  # Reducir
MARGEN_CRUCE = 50     # Aumentar
```

### Problema: "Webcam no abre"

```python
# En main.py → _inicializar_webcam():

# Probar diferentes backends:
self.captura = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)  # Windows
self.captura = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_V4L2)   # Linux
self.captura = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_AVFOUNDATION)  # macOS

# Probar diferentes índices:
CAMERA_INDEX = 0  # Cámara principal
CAMERA_INDEX = 1  # Cámara secundaria
```

### Problema: "GUI no responde"

```python
# El procesamiento de video está en hilo separado.
# Si la GUI se congela:

1. Verificar que _bucle_video() tiene sleep(0.01)
2. Verificar que actualizaciones GUI usan root.after()
3. No hacer operaciones pesadas en callbacks de GUI
```

---

## 📚 Referencias Rápidas

### Estructura de Contadores

```python
contadores = {
    'adulto': {'izq_der': 5, 'der_izq': 3},
    'nino': {'izq_der': 2, 'der_izq': 1},
    'silla_ruedas': {'izq_der': 0, 'der_izq': 0},
    'bicicleta': {'izq_der': 1, 'der_izq': 2},
    'patinete': {'izq_der': 3, 'der_izq': 0},
    'movilidad_reducida': {'izq_der': 0, 'der_izq': 1},
}
```

### Colores por Categoría (BGR para OpenCV)

```python
'adulto':            (0, 255, 0)    # Verde
'nino':              (255, 255, 0)  # Cian
'silla_ruedas':      (255, 0, 255)  # Magenta
'bicicleta':         (0, 165, 255)  # Naranja
'patinete':          (0, 0, 255)    # Rojo
'movilidad_reducida': (128, 0, 128) # Púrpura
```

### Comandos Útiles

```bash
# Ejecutar aplicación
python main.py

# Instalar dependencias
pip install -r requirements.txt

# Verificar GPU
python -c "import torch; print(torch.cuda.is_available())"

# Probar modelo YOLO
python -c "from ultralytics import YOLO; m = YOLO('yolov8n.pt'); print(m.names)"
```

---

## ✅ Checklist para Modificaciones

- [ ] ¿Los cambios de configuración están en `config.py`?
- [ ] ¿Se mantienen los type hints?
- [ ] ¿Se agregó logging apropiado?
- [ ] ¿Los callbacks están correctamente conectados?
- [ ] ¿Se manejan las excepciones?
- [ ] ¿Los recursos se liberan correctamente?
- [ ] ¿La GUI se actualiza de forma thread-safe?
- [ ] ¿Se actualizó esta documentación si es necesario?

---

*Última actualización: Enero 2026*
