/**
 * counter.js — Contador bidireccional de cruce de línea
 *
 * Port directo de la lógica Python (counter.py) a JavaScript.
 * Detecta cuándo un objeto cruza la línea vertical:
 *   - Izquierda → Derecha = "in"  (Entrada)
 *   - Derecha → Izquierda = "out" (Salida)
 */

'use strict';

/** Categorías rastreadas (mismas que en config.py) */
const CATEGORY_KEYS = ['persons', 'bicycles', 'cars', 'motorcycles', 'buses', 'trucks'];


class Counter {
  /**
   * @param {Object}   opts
   * @param {number}   opts.linePosition  Posición relativa X de la línea (0.0 – 1.0)
   * @param {number}   opts.lineYPosition Posición relativa Y del centro de segmento (0.0 – 1.0)
   * @param {number}   opts.lineHeight    Altura relativa del segmento (0.0 – 1.0)
   * @param {number}   opts.margin        Píxeles de margen para resetear la bandera de cruce
   * @param {Function} opts.onCross       Callback(categoria, direction, trackId)
   */
  constructor({ linePosition = 0.5, lineYPosition = 0.5, lineHeight = 1.0, margin = 30, onCross = null } = {}) {
    this.linePos     = linePosition;
    this.lineYPos    = lineYPosition;
    this.lineHeightRel = lineHeight;
    this.margin      = margin;
    this.onCross     = onCross;
    this.frameWidth  = 640;
    this.frameHeight = 480;
    this.lineX       = Math.round(this.frameWidth * this.linePos);
    this.lineY       = Math.round(this.frameHeight * this.lineYPos);
    this.lineHeightPx = Math.round(this.frameHeight * this.lineHeightRel);
    this.lineTop     = 0;
    this.lineBottom  = this.frameHeight;
    this._recomputeLineSegment();

    /** Estado de cruce por track: Map<trackId, { categoria, canCross }> */
    this._trackState = new Map();

    /** Contadores: { persons: { in: 0, out: 0 }, ... } */
    this.counts = {};
    CATEGORY_KEYS.forEach(k => { this.counts[k] = { in: 0, out: 0 }; });
  }

  /* ── Configuración ──────────────────────────────────────────────────── */

  /** Actualiza dimensiones del frame (llamar al abrir cámara) */
  setFrameSize(w, h) {
    this.frameWidth  = w;
    this.frameHeight = h;
    this.lineX       = Math.round(w * this.linePos);
    this._recomputeLineSegment();
  }

  /** Actualiza posición relativa de la línea (0.02 – 0.98) */
  setLinePosition(pos) {
    this.linePos = Math.max(0.02, Math.min(0.98, pos));
    this.lineX   = Math.round(this.frameWidth * this.linePos);
  }

  /** Actualiza posición vertical relativa del centro del segmento (0.02 – 0.98) */
  setLineYPosition(pos) {
    this.lineYPos = Math.max(0.02, Math.min(0.98, pos));
    this._recomputeLineSegment();
  }

  /** Actualiza altura relativa del segmento (0.05 – 1.0) */
  setLineHeight(heightRel) {
    this.lineHeightRel = Math.max(0.05, Math.min(1.0, heightRel));
    this._recomputeLineSegment();
  }

  _recomputeLineSegment() {
    this.lineY = Math.round(this.frameHeight * this.lineYPos);
    this.lineHeightPx = Math.round(this.frameHeight * this.lineHeightRel);

    const half = Math.round(this.lineHeightPx / 2);
    this.lineTop = Math.max(0, this.lineY - half);
    this.lineBottom = Math.min(this.frameHeight, this.lineY + half);

    // Ajustar para mantener altura lo más cercana posible cuando toca bordes
    const currentHeight = this.lineBottom - this.lineTop;
    if (currentHeight < this.lineHeightPx && this.frameHeight >= this.lineHeightPx) {
      if (this.lineTop === 0) {
        this.lineBottom = this.lineHeightPx;
      } else if (this.lineBottom === this.frameHeight) {
        this.lineTop = this.frameHeight - this.lineHeightPx;
      }
    }
  }

  /* ── Procesamiento ──────────────────────────────────────────────────── */

  /**
   * Procesa detecciones con tracking.
   * Cada item debe tener: trackId, categoria, history (array de posiciones X)
   * @param {Array<Object>} trackedDetections
   */
  process(trackedDetections) {
    const activeIds = new Set();

    for (const det of trackedDetections) {
      const { trackId, categoria, history } = det;
      if (!trackId || !this.counts[categoria]) continue;

      activeIds.add(trackId);

      // Inicializar estado si es nuevo
      if (!this._trackState.has(trackId)) {
        this._trackState.set(trackId, { categoria, canCross: true });
      }

      const state = this._trackState.get(trackId);

      // Comprobar cruce con al menos 2 puntos de historial
      if (history && history.length >= 2) {
        const prevX = history[history.length - 2];
        const currX = history[history.length - 1];
        const centerY = det.center?.[1];
        const insideSegment = Number.isFinite(centerY)
          && centerY >= this.lineTop
          && centerY <= this.lineBottom;

        if (prevX < this.lineX && currX >= this.lineX && state.canCross && insideSegment) {
          // Izquierda → Derecha = Entrada
          this.counts[categoria].in++;
          state.canCross = false;
          if (this.onCross) this.onCross(categoria, 'in', trackId);

        } else if (prevX > this.lineX && currX <= this.lineX && state.canCross && insideSegment) {
          // Derecha → Izquierda = Salida
          this.counts[categoria].out++;
          state.canCross = false;
          if (this.onCross) this.onCross(categoria, 'out', trackId);

        } else if (Math.abs(currX - this.lineX) > this.margin) {
          // Se alejó de la línea → puede volver a cruzar
          state.canCross = true;
        }
      }
    }

    // Limpiar tracks que ya no están activos
    for (const [id] of this._trackState) {
      if (!activeIds.has(id)) this._trackState.delete(id);
    }
  }

  /* ── Consultas ──────────────────────────────────────────────────────── */

  /** Devuelve copia de conteos con campo 'total' */
  getCounts() {
    const result = {};
    for (const [k, v] of Object.entries(this.counts)) {
      result[k] = { in: v.in, out: v.out, total: v.in + v.out };
    }
    return result;
  }

  /** Reinicia contadores y estados de cruce */
  reset() {
    CATEGORY_KEYS.forEach(k => { this.counts[k] = { in: 0, out: 0 }; });
    this._trackState.clear();
  }
}
