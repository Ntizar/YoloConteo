# YoloConteo - Sistema de Conteo Bidireccional

## 📋 Descripción

Sistema de conteo bidireccional de personas y vehículos de movilidad personal con interfaz gráfica desarrollado en Python. Utiliza YOLO para detección de objetos y DeepSort para tracking, permitiendo contar el paso de personas y vehículos en ambas direcciones a través de una línea virtual.

## 🎯 Características

### Detección y Conteo
- **6 categorías de detección:**
  - 👤 Adultos (pedestrian/person)
  - 👶 Niños (children)
  - ♿ Sillas de ruedas (wheelchair)
  - 🚲 Bicicletas (bicycle)
  - 🛴 Patinetes (scooter/e-scooter)
  - 🦽 Personas con movilidad reducida (mobility aids)

- **Conteo bidireccional:**
  - Línea vertical configurable en el centro de la pantalla
  - Contador separado para cada categoría en ambas direcciones
  - Tracking con IDs únicos para evitar doble conteo

### Registro de Datos
- Timestamp y geolocalización GPS automática
- Archivo CSV con todos los cruces registrados
- Exportación de resúmenes personalizados
- Snapshots automáticos cada 5 minutos

### Interfaz Gráfica
- Feed de video en tiempo real con bounding boxes coloreados
- Panel de contadores actualizado en tiempo real
- Controles intuitivos (Iniciar, Pausar, Reiniciar, Exportar)
- Slider para ajustar posición de línea de conteo
- Display de coordenadas GPS y timestamp
- Contador de FPS en pantalla
- Alertas visuales para personas con movilidad reducida

## 📁 Estructura del Proyecto

```
YoloConteo/
├── main.py                  # Archivo principal de la aplicación
├── config.py                # Configuración y constantes
├── detector_yolo.py         # Módulo de detección YOLO
├── bidirectional_counter.py # Módulo de conteo bidireccional
├── data_logger.py           # Módulo de registro de datos
├── gui.py                   # Interfaz gráfica con Tkinter
├── requirements.txt         # Dependencias del proyecto
├── README.md               # Este archivo
├── snapshots/              # Carpeta de capturas automáticas
└── *.csv                   # Archivos de datos generados
```

## 🔧 Requisitos del Sistema

- Python 3.8 o superior
- Webcam funcional
- Conexión a Internet (para obtener GPS inicial)
- Windows/Linux/macOS

## 📦 Instalación

### 1. Clonar o descargar el proyecto

```bash
cd YoloConteo
```

### 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Instalar PyTorch (según tu sistema)

**Para CPU:**
```bash
pip install torch torchvision
```

**Para GPU NVIDIA (CUDA 11.8):**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 5. Descargar modelo YOLO

El modelo se descargará automáticamente la primera vez que ejecutes la aplicación. Por defecto usa `yolov8n.pt` (YOLO v8 nano).

## 🚀 Uso

### Ejecutar la aplicación

```bash
python main.py
```

### Controles de la interfaz

| Botón | Función |
|-------|---------|
| **▶ Iniciar Conteo** | Inicia la captura de video y el conteo |
| **⏸ Pausar** | Pausa/reanuda el conteo |
| **🔄 Reiniciar Contadores** | Pone todos los contadores a cero |
| **💾 Exportar Datos** | Guarda un resumen CSV |

### Ajustes

- **Posición de Línea:** Usa el slider para mover la línea de conteo
- **Umbral de Confianza:** Ajusta la sensibilidad de detección
- **Ubicación:** Escribe manualmente el nombre del lugar

## 📊 Formato de Datos

### Archivo de registros (conteo_bidireccional.csv)

| Columna | Descripción |
|---------|-------------|
| timestamp | Fecha y hora ISO 8601 |
| fecha | Fecha YYYY-MM-DD |
| hora | Hora HH:MM:SS |
| latitude | Latitud GPS |
| longitude | Longitud GPS |
| ubicacion | Nombre del lugar |
| categoria | Tipo de objeto detectado |
| direccion | Izq→Der o Der→Izq |
| count_izq_der | Total acumulado izq→der |
| count_der_izq | Total acumulado der→izq |
| total_categoria | Total de la categoría |

## ⚙️ Configuración Avanzada

Edita `config.py` para personalizar:

```python
# Modelo YOLO
YOLO_MODEL_PATH = "yolov8n.pt"  # Cambiar por modelo personalizado

# Cámara
CAMERA_INDEX = 0  # Índice de la webcam
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480

# Línea de conteo
LINEA_POSICION_DEFAULT = 0.5  # 0.0 a 1.0
LINEA_COLOR = (0, 255, 255)   # Amarillo (BGR)

# Snapshots
SNAPSHOT_INTERVAL = 300  # Segundos (5 minutos)
```

## 🎨 Códigos de Color

| Categoría | Color |
|-----------|-------|
| Adultos | 🟢 Verde |
| Niños | 🔵 Azul claro |
| Sillas de ruedas | 🟣 Morado |
| Bicicletas | 🟠 Naranja |
| Patinetes | 🔴 Rojo |
| Movilidad reducida | 🟤 Púrpura oscuro |

## 🔍 Uso de Modelo Personalizado

Para detectar todas las categorías específicas (niños, sillas de ruedas, patinetes), necesitarás un modelo personalizado:

### Opción 1: Roboflow Universe
1. Busca un modelo entrenado en [Roboflow Universe](https://universe.roboflow.com/)
2. Descarga el modelo en formato YOLO
3. Actualiza `YOLO_MODEL_PATH` en `config.py`

### Opción 2: Entrenar modelo personalizado
1. Prepara un dataset anotado con las categorías deseadas
2. Entrena usando Ultralytics:
```bash
yolo train model=yolov8n.pt data=tu_dataset.yaml epochs=100
```

## ⚠️ Limitaciones

- El modelo COCO estándar solo detecta "person" y "bicycle"
- Para diferenciación niño/adulto se usa heurística por tamaño
- Precisión GPS depende de la conexión a Internet
- El rendimiento varía según el hardware disponible

## 🐛 Solución de Problemas

### La webcam no se detecta
- Verifica que no esté en uso por otra aplicación
- Prueba con diferentes valores de `CAMERA_INDEX` (0, 1, 2...)

### Bajo FPS
- Reduce la resolución de video
- Usa un modelo más ligero (yolov8n)
- Desactiva DeepSort si no es necesario

### Error de GPU/CUDA
- Verifica que tengas los drivers NVIDIA actualizados
- Reinstala PyTorch con soporte CUDA

## 📄 Licencia

Este proyecto es de código abierto. Siéntete libre de usar, modificar y distribuir.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request.

---

**Desarrollado con ❤️ usando Python, YOLO y Tkinter**
