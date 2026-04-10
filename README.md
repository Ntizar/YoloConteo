# YoloConteo

<div align="center">

![YOLOv8](https://img.shields.io/badge/YOLOv8n-ONNX-purple)
![WebGPU](https://img.shields.io/badge/WebGPU-Acelerado-orange)
![License](https://img.shields.io/badge/License-AGPL--3.0-blue)

**Cuenta personas y vehículos en tiempo real desde tu móvil o PC.**
**Abre un enlace, apunta la cámara y listo. Sin instalar nada.**

### [Probar la app en vivo](https://yolo-conteov2.vercel.app)

Creado por **David Antizar**

</div>

---

## ¿Qué es YoloConteo?

YoloConteo es una app web que **detecta y cuenta personas, coches, motos, bicicletas, autobuses y camiones** que cruzan una línea virtual en la imagen de la cámara.

Lo que la hace especial:

- **Funciona 100% en el navegador** — no necesita servidor con GPU ni instalación.
- **Cualquier persona con el enlace puede usarla** desde el móvil o el PC.
- **La IA corre en tu dispositivo** usando la GPU local vía WebGPU (o WASM como fallback).
- **Desplegada en Vercel** — accesible desde cualquier lugar con una URL.

El modelo de detección es [YOLOv8n](https://github.com/ultralytics/ultralytics) convertido a ONNX (~12 MB), que se descarga una vez y queda en caché del navegador.

---

## ¿Cómo funciona?

1. Abres el enlace en Chrome o Edge (móvil o PC).
2. Permites acceso a la cámara.
3. Ajustas la línea de conteo con el slider.
4. La app detecta objetos en tiempo real y cuenta cada cruce en ambas direcciones.
5. Puedes exportar los datos a CSV y geolocalizarte con GPS.

```
Cámara → YOLOv8n (ONNX/WebGPU) → Tracker IoU → Contador bidireccional → Resultados en pantalla
```

| Objeto     | Emoji |
|------------|-------|
| Personas   | 👤    |
| Bicicletas | 🚲    |
| Coches     | 🚗    |
| Motos      | 🏍️    |
| Autobuses  | 🚌    |
| Camiones   | 🚛    |

---

## Rendimiento

| Backend | FPS esperados | Requisito |
|---------|--------------|-----------|
| **WebGPU** | 20-40+ fps | Chrome/Edge 113+ |
| **WASM** (fallback) | 5-15 fps | Cualquier navegador moderno |

En móvil se optimiza automáticamente saltando frames de inferencia para mantener fluidez.

---

## Ejecutar en local

### Windows

```
doble clic en iniciar.bat
```

### Cualquier SO

```bash
python start.py
```

### Servidor manual

```bash
python web/serve.py       # Puerto 8000
python web/serve.py 3000  # Puerto personalizado
```

Abre `http://localhost:8000` en Chrome o Edge.

---

## Despliegue en producción

La carpeta `web/` es completamente autocontenida (HTML + JS + CSS + modelo ONNX). Sirve como sitio estático en cualquier hosting:

- **Vercel** (usado actualmente): conecta el repo, directorio de publicación `web/`, sin build command.
- **Netlify**: mismo proceso que Vercel.
- **GitHub Pages**: `git subtree push --prefix web origin gh-pages`

> HTTPS es obligatorio en producción para que funcionen la cámara y el GPS.

---

## Estructura del proyecto

```
YoloConteo/
├── web/                    # ★ App web — despliega esta carpeta
│   ├── index.html          #   Interfaz (Ntizar Design System)
│   ├── detector.js         #   YOLOv8n inferencia ONNX (WebGPU/WASM)
│   ├── tracker.js          #   Tracking por IoU
│   ├── counter.js          #   Conteo bidireccional por cruce de línea
│   ├── app.js              #   Orquestación: cámara, UI, GPS, mapa, CSV
│   ├── ntizar.css          #   Estilos
│   ├── yolov8n.onnx        #   Modelo YOLOv8n (~12 MB)
│   └── serve.py            #   Servidor local de desarrollo
├── export_model.py         # Exporta yolov8n.pt → web/yolov8n.onnx
├── iniciar.bat             # Lanzador rápido Windows
├── start.py                # Lanzador cross-platform
├── test_counter.py         # Tests unitarios
└── test_api.py             # Tests de integración
```

---

## Licencia

Este proyecto está licenciado bajo **GNU Affero General Public License v3.0 (AGPL-3.0)**.

Esta licencia se aplica porque YoloConteo utiliza [YOLOv8 de Ultralytics](https://github.com/ultralytics/ultralytics), que se distribuye bajo AGPL-3.0.

### ¿Qué puedes hacer?

- Usar la app libremente para cualquier propósito (personal, académico, comercial).
- Estudiar, modificar y distribuir el código fuente.
- Desplegar tu propia instancia pública.

### ¿Qué obligaciones tienes?

- **Publicar el código fuente** de cualquier versión modificada que distribuyas o despliegues como servicio en red.
- Mantener los avisos de licencia y copyright.
- Licenciar tus modificaciones también bajo AGPL-3.0.

### Uso comercial sin AGPL

Si necesitas usar YOLOv8 en un producto comercial de código cerrado, Ultralytics ofrece una [licencia comercial](https://www.ultralytics.com/license). El resto del código de YoloConteo seguiría bajo AGPL-3.0.

Consulta el archivo [LICENSE](LICENSE) para el texto completo.
