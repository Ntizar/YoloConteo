/**
 * detector.js — YOLOv8n inference via ONNX Runtime Web (WebGPU → WASM fallback)
 *
 * Ejecuta el modelo YOLOv8n.onnx directamente en el navegador del usuario,
 * aprovechando la GPU local vía WebGPU o, como fallback, WASM.
 *
 * Clases COCO detectadas: personas, bicicletas, coches, motos, autobuses, camiones
 */

'use strict';

const MODEL_INPUT_SIZE = 640;
const CONF_THRESHOLD   = 0.25;
const IOU_THRESHOLD    = 0.5;
const ORT_VERSION      = '1.22.0';

/** Mapa de clases COCO que nos interesan (6 de 80) */
const COCO_CLASSES = {
  0: { key: 'persons',     label: 'Personas',   emoji: '👤', color: '#00ff00' },
  1: { key: 'bicycles',    label: 'Bicicletas', emoji: '🚲', color: '#00a5ff' },
  2: { key: 'cars',        label: 'Coches',     emoji: '🚗', color: '#00c8ff' },
  3: { key: 'motorcycles', label: 'Motos',      emoji: '🏍️', color: '#ff6400' },
  5: { key: 'buses',       label: 'Autobuses',  emoji: '🚌', color: '#ff0000' },
  7: { key: 'trucks',      label: 'Camiones',   emoji: '🚛', color: '#008cff' },
};

const VALID_CLASS_IDS = new Set(Object.keys(COCO_CLASSES).map(Number));


class Detector {

  constructor() {
    this.session    = null;
    this.ready      = false;
    this.backend    = 'none';
    this._outputName = 'output0';  // Se descubre al cargar
    this._debugOnce  = true;        // Log de debug solo en la primera detección

    // Canvas de 640×640 para resize previo a la inferencia
    this._offCanvas = null;
    this._offCtx    = null;

    // Letterbox state (updated per-detect call)
    this._lbScale   = 1;
    this._lbOffsetX = 0;
    this._lbOffsetY = 0;
  }

  /* ── Inicialización ─────────────────────────────────────────────────── */

  /**
   * Carga el modelo ONNX. Intenta WebGPU primero; si falla, usa WASM.
   * @param {string}   modelUrl   Ruta al archivo .onnx
   * @param {Function} onProgress Callback con mensaje de progreso
   */
  async init(modelUrl, onProgress) {
    // Rutas para los archivos .wasm del runtime (pinned a la misma versión que el JS)
    ort.env.wasm.wasmPaths = `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;

    const backends = ['webgpu', 'wasm'];

    for (const ep of backends) {
      try {
        if (onProgress) onProgress(`Cargando modelo (${ep.toUpperCase()})…`);
        this.session = await ort.InferenceSession.create(modelUrl, {
          executionProviders: [ep],
        });
        this.backend = ep;
        this.ready   = true;

        // Descubrir nombre del tensor de salida
        const outNames = this.session.outputNames;
        if (outNames && outNames.length > 0) this._outputName = outNames[0];
        console.log(`[Detector] Output tensor: "${this._outputName}"`);

        // Canvas regular (oculto) — más compatible con drawImage(video) que OffscreenCanvas
        this._offCanvas = document.createElement('canvas');
        this._offCanvas.width  = MODEL_INPUT_SIZE;
        this._offCanvas.height = MODEL_INPUT_SIZE;
        this._offCtx = this._offCanvas.getContext('2d', { willReadFrequently: true });

        if (onProgress) onProgress(`Modelo listo ✓ (${ep.toUpperCase()})`);
        console.log(`[Detector] Backend: ${ep}`);
        return;
      } catch (e) {
        console.warn(`[Detector] ${ep} no disponible:`, e.message);
      }
    }

    throw new Error('No se pudo inicializar ONNX Runtime. Necesitas Chrome/Edge actualizado.');
  }

  /* ── Detección ──────────────────────────────────────────────────────── */

  /**
   * Ejecuta detección sobre un elemento de vídeo.
   * @param {HTMLVideoElement} video   Elemento <video> con la cámara
   * @param {number}           origW   Ancho real del vídeo
   * @param {number}           origH   Alto real del vídeo
   * @returns {Array<Object>}  Detecciones filtradas y con NMS
   */
  async detect(video, origW, origH) {
    if (!this.ready) return [];

    const input  = this._preprocess(video);
    const tensor = new ort.Tensor('float32', input, [1, 3, MODEL_INPUT_SIZE, MODEL_INPUT_SIZE]);

    const feeds = {};
    feeds[this.session.inputNames[0]] = tensor;
    const result = await this.session.run(feeds);
    const output = result[this._outputName];

    if (!output) {
      console.error('[Detector] No output tensor found. Keys:', Object.keys(result));
      return [];
    }

    // Debug: log en la primera detección
    if (this._debugOnce) {
      this._debugOnce = false;
      const raw = output.data;
      const nDet = output.dims[2];
      let maxS = 0;
      for (let i = 0; i < nDet; i++) {
        for (let c = 4; c < 84; c++) {
          const s = raw[c * nDet + i];
          if (s > maxS) maxS = s;
        }
      }
      console.log(`[Detector] Output shape: [${output.dims}], max class score: ${maxS.toFixed(4)}, pixels sample: [${input[0].toFixed(3)}, ${input[1].toFixed(3)}, ${input[2].toFixed(3)}]`);
    }

    return this._postprocess(output, origW, origH);
  }

  /* ── Preprocesado ───────────────────────────────────────────────────── */

  /**
   * Letterbox: dibuja el vídeo centrado en un canvas 640×640 manteniendo
   * la proporción original, rellena con gris (114). Convierte RGBA uint8
   * a RGB float32 en formato NCHW (lo que espera YOLO).
   */
  _preprocess(video) {
    const vw = video.videoWidth  || MODEL_INPUT_SIZE;
    const vh = video.videoHeight || MODEL_INPUT_SIZE;

    // Letterbox: escala manteniendo aspect ratio
    const scale = Math.min(MODEL_INPUT_SIZE / vw, MODEL_INPUT_SIZE / vh);
    const nw = Math.round(vw * scale);
    const nh = Math.round(vh * scale);
    const dx = Math.round((MODEL_INPUT_SIZE - nw) / 2);
    const dy = Math.round((MODEL_INPUT_SIZE - nh) / 2);

    // Guardar para postprocesado
    this._lbScale   = scale;
    this._lbOffsetX = dx;
    this._lbOffsetY = dy;

    // Rellenar con gris 114 y dibujar vídeo centrado
    this._offCtx.fillStyle = 'rgb(114,114,114)';
    this._offCtx.fillRect(0, 0, MODEL_INPUT_SIZE, MODEL_INPUT_SIZE);
    this._offCtx.drawImage(video, dx, dy, nw, nh);

    const { data } = this._offCtx.getImageData(0, 0, MODEL_INPUT_SIZE, MODEL_INPUT_SIZE);

    const size  = MODEL_INPUT_SIZE * MODEL_INPUT_SIZE;
    const float = new Float32Array(3 * size);

    for (let i = 0; i < size; i++) {
      const px = i * 4;
      float[i]            = data[px]     / 255;   // R
      float[size + i]     = data[px + 1] / 255;   // G
      float[2 * size + i] = data[px + 2] / 255;   // B
    }
    return float;
  }

  /* ── Postprocesado ──────────────────────────────────────────────────── */

  /**
   * Convierte la salida del modelo [1, 84, 8400] en detecciones útiles.
   * Formato salida YOLO: 84 = 4 (cx,cy,w,h) + 80 (class scores)
   *                      8400 = anchors por defecto para input 640
   */
  _postprocess(output, origW, origH) {
    const raw  = output.data;
    const dims = output.dims;   // [1, 84, 8400]
    const nCh  = dims[1];       // 84
    const nDet = dims[2];       // 8400

    // Invertir letterbox: model coords → original coords
    const lbScale = this._lbScale;
    const lbDx    = this._lbOffsetX;
    const lbDy    = this._lbOffsetY;

    const detections = [];

    for (let i = 0; i < nDet; i++) {
      // Encontrar clase con mayor score
      let maxScore = 0;
      let maxClass = -1;

      for (let c = 4; c < nCh; c++) {
        const score = raw[c * nDet + i];
        if (score > maxScore) {
          maxScore = score;
          maxClass = c - 4;
        }
      }

      if (maxScore < CONF_THRESHOLD) continue;
      if (!VALID_CLASS_IDS.has(maxClass)) continue;

      // Bbox en coords del modelo (640×640 letterbox)
      const rawCx = raw[0 * nDet + i];
      const rawCy = raw[1 * nDet + i];
      const rawW  = raw[2 * nDet + i];
      const rawH  = raw[3 * nDet + i];

      // Revertir letterbox → coords originales del vídeo
      const cx = (rawCx - lbDx) / lbScale;
      const cy = (rawCy - lbDy) / lbScale;
      const bw = rawW / lbScale;
      const bh = rawH / lbScale;

      const classInfo = COCO_CLASSES[maxClass];

      detections.push({
        bbox:       [cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2],
        center:     [cx, cy],
        confidence: maxScore,
        classId:    maxClass,
        categoria:  classInfo.key,
        label:      classInfo.label,
        emoji:      classInfo.emoji,
        color:      classInfo.color,
      });
    }

    return this._nms(detections);
  }

  /* ── NMS (Non-Maximum Suppression) ──────────────────────────────────── */

  _nms(detections) {
    detections.sort((a, b) => b.confidence - a.confidence);

    const keep       = [];
    const suppressed = new Set();

    for (let i = 0; i < detections.length; i++) {
      if (suppressed.has(i)) continue;
      keep.push(detections[i]);

      for (let j = i + 1; j < detections.length; j++) {
        if (suppressed.has(j)) continue;
        if (detections[i].classId === detections[j].classId &&
            this._iou(detections[i].bbox, detections[j].bbox) > IOU_THRESHOLD) {
          suppressed.add(j);
        }
      }
    }
    return keep;
  }

  /** IoU entre dos bboxes [x1,y1,x2,y2] */
  _iou(a, b) {
    const x1 = Math.max(a[0], b[0]);
    const y1 = Math.max(a[1], b[1]);
    const x2 = Math.min(a[2], b[2]);
    const y2 = Math.min(a[3], b[3]);

    const inter = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
    const areaA = (a[2] - a[0]) * (a[3] - a[1]);
    const areaB = (b[2] - b[0]) * (b[3] - b[1]);

    return inter / (areaA + areaB - inter + 1e-6);
  }
}
