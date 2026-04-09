# YoloConteo v2

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![ONNX](https://img.shields.io/badge/ONNX-Runtime%20Web-005CED?logo=onnx)
![YOLOv8](https://img.shields.io/badge/YOLOv8n-ONNX-purple)
![WebGPU](https://img.shields.io/badge/WebGPU-Acelerado-orange)
![License](https://img.shields.io/badge/License-MIT-green)

**Contador bidireccional de personas y vehículos en tiempo real.**
**100% en navegador — sin servidor de IA — cualquiera con un enlace lo usa.**

### 👉 [Probar la app en vivo](https://yolo-conteo.vercel.app)

Creado por **David Antizar**

</div>

---

## ¿Qué hace?

YoloConteo usa la cámara del usuario (webcam, cámara trasera del móvil), detecta y rastrea objetos con YOLOv8n ejecutado **directamente en el navegador** vía ONNX Runtime Web + WebGPU, y cuenta cuántos cruzan una línea virtual en cada dirección.

**No necesita servidor con GPU.** La inferencia usa la GPU del dispositivo del usuario.

| Categoría  | Clase COCO | Emoji |
|------------|-----------|-------|
| Personas   | 0         | 👤    |
| Bicicletas | 1         | 🚲    |
| Coches     | 2         | 🚗    |
| Motos      | 3         | 🏍️    |
| Autobuses  | 5         | 🚌    |
| Camiones   | 7         | 🚛    |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    NAVEGADOR DEL USUARIO                 │
│                                                          │
│  getUserMedia ──► detector.js ──► tracker.js ──► counter.js
│  (cámara)        (ONNX/WebGPU)   (IoU tracker) (cruce línea)
│                                                          │
│  Canvas ◄──── Anotaciones (bboxes, línea, etiquetas)     │
│  UI ◄──────── Contadores, FPS, mapa, CSV export          │
└─────────────────────────────────────────────────────────┘
```

**Servidor = archivos estáticos** (HTML + JS + CSS + modelo ONNX de 12 MB).
Se puede alojar en GitHub Pages, Netlify, Vercel, o cualquier hosting estático.

### Backends de inferencia (en orden de prioridad)

| Backend | FPS esperados | Requisito |
|---------|--------------|-----------|
| **WebGPU** | 20-40+ fps | Chrome/Edge 113+ |
| **WASM** (fallback) | 5-15 fps | Cualquier navegador moderno |

---

## Uso rápido

### Opción 1: Local (Windows)

```
doble clic en iniciar.bat
```

Exporta el modelo ONNX si es la primera vez y arranca un servidor local.

### Opción 2: Local (cualquier SO)

```bash
python start.py
```

### Opción 3: Servidor manual

```bash
python web/serve.py      # Puerto 8000 por defecto
python web/serve.py 3000 # Puerto personalizado
```

Abre `http://localhost:8000` en **Chrome o Edge** (WebGPU habilitado).

### Opción 4: Desplegar en la web

La carpeta `web/` es completamente autocontenida. Para que cualquiera con un enlace use la app:

1. **GitHub Pages**: Sube la carpeta `web/` como raíz del sitio
2. **Netlify / Vercel**: Apunta a `web/` como directorio de publicación
3. **Cualquier hosting estático**: Sube los archivos de `web/`

> **Importante**: Para GPS y cámara en producción se necesita **HTTPS**.
> GitHub Pages y Netlify proporcionan HTTPS automático.

---

## Flujo de uso

1. **Fuente** — Selecciona "Webcam 0", una IP-cam RTSP o una ruta de archivo MP4.
2. **Iniciar** — Pulsa el botón verde.
3. **Línea** — Ajusta la posición vertical del slider.
4. **GPS** — Pulsa "Obtener ubicación" para geolocalizar la sesión.
5. **Exportar** — Descarga el CSV con todos los cruces registrados.
6. **Detener / Pausar** — Controla el pipeline desde la interfaz.

---

## Testing

### 1. Tests unitarios (sin servidor, sin cámara)

Prueban la lógica de cruce de línea de `counter.py`. No necesitan ningún servicio externo.

```bash
python test_counter.py
# o con pytest:
python -m pytest test_counter.py -v
```

15 casos cubiertos: dirección entrada/salida, prevención de doble conteo, reset, callbacks, clamping de línea, categorías desconocidas.

---

### 2. Tests de integración (necesitan servidor arrancado)

Prueban todos los endpoints REST y el WebSocket contra un servidor real.

```bash
# Terminal 1 — arranca el servidor
iniciar.bat

# Terminal 2 — lanza los tests
python test_api.py

# Contra otra máquina en red local:
python test_api.py --host http://192.168.1.50:8000
```

Endpoints cubiertos: `/`, `/static/`, `/api/status`, `/api/line-position`, `/api/location`, `/api/camera` (fuente inválida → 400), `/api/reset`, `/api/pause`, `/ws`, `/api/export`.

---

### 3. Test con vídeo MP4 (sin cámara física)

Coloca un `.mp4` en la carpeta del proyecto y ejecuta:

```bash
test_video.bat                    # detecta el primer .mp4 automáticamente
test_video.bat C:\ruta\video.mp4  # ruta explícita
```

El servidor arranca con instrucciones en pantalla. En la UI escribe la ruta del vídeo en el campo "URL personalizada" y pulsa Iniciar.

---

## API

| Método | Endpoint             | Descripción                                 |
|--------|----------------------|---------------------------------------------|
| GET    | `/`                  | Interfaz web                                |
| GET    | `/video_feed`        | Stream MJPEG                                |
| WS     | `/ws`                | Conteos en tiempo real (JSON cada 500 ms)   |
| GET    | `/api/status`        | Estado del pipeline y contadores            |
| POST   | `/api/start`         | Inicia con `{"source": "0"}` (cam/rtsp/mp4) |
| POST   | `/api/pause`         | Pausa / reanuda                             |
| POST   | `/api/stop`          | Detiene y libera la cámara                  |
| POST   | `/api/reset`         | Reinicia contadores sin detener stream      |
| POST   | `/api/export`        | Descarga CSV de la sesión                   |
| POST   | `/api/line-position` | `{"position": 0.5}` — mueve la línea        |
| POST   | `/api/location`      | `{"lat": …, "lng": …, "name": …}` — GPS    |
| POST   | `/api/camera`        | Cambia parámetros de stream en caliente     |

---

## Formato CSV

```
fecha, hora, tipo, direccion, total_tipo, total_dir0, total_dir1,
total_sesion, ubicacion, latitude, longitude, sesion_id
```

Cada fila representa un evento de cruce. Los archivos se guardan en:

```
datos/
  <Nombre_lat_lon_fecha>/
    registros_HHMMSS.csv
```

---

## Estructura del proyecto

```
YoloConteo/
├── web/                    # ★ App web autocontenida (deploy esto)
│   ├── index.html          #   UI principal (Ntizar Design System)
│   ├── detector.js         #   YOLOv8n ONNX inference (WebGPU/WASM)
│   ├── tracker.js          #   Tracker IoU simple
│   ├── counter.js          #   Contador bidireccional de cruce de línea
│   ├── app.js              #   Orquestación, cámara, UI, GPS, mapa
│   ├── ntizar.css          #   Ntizar Design System v2.0.0
│   ├── yolov8n.onnx        #   Modelo YOLOv8n exportado (12 MB)
│   └── serve.py            #   Servidor local con headers WebGPU
├── iniciar.bat             # Lanzador Windows (exporta modelo + servidor)
├── start.py                # Lanzador cross-platform
├── export_model.py         # Exporta yolov8n.pt → web/yolov8n.onnx
├── yolov8n.pt              # Modelo PyTorch original (para exportar)
├── main.py                 # [Legacy] FastAPI server-side
├── detector.py             # [Legacy] Detección server-side
├── counter.py              # [Legacy] Contador server-side
├── stream.py               # [Legacy] MJPEG server-side
├── logger.py               # [Legacy] CSV logger server-side
├── config.py               # [Legacy] Configuración server-side
├── requirements.txt        # [Legacy] Dependencias server-side
├── test_counter.py         # Tests unitarios
└── test_api.py             # Tests de integración
```

---

## Notas de diseño

- **Client-side inference**: Todo corre en el navegador. El servidor solo sirve archivos estáticos.
- **WebGPU → WASM fallback**: Si el navegador soporta WebGPU, la inferencia usa la GPU del dispositivo (20-40 fps). Si no, cae a WASM (~5-15 fps).
- **Tracker IoU**: Reemplaza ByteTrack server-side. Más simple, cero dependencias, suficiente para conteo.
- **Solo 6 clases COCO** fiables: se descartan clases con alta tasa de falsos positivos.
- **GPS + Mapa Leaflet**: Geolocalización del navegador + mapa interactivo con reverse geocoding.
- **Modelo ONNX de 12 MB**: Se descarga una sola vez y el navegador lo cachea.

---

## Despliegue en producción

### GitHub Pages (gratuito)

```bash
# 1. Asegúrate de tener web/yolov8n.onnx (ejecuta export_model.py)
# 2. Sube la carpeta web/ como rama gh-pages:
git subtree push --prefix web origin gh-pages
```

### Netlify / Vercel

1. Conecta tu repositorio
2. Directorio de publicación: `web/`
3. Sin build command (archivos estáticos)

> **HTTPS obligatorio** en producción para que funcionen `getUserMedia` (cámara) y `geolocation` (GPS).

---

## Licencia

MIT
