/**
 * counter.js — Contador bidireccional de cruce de línea
 *
 * Port directo de la lógica Python (counter.py) a JavaScript.
 * Detecta cuándo un objeto cruza un segmento orientable:
 *   - Lado negativo → positivo = "in"  (Entrada)
 *   - Lado positivo → negativo = "out" (Salida)
 */

'use strict';

/** Categorías rastreadas (mismas que en config.py) */
const CATEGORY_KEYS = ['persons', 'bicycles', 'cars', 'motorcycles', 'buses', 'trucks'];


class Counter {
  /**
   * @param {Object}   opts
   * @param {number}   opts.linePosition  Posición relativa X del centro de línea (0.0 – 1.0)
   * @param {number}   opts.lineYPosition Posición relativa Y del centro de segmento (0.0 – 1.0)
   * @param {number}   opts.lineHeight    Longitud relativa del segmento (0.0 – 1.0)
   * @param {number}   opts.lineAngle     Ángulo en grados (0 = vertical)
   * @param {number}   opts.margin        Píxeles de margen para resetear la bandera de cruce
   * @param {Function} opts.onCross       Callback(categoria, direction, trackId)
   */
  constructor({ linePosition = 0.5, lineYPosition = 0.5, lineHeight = 1.0, lineAngle = 0, margin = 30, onCross = null } = {}) {
    this.linePos     = linePosition;
    this.lineYPos    = lineYPosition;
    this.lineHeightRel = lineHeight;
    this.lineAngleDeg = lineAngle;
    this.margin      = margin;
    this.onCross     = onCross;
    this.frameWidth  = 640;
    this.frameHeight = 480;
    this.lineX       = Math.round(this.frameWidth * this.linePos);
    this.lineY       = Math.round(this.frameHeight * this.lineYPos);
    this.lineLengthPx = Math.round(this.frameHeight * this.lineHeightRel);
    this.lineDirX = 0;
    this.lineDirY = 1;
    this.lineNormalX = 1;
    this.lineNormalY = 0;
    this.lineX1 = this.lineX;
    this.lineY1 = 0;
    this.lineX2 = this.lineX;
    this.lineY2 = this.frameHeight;
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
    this._recomputeLineSegment();
  }

  /** Actualiza posición relativa de la línea (0.02 – 0.98) */
  setLinePosition(pos) {
    this.linePos = Math.max(0.02, Math.min(0.98, pos));
    this._recomputeLineSegment();
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

  /** Actualiza ángulo del segmento en grados (-89 – 89, 0 = vertical) */
  setLineAngle(angleDeg) {
    this.lineAngleDeg = Math.max(-89, Math.min(89, angleDeg));
    this._recomputeLineSegment();
  }

  _recomputeLineSegment() {
    this.lineX = Math.round(this.frameWidth * this.linePos);
    this.lineY = Math.round(this.frameHeight * this.lineYPos);
    this.lineLengthPx = Math.round(this.frameHeight * this.lineHeightRel);

    const rad = (this.lineAngleDeg * Math.PI) / 180;
    this.lineDirX = Math.sin(rad);
    this.lineDirY = Math.cos(rad);

    // Normal para determinar lado de cruce. Con ángulo 0 queda: dist = x - lineX.
    this.lineNormalX = this.lineDirY;
    this.lineNormalY = -this.lineDirX;

    const half = this.lineLengthPx / 2;
    this.lineX1 = this.lineX - this.lineDirX * half;
    this.lineY1 = this.lineY - this.lineDirY * half;
    this.lineX2 = this.lineX + this.lineDirX * half;
    this.lineY2 = this.lineY + this.lineDirY * half;

    // Compatibilidad para cualquier uso legado del tramo vertical
    this.lineTop = Math.max(0, Math.min(this.frameHeight, Math.round(Math.min(this.lineY1, this.lineY2))));
    this.lineBottom = Math.max(0, Math.min(this.frameHeight, Math.round(Math.max(this.lineY1, this.lineY2))));
  }

  _signedDistanceToLine(point) {
    const dx = point[0] - this.lineX;
    const dy = point[1] - this.lineY;
    return dx * this.lineNormalX + dy * this.lineNormalY;
  }

  _lineProjection(point) {
    const dx = point[0] - this.lineX;
    const dy = point[1] - this.lineY;
    return dx * this.lineDirX + dy * this.lineDirY;
  }

  /* ── Procesamiento ──────────────────────────────────────────────────── */

  /**
   * Procesa detecciones con tracking.
    * Cada item debe tener: trackId, categoria, history (array de centros [x, y])
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
        const prevRaw = history[history.length - 2];
        const currRaw = history[history.length - 1];

        const prev = Array.isArray(prevRaw)
          ? prevRaw
          : [prevRaw, Number.isFinite(det.center?.[1]) ? det.center[1] : this.lineY];
        const curr = Array.isArray(currRaw)
          ? currRaw
          : [currRaw, Number.isFinite(det.center?.[1]) ? det.center[1] : this.lineY];

        const prevDist = this._signedDistanceToLine(prev);
        const currDist = this._signedDistanceToLine(curr);
        const prevProj = this._lineProjection(prev);
        const currProj = this._lineProjection(curr);

        const halfLen = this.lineLengthPx / 2;
        const midProj = (prevProj + currProj) / 2;
        const insideSegment = Math.abs(prevProj) <= halfLen
          || Math.abs(currProj) <= halfLen
          || Math.abs(midProj) <= halfLen;

        const eps = 1.5;

        if (prevDist < -eps && currDist >= eps && state.canCross && insideSegment) {
          // Lado negativo → lado positivo = Entrada
          this.counts[categoria].in++;
          state.canCross = false;
          if (this.onCross) this.onCross(categoria, 'in', trackId);

        } else if (prevDist > eps && currDist <= -eps && state.canCross && insideSegment) {
          // Lado positivo → lado negativo = Salida
          this.counts[categoria].out++;
          state.canCross = false;
          if (this.onCross) this.onCross(categoria, 'out', trackId);

        } else if (Math.abs(currDist) > this.margin) {
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
