# -*- coding: utf-8 -*-
"""
test_api.py — Tests de integración para todos los endpoints de YoloConteo v2.

USO:
    # Con el servidor corriendo (iniciar.bat o uvicorn main:app --port 8000):
    python test_api.py

    # Especificar host/puerto distinto:
    python test_api.py --host http://192.168.1.10:8000

REQUISITOS:
    pip install requests websocket-client
    (ya incluido en el entorno virtual si hiciste pip install -r requirements.txt)
"""

import sys
import json
import time
import argparse
import threading

try:
    import requests
except ImportError:
    print("Instala 'requests':  pip install requests")
    sys.exit(1)

BASE = "http://localhost:8000"

# ── Colores ANSI ──────────────────────────────────────────────────────────────
OK   = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
INFO = "\033[94m→\033[0m"

passed = 0
failed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  {OK}  {label}")
    else:
        failed += 1
        print(f"  {FAIL}  {label}  {detail}")


def section(title: str) -> None:
    print(f"\n\033[1m{'─'*50}\033[0m")
    print(f"\033[1m  {title}\033[0m")
    print(f"\033[1m{'─'*50}\033[0m")


def get(path: str, **kwargs):
    return requests.get(f"{BASE}{path}", timeout=10, **kwargs)


def post(path: str, body: dict = None, **kwargs):
    return requests.post(f"{BASE}{path}", json=body, timeout=10, **kwargs)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — Servidor arrancado y frontend
# ══════════════════════════════════════════════════════════════════════════════
def test_server():
    section("1. Servidor y frontend")
    try:
        r = get("/")
        check("GET /  →  200", r.status_code == 200)
        check("Content-Type HTML", "text/html" in r.headers.get("content-type", ""))
        check("Contiene 'YoloConteo'", "YoloConteo" in r.text)
        check("Carga ntizar.css", "ntizar.css" in r.text)
        check("Carga app.js", "app.js" in r.text)
    except requests.ConnectionError:
        print(f"  {FAIL}  No se puede conectar a {BASE}")
        print(f"  {INFO}  Asegúrate de que el servidor está corriendo: uvicorn main:app --port 8000")
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2 — Archivos estáticos
# ══════════════════════════════════════════════════════════════════════════════
def test_static():
    section("2. Archivos estáticos")
    r = get("/static/ntizar.css")
    check("GET /static/ntizar.css  →  200", r.status_code == 200)
    check("ntizar.css tiene contenido", len(r.text) > 10_000)

    r = get("/static/app.js")
    check("GET /static/app.js  →  200", r.status_code == 200)
    check("app.js tiene connectWS()", "connectWS" in r.text)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — /api/status (sin cámara activa)
# ══════════════════════════════════════════════════════════════════════════════
def test_status():
    section("3. /api/status")
    r = get("/api/status")
    check("GET /api/status  →  200", r.status_code == 200)
    data = r.json()
    check("Campo 'status' presente", "status" in data)
    check("Campo 'counts' presente", "counts" in data)
    check("Campo 'location' presente", "location" in data)
    check("Estado inicial es 'stopped'", data["status"] == "stopped")

    counts = data["counts"]
    expected_keys = {"persons", "bicycles", "cars", "motorcycles", "buses", "trucks"}
    check("6 categorías en counts", set(counts.keys()) == expected_keys)
    for k in expected_keys:
        check(f"counts.{k} tiene in/out/total", all(f in counts[k] for f in ("in","out","total")))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — Línea de conteo
# ══════════════════════════════════════════════════════════════════════════════
def test_line_position():
    section("4. /api/line-position")
    for pos, label in [(0.3, "0.3"), (0.5, "0.5"), (0.75, "0.75")]:
        r = post("/api/line-position", {"position": pos})
        check(f"POST position={label}  →  200", r.status_code == 200)
        data = r.json()
        check(f"line_pos devuelta = {label}", abs(data.get("line_pos", 0) - pos) < 0.001)

    # Valores fuera de rango deben ser rechazados (422)
    r = post("/api/line-position", {"position": 1.5})
    check("position=1.5 rechazado (422)", r.status_code == 422)
    r = post("/api/line-position", {"position": -0.1})
    check("position=-0.1 rechazado (422)", r.status_code == 422)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — Ubicación
# ══════════════════════════════════════════════════════════════════════════════
def test_location():
    section("5. /api/location")

    # Solo nombre
    r = post("/api/location", {"name": "Gran Vía 28"})
    check("POST solo nombre  →  200", r.status_code == 200)
    data = r.json()
    check("name guardado", data.get("name") == "Gran Vía 28")

    # Nombre + coordenadas reales
    r = post("/api/location", {"lat": 40.4198, "lng": -3.7038, "name": "Madrid Centro"})
    check("POST lat+lng+name  →  200", r.status_code == 200)
    data = r.json()
    check("lat devuelta correcta", abs(data.get("lat", 0) - 40.4198) < 0.001)
    check("lng devuelta correcta", abs(data.get("lng", 0) - (-3.7038)) < 0.001)
    check("name devuelto correcto", data.get("name") == "Madrid Centro")

    # Verificar que persiste en /api/status
    r = get("/api/status")
    loc = r.json().get("location", {})
    check("location visible en /api/status", loc.get("name") == "Madrid Centro")


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6 — Cámara (source inválido debe devolver 400)
# ══════════════════════════════════════════════════════════════════════════════
def test_camera_invalid():
    section("6. /api/start con source inválido")
    r = post("/api/start", {"source": "/ruta/que/no/existe.mp4"})
    check(
        "Source inválido  →  400",
        r.status_code == 400,
        f"(got {r.status_code})",
    )


# ══════════════════════════════════════════════════════════════════════════════
# TEST 7 — Reset y pause sin sesión activa
# ══════════════════════════════════════════════════════════════════════════════
def test_reset_and_pause():
    section("7. /api/reset y /api/pause (sin sesión activa)")
    r = post("/api/reset")
    check("POST /api/reset  →  200", r.status_code == 200)

    # Pause cuando está stopped no debe romper nada
    r = post("/api/pause")
    check("POST /api/pause (stopped)  →  200", r.status_code == 200)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 8 — WebSocket (smoke test básico)
# ══════════════════════════════════════════════════════════════════════════════
def test_websocket():
    section("8. WebSocket /ws")
    try:
        import websocket as ws_lib
    except ImportError:
        print(f"  {INFO}  websocket-client no instalado. Saltando test WS.")
        print(f"  {INFO}  Instala con: pip install websocket-client")
        return

    received = []
    errors   = []

    def _run():
        try:
            ws = ws_lib.create_connection(f"ws://localhost:8000/ws", timeout=5)
            msg = ws.recv()
            received.append(json.loads(msg))
            ws.close()
        except Exception as e:
            errors.append(str(e))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=8)

    check("WebSocket conecta y recibe mensaje", len(received) > 0 and not errors,
          errors[0] if errors else "")

    if received:
        msg = received[0]
        check("Mensaje tiene 'status'",    "status"    in msg)
        check("Mensaje tiene 'counts'",    "counts"    in msg)
        check("Mensaje tiene 'fps'",       "fps"       in msg)
        check("Mensaje tiene 'timestamp'", "timestamp" in msg)
        check("Mensaje tiene 'location'",  "location"  in msg)


# ══════════════════════════════════════════════════════════════════════════════
# TEST 9 — Export CSV sin datos (debe devolver CSV vacío o con cabeceras)
# ══════════════════════════════════════════════════════════════════════════════
def test_export():
    section("9. /api/export (sin datos)")
    r = post("/api/export")
    check("POST /api/export  →  200", r.status_code == 200)
    check("Content-Type CSV", "text/csv" in r.headers.get("content-type", ""))
    check("Content-Disposition con filename", "filename" in r.headers.get("content-disposition", ""))
    check("CSV tiene cabeceras", "tipo" in r.text and "fecha" in r.text)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000",
                        help="URL base del servidor (default: http://localhost:8000)")
    args = parser.parse_args()

    global BASE
    BASE = args.host.rstrip("/")

    print(f"\n\033[1m  YoloConteo v2 — Tests de integración API\033[0m")
    print(f"  Servidor: {BASE}\n")

    test_server()
    test_static()
    test_status()
    test_line_position()
    test_location()
    test_camera_invalid()
    test_reset_and_pause()
    test_websocket()
    test_export()

    print(f"\n{'═'*52}")
    total = passed + failed
    color = "\033[92m" if failed == 0 else "\033[91m"
    print(f"  {color}Resultado: {passed}/{total} tests pasaron\033[0m")
    if failed > 0:
        print(f"  \033[91m{failed} test(s) fallaron\033[0m")
    print(f"{'═'*52}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
