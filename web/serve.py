#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serve.py — Servidor local para YoloConteo v2 Web.

Sirve archivos estáticos con los headers necesarios para
WebGPU y SharedArrayBuffer (WASM multi-hilo).

Uso:
    python serve.py          # Puerto 8000
    python serve.py 3000     # Puerto 3000
"""

import http.server
import os
import socket
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


class CORSHandler(http.server.SimpleHTTPRequestHandler):
    """Añade headers Cross-Origin necesarios para ONNX Runtime Web."""

    def end_headers(self):
        # Necesarios para SharedArrayBuffer (WASM multi-thread)
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'credentialless')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def log_message(self, format, *args):
        """Silenciar logs de archivos estáticos, solo mostrar errores."""
        if args and '200' not in str(args[1]):
            super().log_message(format, *args)


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    # Servir desde el directorio de este script (web/)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    ip = get_local_ip()
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║     YoloConteo v2 — Versión Web          ║")
    print("  ║     Detección en navegador (WebGPU)      ║")
    print("  ╚══════════════════════════════════════════╝")
    print()
    print(f"  ┌─────────────────────────────────────────────┐")
    print(f"  │   http://localhost:{PORT}        (local)      │")
    print(f"  │   http://{ip}:{PORT}  (red local)    │")
    print(f"  └─────────────────────────────────────────────┘")
    print()
    print("  Abre la URL en Chrome/Edge (WebGPU habilitado).")
    print("  Pulsa Ctrl+C para detener el servidor.")
    print()

    with http.server.HTTPServer(('0.0.0.0', PORT), CORSHandler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n  Servidor detenido.")


if __name__ == "__main__":
    main()
