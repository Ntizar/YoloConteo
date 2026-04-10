// app.js — YoloConteo v2 Frontend
// WebSocket, controles, geolocation, UI updates — Vanilla JS, sin frameworks

'use strict';

// ── Estado local ──────────────────────────────────────────────────────────────
const state = {
  status: 'stopped',
  videoVisible: false,
  connected: false,
  uploadedVideoPath: null,   // ruta del video subido al servidor
  sourceType: 'camera',
};

// ── Helpers DOM ───────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const show = (el) => { if (el) el.style.display = ''; };
const hide = (el) => { if (el) el.style.display = 'none'; };

// ── WebSocket con reconexión exponencial ──────────────────────────────────────
let ws;
let reconnectDelay = 1000;

function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const url   = `${proto}://${location.host}/ws`;
  ws = new WebSocket(url);

  ws.onopen = () => {
    reconnectDelay = 1000;
    setConnected(true);
  };

  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      updateUI(data);
    } catch (_) { /* ignorar mensajes malformados */ }
  };

  ws.onclose = () => {
    setConnected(false);
    setTimeout(connectWS, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 30_000);
  };

  ws.onerror = () => ws.close();
}

function setConnected(ok) {
  state.connected = ok;
  const badge = $('conn-badge');
  if (!badge) return;
  badge.textContent = ok ? 'Conectado' : 'Desconectado';
  badge.className   = ok
    ? 'badge badge-success no-dot'
    : 'badge badge-danger no-dot';
  if (!ok) showAlert('Conexión perdida. Reconectando…', 'warning');
  else      showAlert('Conexión establecida', 'success');
}

// ── Actualización de UI desde datos del WebSocket ────────────────────────────
const CATEGORIES = ['persons', 'bicycles', 'cars', 'motorcycles', 'buses', 'trucks'];
const TOTALS     = { in: 0, out: 0, total: 0 };

function updateUI(data) {
  // Estado y FPS
  state.status     = data.status;
  state.sourceType = data.source_type || 'camera';
  updateStatusButtons(data.status);

  const fpsEl = $('fps-badge');
  if (fpsEl) fpsEl.textContent = `${data.fps} fps`;

  // Badge de fuente
  const srcBadge = $('video-source-badge');
  if (srcBadge) {
    srcBadge.textContent = state.sourceType === 'video' ? '📁 Vídeo' : '📷 Cámara';
    srcBadge.className   = state.sourceType === 'video'
      ? 'badge badge-warning no-dot'
      : 'badge badge-glass no-dot';
  }

  // Progreso de reproducción de vídeo
  const playbackWrap = $('video-playback-wrap');
  const playbackBar  = $('video-progress-bar');
  const playbackPct  = $('video-progress-pct');
  if (state.sourceType === 'video') {
    if (playbackWrap) playbackWrap.style.display = '';
    const pct = Math.round((data.video_progress || 0) * 100);
    if (playbackBar) playbackBar.style.width = `${pct}%`;
    if (playbackPct) playbackPct.textContent  = `${pct}%`;
  } else {
    if (playbackWrap) playbackWrap.style.display = 'none';
  }

  // Notificación de vídeo terminado (una sola vez)
  if (data.video_ended && !state._videoEndedNotified) {
    state._videoEndedNotified = true;
    showAlert('✅ Vídeo finalizado — revisa los resultados del conteo', 'success', 6000);
  }
  if (!data.video_ended) {
    state._videoEndedNotified = false;
  }

  // Ubicación
  if (data.location) {
    const locEl = $('location-display');
    if (locEl) {
      const { name, lat, lng } = data.location;
      let text = name || '';
      if (lat !== null && lat !== undefined) text += ` (${lat.toFixed(5)}, ${lng.toFixed(5)})`;
      locEl.textContent = text || '—';
    }
  }

  // Contadores por categoría
  let totalIn = 0, totalOut = 0;

  CATEGORIES.forEach((cat) => {
    const counts = data.counts?.[cat] || { in: 0, out: 0, total: 0 };
    const inEl    = $(`count-${cat}-in`);
    const outEl   = $(`count-${cat}-out`);
    const totalEl = $(`count-${cat}-total`);
    const barEl   = $(`bar-${cat}`);

    if (inEl)    inEl.textContent    = counts.in;
    if (outEl)   outEl.textContent   = counts.out;
    if (totalEl) totalEl.textContent = counts.total;

    totalIn  += counts.in  || 0;
    totalOut += counts.out || 0;

    // Progress bar relativa al total de esa categoría
    if (barEl && counts.total > 0) {
      const pct = Math.round((counts.in / counts.total) * 100);
      barEl.style.width = `${pct}%`;
    }

    // Alerta especial para vehículos grandes
    if ((cat === 'buses' || cat === 'trucks') && counts.total > 0) {
      // solo si el total subió
      const prev = parseInt(barEl?.dataset?.prev || '0', 10);
      if (counts.total > prev) {
        const label = cat === 'buses' ? 'Autobús' : 'Camión';
        showAlert(`${label} detectado`, 'warning', 2500);
      }
      if (barEl) barEl.dataset.prev = counts.total;
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
  updateTable(data.counts);

  // Slider de línea (solo actualizar si no está siendo arrastrado)
  const slider = $('line-slider');
  if (slider && !slider.matches(':active')) {
    slider.value = Math.round((data.line_pos || 0.5) * 100);
  }
}

function updateStatusButtons(status) {
  const btnStart  = $('btn-start');
  const btnPause  = $('btn-pause');
  const btnStop   = $('btn-stop');
  const statusBadge = $('status-badge');

  if (!btnStart) return;

  if (status === 'running') {
    btnStart.disabled = true;
    btnPause.disabled = false;
    btnStop.disabled  = false;
    btnPause.textContent = '⏸ Pausar';
    if (statusBadge) { statusBadge.textContent = 'Activo'; statusBadge.className = 'badge badge-success no-dot'; }
  } else if (status === 'paused') {
    btnStart.disabled = true;
    btnPause.disabled = false;
    btnStop.disabled  = false;
    btnPause.textContent = '▶ Reanudar';
    if (statusBadge) { statusBadge.textContent = 'Pausado'; statusBadge.className = 'badge badge-warning no-dot'; }
  } else if (status === 'video_ended') {
    btnStart.disabled = false;
    btnPause.disabled = true;
    btnStop.disabled  = false;
    btnPause.textContent = '⏸ Pausar';
    if (statusBadge) { statusBadge.textContent = 'Vídeo terminado'; statusBadge.className = 'badge badge-success no-dot'; }
  } else {
    btnStart.disabled = false;
    btnPause.disabled = true;
    btnStop.disabled  = true;
    btnPause.textContent = '⏸ Pausar';
    if (statusBadge) { statusBadge.textContent = 'Detenido'; statusBadge.className = 'badge badge-glass no-dot'; }
  }
}
    btnStart.disabled = true;
    btnPause.disabled = false;
    btnStop.disabled  = false;
    btnPause.textContent = '▶ Reanudar';
    if (statusBadge) { statusBadge.textContent = 'Pausado'; statusBadge.className = 'badge badge-warning no-dot'; }
  } else {
    btnStart.disabled = false;
    btnPause.disabled = true;
    btnStop.disabled  = true;
    btnPause.textContent = '⏸ Pausar';
    if (statusBadge) { statusBadge.textContent = 'Detenido'; statusBadge.className = 'badge badge-glass no-dot'; }
  }
}

// ── Tabla resumen ─────────────────────────────────────────────────────────────
const CAT_LABELS = {
  persons: '👤 Personas', bicycles: '🚲 Bicicletas', cars: '🚗 Coches',
  motorcycles: '🏍️ Motos', buses: '🚌 Autobuses', trucks: '🚛 Camiones',
};

function updateTable(counts = {}) {
  const tbody = $('summary-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  CATEGORIES.forEach((cat) => {
    const c = counts[cat] || { in: 0, out: 0, total: 0 };
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${CAT_LABELS[cat] || cat}</td>
      <td class="text-blue">${c.in}</td>
      <td class="text-orange">${c.out}</td>
      <td><strong>${c.total}</strong></td>
    `;
    tbody.appendChild(tr);
  });
}

// ── Controles ─────────────────────────────────────────────────────────────────
async function apiCall(endpoint, method = 'POST', body = null) {
  try {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(endpoint, opts);
    return r.ok ? r.json() : null;
  } catch (e) {
    showAlert(`Error de red: ${e.message}`, 'danger');
    return null;
  }
}

function getSelectedSource() {
  const sel = $('camera-select');
  if (sel?.value === 'upload') {
    return state.uploadedVideoPath || null;
  }
  const custom = $('camera-custom');
  if (sel?.value === 'custom') return custom?.value?.trim() || '0';
  return sel?.value || '0';
}

async function startCounting() {
  const source = getSelectedSource();
  if (source === null) {
    showAlert('Primero sube un vídeo antes de iniciar el conteo', 'warning');
    return;
  }
  const res = await apiCall('/api/start', 'POST', { source });
  if (!res) showAlert('No se pudo iniciar', 'danger');
}

async function pauseCounting() {
  await apiCall('/api/pause');
}

async function stopCounting() {
  await apiCall('/api/stop');
}

async function resetCounters() {
  if (!confirm('¿Reiniciar todos los contadores?')) return;
  await apiCall('/api/reset');
}

async function exportCSV() {
  try {
    const r = await fetch('/api/export', { method: 'POST' });
    if (!r.ok) { showAlert('Error al exportar', 'danger'); return; }
    const blob = await r.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `conteo_${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    showAlert(`Error exportando: ${e.message}`, 'danger');
  }
}

async function uploadVideo() {
  const fileInput = $('video-file-input');
  const file = fileInput?.files?.[0];
  if (!file) { showAlert('Selecciona un archivo de vídeo primero', 'warning'); return; }

  const progressWrap = $('upload-progress-wrap');
  const progressBar  = $('upload-progress-bar');
  const progressPct  = $('upload-pct');
  const infoWrap     = $('video-info-wrap');

  show(progressWrap);
  hide(infoWrap);
  if (progressBar) progressBar.style.width = '0%';
  if (progressPct) progressPct.textContent = '0%';

  const formData = new FormData();
  formData.append('file', file);

  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload-video');

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        if (progressBar) progressBar.style.width = `${pct}%`;
        if (progressPct) progressPct.textContent = `${pct}%`;
      }
    };

    xhr.onload = () => {
      hide(progressWrap);
      if (xhr.status >= 200 && xhr.status < 300) {
        const data = JSON.parse(xhr.responseText);
        state.uploadedVideoPath = data.path;

        // Mostrar info del vídeo
        const nameEl = $('video-info-name');
        const durEl  = $('video-info-dur');
        const fpsEl2 = $('video-info-fps');
        if (nameEl) nameEl.textContent = data.filename;
        if (durEl)  durEl.textContent  = `${data.duration_s}s`;
        if (fpsEl2) fpsEl2.textContent = `${data.fps} fps`;
        show(infoWrap);

        showAlert(`✅ Vídeo listo: ${data.filename} (${data.duration_s}s)`, 'success', 4000);
        resolve(data);
      } else {
        let detail = 'Error al subir el vídeo';
        try { detail = JSON.parse(xhr.responseText).detail || detail; } catch (_) {}
        showAlert(detail, 'danger');
        resolve(null);
      }
    };

    xhr.onerror = () => {
      hide(progressWrap);
      showAlert('Error de red al subir el vídeo', 'danger');
      resolve(null);
    };

    xhr.send(formData);
  });
}

// ── Slider de línea ───────────────────────────────────────────────────────────
let _lineDebounce = null;

function onLineSlider(value) {
  const pos = parseInt(value, 10) / 100;
  clearTimeout(_lineDebounce);
  _lineDebounce = setTimeout(() => {
    apiCall('/api/line-position', 'POST', { position: pos });
  }, 200);
}

// ── Video toggle ──────────────────────────────────────────────────────────────
function toggleVideo() {
  const section = $('video-section');
  const img     = $('video-feed');
  const btn     = $('btn-toggle-video');
  if (!section) return;

  state.videoVisible = !state.videoVisible;

  if (state.videoVisible) {
    show(section);
    if (img) img.src = `/video_feed?fps=15&quality=60`;
    if (btn) btn.textContent = '📷 Ocultar video';
  } else {
    hide(section);
    if (img) img.src = '';   // libera el stream MJPEG
    if (btn) btn.textContent = '📷 Mostrar video';
  }
}

// ── Geolocation ───────────────────────────────────────────────────────────────
function requestGPS() {
  if (!navigator.geolocation) {
    showAlert('GPS no disponible en este navegador', 'warning');
    return;
  }
  showAlert('Obteniendo ubicación GPS…', 'info', 3000);
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const name = $('location-input')?.value || '';
      apiCall('/api/location', 'POST', {
        lat:  pos.coords.latitude,
        lng:  pos.coords.longitude,
        name,
      }).then(() => showAlert('Ubicación GPS actualizada ✓', 'success'));
    },
    () => showAlert('No se pudo obtener GPS. Prueba con nombre manual.', 'danger'),
    { timeout: 10_000, enableHighAccuracy: true },
  );
}

async function setLocationManual() {
  const name = $('location-input')?.value?.trim();
  if (!name) return;
  await apiCall('/api/location', 'POST', { name });
  showAlert(`Ubicación establecida: ${name}`, 'success');
}

// ── Cámara personalizada ──────────────────────────────────────────────────────
function onCameraSelect() {
  const sel        = $('camera-select');
  const customWrap = $('camera-custom-wrap');
  const uploadWrap = $('upload-wrap');
  if (customWrap) customWrap.style.display = sel?.value === 'custom' ? '' : 'none';
  if (uploadWrap) uploadWrap.style.display = sel?.value === 'upload' ? '' : 'none';
  // Resetear ruta subida si se cambia a otro modo
  if (sel?.value !== 'upload') {
    state.uploadedVideoPath = null;
    const infoWrap = $('video-info-wrap');
    if (infoWrap) hide(infoWrap);
  }
}

// ── Tema ──────────────────────────────────────────────────────────────────────
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

// ── Alertas ───────────────────────────────────────────────────────────────────
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
    <button class="alert-dismiss" onclick="this.parentElement.remove()">&times;</button>
  `;
  container.appendChild(div);

  if (duration > 0) {
    setTimeout(() => div.remove(), duration);
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  applyStoredTheme();
  connectWS();

  // Ocultar video por defecto (mobile-first)
  const videoSection = $('video-section');
  if (videoSection) hide(videoSection);

  // Bind eventos
  $('btn-start')?.addEventListener('click', startCounting);
  $('btn-pause')?.addEventListener('click', pauseCounting);
  $('btn-stop')?.addEventListener('click', stopCounting);
  $('btn-reset')?.addEventListener('click', resetCounters);
  $('btn-export')?.addEventListener('click', exportCSV);
  $('btn-upload-video')?.addEventListener('click', uploadVideo);
  $('btn-toggle-video')?.addEventListener('click', toggleVideo);
  $('btn-gps')?.addEventListener('click', requestGPS);
  $('btn-set-location')?.addEventListener('click', setLocationManual);
  $('btn-theme')?.addEventListener('click', toggleTheme);
  $('camera-select')?.addEventListener('change', onCameraSelect);
  $('line-slider')?.addEventListener('input', (e) => onLineSlider(e.target.value));
});
