/**
 * tracker.js — Tracker IoU simple para navegador
 *
 * Asigna IDs persistentes a las detecciones entre frames usando
 * coincidencia por IoU (Intersection over Union). Sin dependencias.
 */

'use strict';

class Track {
  /**
   * @param {number} id          ID único del track
   * @param {Object} detection   Detección inicial { bbox, center, categoria, ... }
   */
  constructor(id, detection) {
    this.id        = id;
    this.detection = detection;
    this.age       = 0;           // Frames sin match
    this.totalAge  = 0;           // Frames total de vida
    this.history   = [detection.center[0]];  // Historial de posición X (para conteo)
  }

  /** Actualiza el track con una nueva detección emparejada */
  update(detection) {
    this.detection = detection;
    this.age       = 0;
    this.totalAge++;
    this.history.push(detection.center[0]);
    if (this.history.length > 60) this.history = this.history.slice(-60);
  }
}


class Tracker {
  /**
   * @param {Object} opts
   * @param {number} opts.maxAge        Frames máximos sin match antes de eliminar track
   * @param {number} opts.iouThreshold  IoU mínimo para considerar un match
   */
  constructor({ maxAge = 15, iouThreshold = 0.25 } = {}) {
    this.nextId       = 1;
    this.tracks       = new Map();   // id → Track
    this.maxAge       = maxAge;
    this.iouThreshold = iouThreshold;
  }

  /**
   * Procesa un array de detecciones y devuelve detecciones con trackId asignado.
   * @param {Array<Object>} detections  Detecciones del frame actual
   * @returns {Array<Object>}           Detecciones enriquecidas con trackId e history
   */
  update(detections) {
    const trackList     = Array.from(this.tracks.values());
    const matched       = new Set();    // Índices de detecciones asignadas
    const matchedTracks = new Set();    // IDs de tracks asignados

    // ─ Construir pares candidatos (track, detección) con IoU ─────────
    const pairs = [];
    for (const track of trackList) {
      for (let d = 0; d < detections.length; d++) {
        const iou = this._iou(track.detection.bbox, detections[d].bbox);
        if (iou > this.iouThreshold) {
          pairs.push({ track, detIdx: d, iou });
        }
      }
    }

    // ─ Asignación greedy por IoU descendente ─────────────────────────
    pairs.sort((a, b) => b.iou - a.iou);

    const results = [];

    for (const { track, detIdx } of pairs) {
      if (matched.has(detIdx) || matchedTracks.has(track.id)) continue;

      track.update(detections[detIdx]);
      matched.add(detIdx);
      matchedTracks.add(track.id);

      results.push({
        ...detections[detIdx],
        trackId: track.id,
        history: track.history,
      });
    }

    // ─ Crear tracks nuevos para detecciones sin match ────────────────
    for (let d = 0; d < detections.length; d++) {
      if (matched.has(d)) continue;

      const track = new Track(this.nextId++, detections[d]);
      this.tracks.set(track.id, track);

      results.push({
        ...detections[d],
        trackId: track.id,
        history: track.history,
      });
    }

    // ─ Envejecer tracks sin match y eliminar los perdidos ────────────
    for (const track of trackList) {
      if (!matchedTracks.has(track.id)) {
        track.age++;
        if (track.age > this.maxAge) {
          this.tracks.delete(track.id);
        }
      }
    }

    return results;
  }

  /** Reinicia todos los tracks */
  reset() {
    this.tracks.clear();
    this.nextId = 1;
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
