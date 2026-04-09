# -*- coding: utf-8 -*-
"""
test_counter.py — Tests unitarios para la lógica de conteo bidireccional.
NO requiere servidor corriendo ni cámara. Se puede ejecutar en cualquier momento.

USO:
    python test_counter.py
    python -m pytest test_counter.py -v   (si tienes pytest instalado)
"""

import sys
import unittest

# Añadir directorio raíz al path para importar los módulos
sys.path.insert(0, __file__.rsplit("\\", 1)[0])

from counter import BidirectionalCounter, TrackInfo


class TestBidirectionalCounter(unittest.TestCase):

    def setUp(self):
        """Crea un contador con dimensiones de test y sin callback."""
        self.counter = BidirectionalCounter(
            frame_width=640,
            frame_height=480,
            line_position=0.5,   # línea en x=320
            margin=30,
        )
        self.line_x = self.counter.line_x  # 320

    # ── Inicialización ─────────────────────────────────────────────────────────

    def test_initial_counts_are_zero(self):
        counts = self.counter.get_counts()
        for cat, v in counts.items():
            self.assertEqual(v["in"],    0, f"{cat}.in should be 0")
            self.assertEqual(v["out"],   0, f"{cat}.out should be 0")
            self.assertEqual(v["total"], 0, f"{cat}.total should be 0")

    def test_all_six_categories_present(self):
        counts = self.counter.get_counts()
        expected = {"persons", "bicycles", "cars", "motorcycles", "buses", "trucks"}
        self.assertEqual(set(counts.keys()), expected)

    def test_initial_line_position(self):
        _, rel = self.counter.get_line_position()
        self.assertAlmostEqual(rel, 0.5, places=2)

    # ── Cruces de línea ────────────────────────────────────────────────────────

    def _make_detection(self, track_id: int, categoria: str, cx: int):
        """Helper: crea una detección mínima."""
        return {
            "track_id": track_id,
            "categoria": categoria,
            "centro": (cx, 240),
        }

    def test_left_to_right_crossing_counts_as_in(self):
        """Objeto que va de izquierda a derecha → contador 'in' sube."""
        # Empieza a la izquierda de la línea
        self.counter.process([self._make_detection(1, "persons", self.line_x - 50)])
        # Cruza la línea
        self.counter.process([self._make_detection(1, "persons", self.line_x + 10)])

        counts = self.counter.get_counts()
        self.assertEqual(counts["persons"]["in"],  1)
        self.assertEqual(counts["persons"]["out"], 0)

    def test_right_to_left_crossing_counts_as_out(self):
        """Objeto que va de derecha a izquierda → contador 'out' sube."""
        self.counter.process([self._make_detection(2, "cars", self.line_x + 50)])
        self.counter.process([self._make_detection(2, "cars", self.line_x - 10)])

        counts = self.counter.get_counts()
        self.assertEqual(counts["cars"]["out"], 1)
        self.assertEqual(counts["cars"]["in"],  0)

    def test_no_crossing_no_count(self):
        """Objeto que no cruza la línea no debe contar."""
        # Siempre a la izquierda
        for cx in [100, 110, 120, 130, 140]:
            self.counter.process([self._make_detection(3, "bicycles", cx)])

        counts = self.counter.get_counts()
        self.assertEqual(counts["bicycles"]["in"],  0)
        self.assertEqual(counts["bicycles"]["out"], 0)

    def test_no_double_count_same_crossing(self):
        """Cruzar la línea una sola vez solo debe contar 1, no múltiples."""
        lx = self.line_x
        # Cruce: izq → der, luego sigue moviéndose a la derecha
        for cx in [lx - 60, lx - 30, lx + 10, lx + 40, lx + 70]:
            self.counter.process([self._make_detection(4, "motorcycles", cx)])

        counts = self.counter.get_counts()
        self.assertEqual(counts["motorcycles"]["in"], 1, "Solo debe contar 1 cruce")

    def test_object_can_cross_back(self):
        """Un objeto que cruza, se aleja y vuelve debe contar dos cruces."""
        lx     = self.line_x
        margin = self.counter.margin

        # Cruce 1: izq → der
        self.counter.process([self._make_detection(5, "persons", lx - 60)])
        self.counter.process([self._make_detection(5, "persons", lx + 10)])

        # Se aleja lo suficiente para resetear la bandera
        self.counter.process([self._make_detection(5, "persons", lx + margin + 50)])

        # Cruce 2: der → izq
        self.counter.process([self._make_detection(5, "persons", lx - 10)])

        counts = self.counter.get_counts()
        self.assertEqual(counts["persons"]["in"],  1)
        self.assertEqual(counts["persons"]["out"], 1)

    def test_multiple_objects_independent(self):
        """Dos objetos distintos se trackean de forma independiente."""
        lx = self.line_x
        # Objeto A cruza izq→der
        self.counter.process([self._make_detection(10, "cars",   lx - 50)])
        self.counter.process([self._make_detection(10, "cars",   lx + 10)])
        # Objeto B cruza der→izq
        self.counter.process([self._make_detection(11, "trucks", lx + 50)])
        self.counter.process([self._make_detection(11, "trucks", lx - 10)])

        counts = self.counter.get_counts()
        self.assertEqual(counts["cars"]["in"],    1)
        self.assertEqual(counts["trucks"]["out"], 1)

    def test_unknown_category_ignored(self):
        """Categoría no conocida no debe lanzar excepción ni contar."""
        lx = self.line_x
        try:
            self.counter.process([{
                "track_id": 99, "categoria": "ovni", "centro": (lx - 50, 240),
            }])
            self.counter.process([{
                "track_id": 99, "categoria": "ovni", "centro": (lx + 10, 240),
            }])
        except Exception as e:
            self.fail(f"Categoría desconocida lanzó excepción: {e}")

    def test_missing_track_id_ignored(self):
        """Detección sin track_id se ignora silenciosamente."""
        try:
            self.counter.process([{"categoria": "persons", "centro": (200, 240)}])
        except Exception as e:
            self.fail(f"Detección sin track_id lanzó excepción: {e}")

    # ── Reset ─────────────────────────────────────────────────────────────────

    def test_reset_clears_all_counts(self):
        lx = self.line_x
        self.counter.process([self._make_detection(20, "persons", lx - 50)])
        self.counter.process([self._make_detection(20, "persons", lx + 10)])

        counts_before = self.counter.get_counts()
        self.assertEqual(counts_before["persons"]["in"], 1)

        self.counter.reset()

        counts_after = self.counter.get_counts()
        for cat, v in counts_after.items():
            self.assertEqual(v["in"],    0, f"After reset: {cat}.in != 0")
            self.assertEqual(v["out"],   0, f"After reset: {cat}.out != 0")
            self.assertEqual(v["total"], 0, f"After reset: {cat}.total != 0")

    def test_reset_clears_tracks(self):
        """Después del reset los tracks previos no afectan al siguiente cruce."""
        lx = self.line_x
        # Cruce antes del reset (objeto 30 queda "cruzado" → puede_cruzar=False)
        self.counter.process([self._make_detection(30, "cars", lx - 50)])
        self.counter.process([self._make_detection(30, "cars", lx + 10)])

        self.counter.reset()

        # El mismo track_id vuelve a aparecer; debe contarse de nuevo
        self.counter.process([self._make_detection(30, "cars", lx - 50)])
        self.counter.process([self._make_detection(30, "cars", lx + 10)])

        counts = self.counter.get_counts()
        self.assertEqual(counts["cars"]["in"], 1)

    # ── Configuración dinámica de línea ───────────────────────────────────────

    def test_set_line_position_updates_line_x(self):
        self.counter.set_line_position(0.25)
        lx, rel = self.counter.get_line_position()
        self.assertAlmostEqual(rel, 0.25, places=2)
        self.assertEqual(lx, int(640 * 0.25))

    def test_set_line_position_clamps(self):
        self.counter.set_line_position(2.0)    # demasiado grande
        _, rel = self.counter.get_line_position()
        self.assertLessEqual(rel, 0.95)

        self.counter.set_line_position(-5.0)   # demasiado pequeño
        _, rel = self.counter.get_line_position()
        self.assertGreaterEqual(rel, 0.05)

    # ── total en get_counts ───────────────────────────────────────────────────

    def test_total_equals_in_plus_out(self):
        lx     = self.line_x
        margin = self.counter.margin

        # Cruce ida
        self.counter.process([self._make_detection(40, "buses", lx - 60)])
        self.counter.process([self._make_detection(40, "buses", lx + 10)])
        # Aleja
        self.counter.process([self._make_detection(40, "buses", lx + margin + 50)])
        # Cruce vuelta
        self.counter.process([self._make_detection(40, "buses", lx - 10)])

        counts = self.counter.get_counts()
        c = counts["buses"]
        self.assertEqual(c["total"], c["in"] + c["out"])

    # ── Callback ──────────────────────────────────────────────────────────────

    def test_on_cross_callback_fires(self):
        events = []
        counter = BidirectionalCounter(
            frame_width=640, frame_height=480,
            line_position=0.5,
            on_cross=lambda cat, direction, tid: events.append((cat, direction, tid)),
        )
        lx = counter.line_x
        counter.process([{"track_id": 50, "categoria": "persons", "centro": (lx - 50, 240)}])
        counter.process([{"track_id": 50, "categoria": "persons", "centro": (lx + 10, 240)}])

        self.assertEqual(len(events), 1)
        cat, direction, tid = events[0]
        self.assertEqual(cat,       "persons")
        self.assertEqual(direction, "in")
        self.assertEqual(tid,       50)


# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n  YoloConteo v2 — Tests unitarios (counter.py)")
    print("  " + "─" * 48)
    result = unittest.main(verbosity=2, exit=False)
    # Código de salida para CI
    sys.exit(0 if result.result.wasSuccessful() else 1)
