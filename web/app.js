/**
 * app.js — YoloConteo v2 Web — Aplicación principal
 *
 * Orquesta: cámara → detección ONNX → tracking → conteo → dibujo → UI
 * Todo se ejecuta en el navegador del usuario. Sin servidor.
 */

'use strict';

/* ══════════════════════════════════════════════════════════════════════════════
   Estado global
   ══════════════════════════════════════════════════════════════════════════════ */

const state = {
  running:  false,
  paused:   false,
  fps:      0,
  backend:  'none',
  sourceMode: 'camera',
  selectedVideoFile: null,
  videoObjectUrl: null,
  videoEndedNotified: false,
  previewFrameCanvas: null,
  location: { name: '', lat: null, lng: null },
  sessionId: '',
  crossLog: [],   // Historial de cruces para CSV
};

/* ── Detección de móvil y config adaptativa ───────────────────────────────── */

const IS_MOBILE = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent)
                  || ('ontouchstart' in window && screen.width < 1024);

/**
 * En móvil: inferir cada SKIP_FRAMES frames y reusar detecciones en los
 * frames intermedios. Esto multiplica el FPS visible sin perder tracking.
 * En desktop no se salta ningún frame.
 */
const SKIP_FRAMES = IS_MOBILE ? 3 : 1;

let detector, tracker, counter;
let video, canvas, ctx;
let map, mapMarker;
let _lineDebounce = null;

/* ── Helpers DOM ──────────────────────────────────────────────────────────── */

const $ = (id) => document.getElementById(id);
const show = (el) => { if (el) el.style.display = ''; };
const hide = (el) => { if (el) el.style.display = 'none'; };


/* ══════════════════════════════════════════════════════════════════════════════
   Inicialización
   ══════════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', async () => {
  applyStoredTheme();
  bindEvents();
  await initDetector();
  await enumerateCameras();
  onSourceChange();
  initMap();
});


async function initDetector() {
  const overlay = $('loading-overlay');
  const text    = $('loading-text');

  show(overlay);
  try {
    detector = new Detector();
    tracker  = new Tracker({ maxAge: 20, iouThreshold: 0.25 });
    counter  = new Counter({
      onCross: (cat, dir, trackId) => logCross(cat, dir, trackId),
    });

    await detector.init('yolov8n.onnx', (msg) => {
      if (text) text.textContent = msg;
    });

    state.backend = detector.backend;
    const badge = $('backend-badge');
    if (badge) badge.textContent = detector.backend.toUpperCase();

  } catch (e) {
    if (text) text.textContent = `Error cargando modelo: ${e.message}`;
    console.error('[initDetector] Error:', e);
    // Ocultar overlay después de 5s para permitir usar la app sin detección
    setTimeout(() => hide(overlay), 5000);
    return;
  }
  hide(overlay);
}


/* ── Enumerar cámaras ─────────────────────────────────────────────────────── */

async function enumerateCameras() {
  const select = $('camera-select');
  if (!select) return;

  const previousValue = select.value;

  try {
    // Se necesita un stream temporal para obtener permisos y labels
    const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
    tempStream.getTracks().forEach(t => t.stop());

    const devices = await navigator.mediaDevices.enumerateDevices();
    const cameras = devices.filter(d => d.kind === 'videoinput');

    select.innerHTML = '';
    cameras.forEach((cam, i) => {
      const opt = document.createElement('option');
      opt.value = cam.deviceId;
      opt.textContent = cam.label || `Cámara ${i + 1}`;
      select.appendChild(opt);
    });

    // Añadir opción "Cámara trasera" y "frontal" para móvil
    if (cameras.length <= 1) {
      const optBack = document.createElement('option');
      optBack.value = 'environment';
      optBack.textContent = '📷 Cámara trasera';
      select.appendChild(optBack);

      const optFront = document.createElement('option');
      optFront.value = 'user';
      optFront.textContent = '🤳 Cámara frontal';
      select.appendChild(optFront);
    }

    const optVideo = document.createElement('option');
    optVideo.value = 'video-file';
    optVideo.textContent = '📁 Archivo de vídeo local';
    select.appendChild(optVideo);

    if (previousValue) select.value = previousValue;
    onSourceChange();
  } catch (e) {
    console.warn('No se pudieron enumerar cámaras:', e.message);
    onSourceChange();
  }
}


/* ══════════════════════════════════════════════════════════════════════════════
   Control de cámara y pipeline
   ══════════════════════════════════════════════════════════════════════════════ */

async function startCamera() {
  const select  = $('camera-select');
  const source  = select ? select.value : '0';

  // Construir constraints según el tipo de fuente
  let constraints;
  // En móvil pedir resolución más baja para reducir carga
  const idealW = IS_MOBILE ? 480 : 640;
  const idealH = IS_MOBILE ? 360 : 480;

  if (source === 'environment' || source === 'user') {
    constraints = {
      video: {
        facingMode: source === 'environment' ? { ideal: 'environment' } : 'user',
        width: { ideal: idealW }, height: { ideal: idealH },
      },
    };
  } else {
    constraints = {
      video: {
        deviceId: { exact: source },
        width: { ideal: idealW }, height: { ideal: idealH },
      },
    };
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia(constraints);

    video = document.createElement('video');
    video.srcObject    = stream;
    video.autoplay     = true;
    video.playsInline  = true;
    video.muted        = true;
    await video.play();

    // Esperar a que el vídeo tenga dimensiones
    await new Promise(r => {
      if (video.videoWidth > 0) return r();
      video.onloadedmetadata = () => r();
    });

    const vw = video.videoWidth;
    const vh = video.videoHeight;

    canvas = $('video-canvas');
    canvas.width  = vw;
    canvas.height = vh;
    ctx = canvas.getContext('2d');

    counter.setFrameSize(vw, vh);
    state.sessionId = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    state.crossLog  = [];

    return true;
  } catch (e) {
    showAlert(`Error de cámara: ${e.message}`, 'danger');
    return false;
  }
}

async function startVideoFile() {
  const file = state.selectedVideoFile;
  if (!file) {
    showAlert('Selecciona un archivo de vídeo primero', 'warning');
    return false;
  }

  try {
    if (state.videoObjectUrl) {
      URL.revokeObjectURL(state.videoObjectUrl);
      state.videoObjectUrl = null;
    }

    const objectUrl = URL.createObjectURL(file);
    state.videoObjectUrl = objectUrl;

    video = document.createElement('video');
    video.src = objectUrl;
    video.autoplay = false;
    video.playsInline = true;
    video.muted = true;

    await new Promise((resolve, reject) => {
      video.onloadedmetadata = () => resolve();
      video.onerror = () => reject(new Error('No se pudo leer el archivo de vídeo'));
    });

    await video.play();

    const vw = video.videoWidth;
    const vh = video.videoHeight;

    canvas = $('video-canvas');
    canvas.width  = vw;
    canvas.height = vh;
    ctx = canvas.getContext('2d');

    counter.setFrameSize(vw, vh);
    state.sessionId = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
    state.crossLog  = [];
    state.videoEndedNotified = false;

    return true;
  } catch (e) {
    showAlert(`Error de vídeo: ${e.message}`, 'danger');
    return false;
  }
}

function stopCamera() {
  if (video) {
    if (video.srcObject) {
      video.srcObject.getTracks().forEach(t => t.stop());
      video.srcObject = null;
    }
    video.pause();
    if (video.src) video.removeAttribute('src');
    video.load();
  }
  video = null;

  if (state.videoObjectUrl) {
    URL.revokeObjectURL(state.videoObjectUrl);
    state.videoObjectUrl = null;
  }

  if (ctx) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawNoSignal();
  }
}


/* ══════════════════════════════════════════════════════════════════════════════
   Loop de detección principal
   ══════════════════════════════════════════════════════════════════════════════ */

let _loopRunning = false;
let _frameCount   = 0;       // Contador de frames para skip
let _lastTracked  = [];      // Últimas detecciones trackeadas (reuso entre frames)
let _fpsSmooth    = 0;       // FPS suavizado (media móvil)

async function detectionLoop() {
  if (!state.running) { _loopRunning = false; return; }
  _loopRunning = true;

  if (state.paused || !video) {
    requestAnimationFrame(detectionLoop);
    return;
  }

  if (state.sourceMode === 'video-file' && video.ended) {
    state.running = false;
    state.paused  = false;
    updateStatusUI('video-ended');
    if (!state.videoEndedNotified) {
      showAlert('Vídeo finalizado — conteo completado', 'success', 5000);
      state.videoEndedNotified = true;
    }
    _loopRunning = false;
    return;
  }

  const t0 = performance.now();

  _frameCount++;
  const runInference = (_frameCount % SKIP_FRAMES === 0);

  if (runInference && detector.ready) {
    try {
      // 1. Detección ONNX
      const detections = await detector.detect(video, canvas.width, canvas.height);

      // 2. Tracking
      _lastTracked = tracker.update(detections);

      // 3. Conteo
      counter.process(_lastTracked);
    } catch (e) {
      console.error('[DetectionLoop] Error en detección:', e);
    }
  }

  // 4. Dibujar frame + anotaciones (reusa _lastTracked cuando se salta inferencia)
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  drawAnnotations(ctx, _lastTracked);

  // 5. FPS (media móvil para lectura estable)
  const elapsed = performance.now() - t0;
  const instantFps = 1000 / Math.max(elapsed, 1);
  _fpsSmooth = _fpsSmooth === 0 ? instantFps : _fpsSmooth * 0.8 + instantFps * 0.2;
  state.fps = Math.round(_fpsSmooth);

  // 6. Actualizar UI
  updateUI();

  requestAnimationFrame(detectionLoop);
}


/* ══════════════════════════════════════════════════════════════════════════════
   Dibujo sobre canvas
   ══════════════════════════════════════════════════════════════════════════════ */

function drawAnnotations(ctx, tracked) {
  const lineX1 = counter.lineX1;
  const lineY1 = counter.lineY1;
  const lineX2 = counter.lineX2;
  const lineY2 = counter.lineY2;
  const centerX = counter.lineX;
  const centerY = counter.lineY;

  // ── Línea de conteo ────────────────────────────────────────────────
  ctx.beginPath();
  ctx.moveTo(lineX1, lineY1);
  ctx.lineTo(lineX2, lineY2);
  ctx.strokeStyle = '#00ffff';
  ctx.lineWidth   = 4;
  ctx.stroke();

  // Extremos del segmento para referencia visual
  ctx.fillStyle = '#00ffff';
  ctx.beginPath();
  ctx.arc(lineX1, lineY1, 4, 0, Math.PI * 2);
  ctx.arc(lineX2, lineY2, 4, 0, Math.PI * 2);
  ctx.fill();

  // Flechas de dirección
  const nx = counter.lineNormalX;
  const ny = counter.lineNormalY;

  ctx.font = 'bold 12px system-ui, sans-serif';
  ctx.fillStyle = '#00ff00';
  ctx.fillText('→ Entrada', centerX + nx * 14, centerY + ny * 14);
  ctx.fillStyle = '#ff4444';
  ctx.fillText('← Salida', centerX - nx * 78, centerY - ny * 14);

  // ── Detecciones ────────────────────────────────────────────────────
  for (const det of tracked) {
    const [x1, y1, x2, y2] = det.bbox;
    const color = det.color;

    // Bbox
    ctx.strokeStyle = color;
    ctx.lineWidth   = 2;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    // Centro
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(det.center[0], det.center[1], 4, 0, Math.PI * 2);
    ctx.fill();

    // Etiqueta con fondo
    const label   = `${det.label} #${det.trackId} ${det.confidence.toFixed(2)}`;
    ctx.font      = '11px system-ui, sans-serif';
    const metrics = ctx.measureText(label);
    const lh      = 16;
    const ly      = Math.max(y1 - lh, 0);

    ctx.fillStyle = color;
    ctx.fillRect(x1, ly, metrics.width + 6, lh);
    ctx.fillStyle = '#000';
    ctx.fillText(label, x1 + 3, ly + 12);
  }
}

function drawNoSignal() {
  if (!canvas || !ctx) return;
  ctx.fillStyle = '#111';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#555';
  ctx.font = '20px system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('Pulsa "Iniciar" para comenzar', canvas.width / 2, canvas.height / 2);
  ctx.textAlign = 'start';
}


/* ══════════════════════════════════════════════════════════════════════════════
   Actualización de UI
   ══════════════════════════════════════════════════════════════════════════════ */

const CATEGORIES = ['persons', 'bicycles', 'cars', 'motorcycles', 'buses', 'trucks'];

const CAT_LABELS = {
  persons:     '👤 Personas',
  bicycles:    '🚲 Bicicletas',
  cars:        '🚗 Coches',
  motorcycles: '🏍️ Motos',
  buses:       '🚌 Autobuses',
  trucks:      '🚛 Camiones',
};

function updateUI() {
  const counts = counter.getCounts();

  // FPS
  const fpsEl = $('fps-badge');
  if (fpsEl) fpsEl.textContent = `${state.fps} fps`;

  // Fuente actual
  const sourceBadge = $('video-source-badge');
  if (sourceBadge) {
    const isVideo = state.sourceMode === 'video-file';
    sourceBadge.textContent = isVideo ? '📁 Vídeo local' : '📷 Cámara';
    sourceBadge.className = isVideo ? 'badge badge-warning no-dot' : 'badge badge-glass no-dot';
  }

  // Progreso en archivo de vídeo
  const progressWrap = $('video-progress-wrap');
  const progressBar = $('video-progress-bar');
  const progressLabel = $('video-progress-label');
  if (state.sourceMode === 'video-file' && video && Number.isFinite(video.duration) && video.duration > 0) {
    show(progressWrap);
    const pct = Math.max(0, Math.min(100, Math.round((video.currentTime / video.duration) * 100)));
    if (progressBar) progressBar.style.width = `${pct}%`;
    if (progressLabel) progressLabel.textContent = `${pct}%`;
  } else {
    hide(progressWrap);
  }

  // Contadores por categoría
  let totalIn = 0, totalOut = 0;

  CATEGORIES.forEach((cat) => {
    const c     = counts[cat] || { in: 0, out: 0, total: 0 };
    const inEl  = $(`count-${cat}-in`);
    const outEl = $(`count-${cat}-out`);
    const totEl = $(`count-${cat}-total`);
    const barEl = $(`bar-${cat}`);

    if (inEl)  inEl.textContent  = c.in;
    if (outEl) outEl.textContent = c.out;
    if (totEl) totEl.textContent = c.total;

    totalIn  += c.in;
    totalOut += c.out;

    if (barEl && c.total > 0) {
      barEl.style.width = `${Math.round((c.in / c.total) * 100)}%`;
    }
  });

  // Totales globales
  const gIn  = $('global-in');
  const gOut = $('global-out');
  const gTot = $('global-total');
  if (gIn)  gIn.textContent  = totalIn;
  if (gOut) gOut.textContent = totalOut;
  if (gTot) gTot.textContent = totalIn + totalOut;

  // Tabla resumen
  updateTable(counts);

  // Slider de línea (no actualizar si se está arrastrando)
  const slider = $('line-slider');
  if (slider && !slider.matches(':active')) {
    slider.value = Math.round(counter.linePos * 100);
  }

  const sliderY = $('line-y-slider');
  if (sliderY && !sliderY.matches(':active')) {
    sliderY.value = Math.round(counter.lineYPos * 100);
  }

  const sliderHeight = $('line-height-slider');
  if (sliderHeight && !sliderHeight.matches(':active')) {
    sliderHeight.value = Math.round(counter.lineHeightRel * 100);
  }

  const sliderAngle = $('line-angle-slider');
  if (sliderAngle && !sliderAngle.matches(':active')) {
    sliderAngle.value = Math.round(counter.lineAngleDeg);
  }

  const lineVal = $('line-val');
  const lineYVal = $('line-y-val');
  const lineHeightVal = $('line-height-val');
  const lineAngleVal = $('line-angle-val');
  if (lineVal) lineVal.textContent = `${Math.round(counter.linePos * 100)}%`;
  if (lineYVal) lineYVal.textContent = `${Math.round(counter.lineYPos * 100)}%`;
  if (lineHeightVal) lineHeightVal.textContent = `${Math.round(counter.lineHeightRel * 100)}%`;
  if (lineAngleVal) lineAngleVal.textContent = `${Math.round(counter.lineAngleDeg)}°`;
}

function updateStatusUI(status) {
  const btnStart = $('btn-start');
  const btnPause = $('btn-pause');
  const btnStop  = $('btn-stop');
  const badge    = $('status-badge');

  if (!btnStart) return;

  if (status === 'running') {
    btnStart.disabled = true;
    btnPause.disabled = false;
    btnStop.disabled  = false;
    btnPause.textContent = '⏸ Pausar';
    if (badge) { badge.textContent = 'Activo'; badge.className = 'badge badge-success no-dot'; }
  } else if (status === 'paused') {
    btnStart.disabled = true;
    btnPause.disabled = false;
    btnStop.disabled  = false;
    btnPause.textContent = '▶ Reanudar';
    if (badge) { badge.textContent = 'Pausado'; badge.className = 'badge badge-warning no-dot'; }
  } else if (status === 'video-ended') {
    btnStart.disabled = false;
    btnPause.disabled = true;
    btnStop.disabled  = false;
    btnPause.textContent = '⏸ Pausar';
    if (badge) { badge.textContent = 'Vídeo terminado'; badge.className = 'badge badge-success no-dot'; }
  } else {
    btnStart.disabled = false;
    btnPause.disabled = true;
    btnStop.disabled  = true;
    btnPause.textContent = '⏸ Pausar';
    if (badge) { badge.textContent = 'Detenido'; badge.className = 'badge badge-glass no-dot'; }
  }
}

function updateTable(counts) {
  const tbody = $('summary-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  CATEGORIES.forEach((cat) => {
    const c  = counts[cat] || { in: 0, out: 0, total: 0 };
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${CAT_LABELS[cat]}</td>
      <td class="text-blue">${c.in}</td>
      <td class="text-orange">${c.out}</td>
      <td><strong>${c.total}</strong></td>`;
    tbody.appendChild(tr);
  });
}


/* ══════════════════════════════════════════════════════════════════════════════
   Controles
   ══════════════════════════════════════════════════════════════════════════════ */

async function startCounting() {
  if (state.running) return;

  const isVideo = state.sourceMode === 'video-file';
  showAlert(isVideo ? 'Iniciando análisis de vídeo…' : 'Iniciando cámara…', 'info', 2000);
  const ok = isVideo ? await startVideoFile() : await startCamera();
  if (!ok) return;

  state.running = true;
  state.paused  = false;
  state.videoEndedNotified = false;
  updateStatusUI('running');

  // Mostrar sección de vídeo
  show($('video-section'));

  if (!_loopRunning) detectionLoop();
}

function pauseCounting() {
  if (!state.running) return;
  state.paused = !state.paused;
  updateStatusUI(state.paused ? 'paused' : 'running');
}

function stopCounting() {
  state.running = false;
  state.paused  = false;
  state.videoEndedNotified = false;
  stopCamera();
  updateStatusUI('stopped');
}

function resetCounters() {
  if (!confirm('¿Reiniciar todos los contadores?')) return;
  counter.reset();
  tracker.reset();
  state.crossLog = [];
  updateUI();
  showAlert('Contadores reiniciados', 'success');
}


/* ══════════════════════════════════════════════════════════════════════════════
   Slider de línea
   ══════════════════════════════════════════════════════════════════════════════ */

function onLineSlider(value) {
  const pos = parseInt(value, 10) / 100;
  $('line-val').textContent = value + '%';
  clearTimeout(_lineDebounce);
  _lineDebounce = setTimeout(() => {
    counter.setLinePosition(pos);
    redrawIdlePreviewWithSegment();
  }, 50);
}

function onLineYSlider(value) {
  const pos = parseInt(value, 10) / 100;
  $('line-y-val').textContent = value + '%';
  clearTimeout(_lineDebounce);
  _lineDebounce = setTimeout(() => {
    counter.setLineYPosition(pos);
    redrawIdlePreviewWithSegment();
  }, 50);
}

function onLineHeightSlider(value) {
  const h = parseInt(value, 10) / 100;
  $('line-height-val').textContent = value + '%';
  clearTimeout(_lineDebounce);
  _lineDebounce = setTimeout(() => {
    counter.setLineHeight(h);
    redrawIdlePreviewWithSegment();
  }, 50);
}

function onLineAngleSlider(value) {
  const angle = parseInt(value, 10);
  $('line-angle-val').textContent = `${value}°`;
  clearTimeout(_lineDebounce);
  _lineDebounce = setTimeout(() => {
    counter.setLineAngle(angle);
    redrawIdlePreviewWithSegment();
  }, 50);
}

function redrawIdlePreviewWithSegment() {
  if (state.running) return;
  if (!state.previewFrameCanvas || !ctx || !canvas) return;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(state.previewFrameCanvas, 0, 0, canvas.width, canvas.height);
  drawAnnotations(ctx, []);
  updateUI();
}

function onSourceChange() {
  const source = $('camera-select')?.value || 'environment';
  const fileWrap = $('video-file-wrap');
  state.sourceMode = source === 'video-file' ? 'video-file' : 'camera';
  if (state.sourceMode === 'video-file') {
    show(fileWrap);
    if (state.selectedVideoFile) {
      renderVideoFirstFramePreview(state.selectedVideoFile)
        .catch((e) => showAlert(`No se pudo actualizar vista previa: ${e.message}`, 'warning', 2500));
    }
  } else {
    hide(fileWrap);
  }
  updateUI();
}

async function renderVideoFirstFramePreview(file) {
  if (!file) return;

  const previewUrl = URL.createObjectURL(file);
  const previewVideo = document.createElement('video');
  previewVideo.src = previewUrl;
  previewVideo.preload = 'auto';
  previewVideo.playsInline = true;
  previewVideo.muted = true;
  previewVideo.currentTime = 0;

  try {
    previewVideo.load();

    await new Promise((resolve, reject) => {
      previewVideo.onloadedmetadata = () => resolve();
      previewVideo.onerror = () => reject(new Error('No se pudo cargar metadatos del vídeo'));
    });

    await new Promise((resolve, reject) => {
      const onReady = () => resolve();
      const onErr = () => reject(new Error('No se pudo decodificar el primer frame'));
      previewVideo.onloadeddata = onReady;
      previewVideo.onseeked = onReady;
      previewVideo.onerror = onErr;

      try {
        previewVideo.currentTime = Math.min(0.001, Number.isFinite(previewVideo.duration) ? previewVideo.duration : 0.001);
      } catch {
        // Algunos navegadores bloquean seek temprano; loadeddata resolverá igual
      }
    });

    const vw = previewVideo.videoWidth || 640;
    const vh = previewVideo.videoHeight || 480;

    canvas = $('video-canvas');
    if (!canvas) return;
    canvas.width = vw;
    canvas.height = vh;
    ctx = canvas.getContext('2d');

    if (counter?.setFrameSize) counter.setFrameSize(vw, vh);
    show($('video-section'));

    if (ctx) {
      if (!state.previewFrameCanvas) {
        state.previewFrameCanvas = document.createElement('canvas');
      }
      state.previewFrameCanvas.width = canvas.width;
      state.previewFrameCanvas.height = canvas.height;
      const previewCtx = state.previewFrameCanvas.getContext('2d');

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(previewVideo, 0, 0, canvas.width, canvas.height);
      if (previewCtx) {
        previewCtx.clearRect(0, 0, state.previewFrameCanvas.width, state.previewFrameCanvas.height);
        previewCtx.drawImage(previewVideo, 0, 0, state.previewFrameCanvas.width, state.previewFrameCanvas.height);
      }
      if (counter) drawAnnotations(ctx, []);
      updateUI();
    }
  } finally {
    previewVideo.pause();
    previewVideo.removeAttribute('src');
    previewVideo.load();
    URL.revokeObjectURL(previewUrl);
  }
}

async function onVideoFileSelected(event) {
  const file = event?.target?.files?.[0] || null;
  state.selectedVideoFile = file;
  state.videoEndedNotified = false;

  const info = $('video-file-info');
  const name = $('video-file-name');
  if (file) {
    if (name) name.textContent = `${file.name} (${Math.round(file.size / 1024 / 1024 * 10) / 10} MB)`;
    show(info);
    try {
      await renderVideoFirstFramePreview(file);
      showAlert('Primer frame cargado: ajusta la línea y luego inicia', 'info', 2600);
    } catch (e) {
      showAlert(`No se pudo mostrar el primer frame: ${e.message}`, 'warning', 3500);
    }
  } else {
    state.previewFrameCanvas = null;
    hide(info);
  }
}


/* ══════════════════════════════════════════════════════════════════════════════
   Registro de cruces y exportación CSV
   ══════════════════════════════════════════════════════════════════════════════ */

function logCross(categoria, direction, trackId) {
  const now    = new Date();
  const counts = counter.getCounts();
  const cat    = counts[categoria] || { in: 0, out: 0, total: 0 };

  state.crossLog.push({
    fecha:       now.toISOString().slice(0, 10),
    hora:        now.toTimeString().slice(0, 8),
    tipo:        categoria,
    direccion:   direction === 'in' ? 0 : 1,
    total_tipo:  cat.total,
    total_dir0:  Object.values(counts).reduce((s, c) => s + c.in, 0),
    total_dir1:  Object.values(counts).reduce((s, c) => s + c.out, 0),
    ubicacion:   state.location.name,
    latitude:    state.location.lat ?? '',
    longitude:   state.location.lng ?? '',
    sesion_id:   state.sessionId,
  });
}

function exportCSV() {
  const counts = counter.getCounts();
  const now    = new Date();
  const ts     = now.toISOString().slice(0, 19).replace(/[:-]/g, '');

  // ── Registros individuales (un row por cada cruce) ──
  let csv = 'fecha,hora,tipo,direccion,total_tipo,total_entrada,total_salida,ubicacion,latitude,longitude,sesion_id\n';

  for (const row of state.crossLog) {
    csv += [
      row.fecha, row.hora, row.tipo, row.direccion,
      row.total_tipo, row.total_dir0, row.total_dir1,
      row.ubicacion, row.latitude, row.longitude, row.sesion_id,
    ].join(',') + '\n';
  }

  // ── Resumen por categoría al final ──
  csv += '\n';
  csv += 'fecha,hora,tipo,entrada,salida,total,ubicacion,latitude,longitude,sesion_id\n';
  let totalIn = 0, totalOut = 0;

  CATEGORIES.forEach(cat => {
    const c = counts[cat];
    totalIn  += c.in;
    totalOut += c.out;
    csv += [
      now.toISOString().slice(0, 10),
      now.toTimeString().slice(0, 8),
      cat, c.in, c.out, c.total,
      state.location.name,
      state.location.lat ?? '',
      state.location.lng ?? '',
      state.sessionId,
    ].join(',') + '\n';
  });

  // Fila total
  csv += [
    now.toISOString().slice(0, 10),
    now.toTimeString().slice(0, 8),
    'TOTAL', totalIn, totalOut, totalIn + totalOut,
    state.location.name,
    state.location.lat ?? '',
    state.location.lng ?? '',
    state.sessionId,
  ].join(',') + '\n';

  // Descargar
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `conteo_${ts}.csv`;
  a.click();
  URL.revokeObjectURL(url);

  showAlert('CSV exportado ✓', 'success');
}


/* ══════════════════════════════════════════════════════════════════════════════
   Ubicación / GPS / Mapa
   ══════════════════════════════════════════════════════════════════════════════ */

function initMap() {
  const mapEl = $('location-map');
  if (!mapEl || typeof L === 'undefined') return;

  map = L.map('location-map', {
    center: [40.4168, -3.7038],   // Madrid por defecto
    zoom: 13,
    zoomControl: true,
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap',
    maxZoom: 19,
  }).addTo(map);

  // Click en el mapa para seleccionar ubicación
  map.on('click', (e) => {
    setMapMarker(e.latlng.lat, e.latlng.lng);
    state.location.lat = e.latlng.lat;
    state.location.lng = e.latlng.lng;
    updateLocationDisplay();

    // Reverse geocoding simple con Nominatim
    reverseGeocode(e.latlng.lat, e.latlng.lng);
  });

  // Fix: Leaflet necesita invalidateSize cuando el contenedor cambia
  setTimeout(() => map.invalidateSize(), 300);
}

function setMapMarker(lat, lng) {
  if (mapMarker) {
    mapMarker.setLatLng([lat, lng]);
  } else {
    mapMarker = L.marker([lat, lng], { draggable: true }).addTo(map);
    mapMarker.on('dragend', () => {
      const pos = mapMarker.getLatLng();
      state.location.lat = pos.lat;
      state.location.lng = pos.lng;
      updateLocationDisplay();
      reverseGeocode(pos.lat, pos.lng);
    });
  }
  map.setView([lat, lng], Math.max(map.getZoom(), 15));
}

async function reverseGeocode(lat, lng) {
  try {
    const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`;
    const res = await fetch(url, { headers: { 'Accept-Language': 'es' } });
    const data = await res.json();
    if (data.display_name) {
      const name = data.display_name.split(',').slice(0, 3).join(',');
      state.location.name = name;
      const input = $('location-input');
      if (input) input.value = name;
      updateLocationDisplay();
    }
  } catch { /* Silently fail — reverse geocoding is optional */ }
}

function requestGPS() {
  if (!navigator.geolocation) {
    showAlert('GPS no disponible en este navegador', 'warning');
    return;
  }
  showAlert('Obteniendo ubicación GPS…', 'info', 3000);

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      state.location.lat = lat;
      state.location.lng = lng;

      if (map) {
        setMapMarker(lat, lng);
        reverseGeocode(lat, lng);
      }

      updateLocationDisplay();
      showAlert('Ubicación GPS actualizada ✓', 'success');
    },
    () => showAlert('No se pudo obtener GPS', 'danger'),
    { timeout: 10000, enableHighAccuracy: true },
  );
}

function setLocationManual() {
  const name = $('location-input')?.value?.trim();
  if (!name) return;
  state.location.name = name;
  updateLocationDisplay();
  showAlert(`Ubicación: ${name}`, 'success');
}

function updateLocationDisplay() {
  const el = $('location-display');
  if (!el) return;
  const { name, lat, lng } = state.location;
  let text = name || '—';
  if (lat !== null && lng !== null) text += ` (${lat.toFixed(5)}, ${lng.toFixed(5)})`;
  el.textContent = text;
}


/* ══════════════════════════════════════════════════════════════════════════════
   Tema
   ══════════════════════════════════════════════════════════════════════════════ */

function toggleTheme() {
  const html = document.documentElement;
  if (html.classList.contains('theme-light')) {
    html.classList.remove('theme-light');
    html.classList.add('theme-dark');
    localStorage.setItem('theme', 'dark');
  } else {
    html.classList.remove('theme-dark');
    html.classList.add('theme-light');
    localStorage.setItem('theme', 'light');
  }
}

function applyStoredTheme() {
  const stored = localStorage.getItem('theme');
  if (stored) document.documentElement.classList.add(`theme-${stored}`);
}


/* ══════════════════════════════════════════════════════════════════════════════
   Alertas
   ══════════════════════════════════════════════════════════════════════════════ */

function showAlert(message, type = 'info', duration = 3000) {
  const container = $('alert-container');
  if (!container) return;

  const iconMap = {
    info:    '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>',
    success: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
    warning: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>',
    danger:  '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
  };

  const div = document.createElement('div');
  div.className = `alert alert-${type} animate-fade-up`;
  div.innerHTML = `
    <svg class="alert-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">${iconMap[type] || iconMap.info}</svg>
    <div class="alert-content">${message}</div>
    <button class="alert-dismiss" onclick="this.parentElement.remove()">&times;</button>`;
  container.appendChild(div);

  if (duration > 0) setTimeout(() => div.remove(), duration);
}


/* ══════════════════════════════════════════════════════════════════════════════
   Bind de eventos
   ══════════════════════════════════════════════════════════════════════════════ */

function bindEvents() {
  $('btn-start')?.addEventListener('click', startCounting);
  $('btn-pause')?.addEventListener('click', pauseCounting);
  $('btn-stop')?.addEventListener('click', stopCounting);
  $('btn-reset')?.addEventListener('click', resetCounters);
  $('btn-export')?.addEventListener('click', exportCSV);
  $('btn-gps')?.addEventListener('click', requestGPS);
  $('btn-set-location')?.addEventListener('click', setLocationManual);
  $('btn-theme')?.addEventListener('click', toggleTheme);

  $('line-slider')?.addEventListener('input', (e) => onLineSlider(e.target.value));
  $('line-y-slider')?.addEventListener('input', (e) => onLineYSlider(e.target.value));
  $('line-height-slider')?.addEventListener('input', (e) => onLineHeightSlider(e.target.value));
  $('line-angle-slider')?.addEventListener('input', (e) => onLineAngleSlider(e.target.value));
  $('camera-select')?.addEventListener('change', onSourceChange);
  $('video-file-input')?.addEventListener('change', onVideoFileSelected);
}
