# -*- coding: utf-8 -*-
"""
Módulo GUI - Interfaz gráfica con Tkinter para el sistema de conteo bidireccional.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
from PIL import Image, ImageTk
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Callable
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContadorWidget(tk.Frame):
    """
    Widget personalizado para mostrar los contadores de una categoría.
    """
    
    def __init__(
        self,
        parent,
        categoria: str,
        nombre_display: str,
        color_hex: str,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.categoria = categoria
        self.color = color_hex
        
        self.configure(bg="#1a1a2e", padx=5, pady=5)
        
        # Nombre de la categoría con indicador de color
        nombre_frame = tk.Frame(self, bg="#1a1a2e")
        nombre_frame.grid(row=0, column=0, sticky="w")
        
        # Indicador de color
        indicador = tk.Frame(nombre_frame, bg=color_hex, width=4, height=20)
        indicador.pack(side="left", padx=(0, 8))
        
        self.label_nombre = tk.Label(
            nombre_frame,
            text=nombre_display,
            font=("Segoe UI", 10, "bold"),
            fg="#ffffff",
            bg="#1a1a2e",
            width=14,
            anchor="w"
        )
        self.label_nombre.pack(side="left")
        
        # Contador Izq→Der (verde)
        self.label_izq_der = tk.Label(
            self,
            text="0",
            font=("Segoe UI", 18, "bold"),
            fg="#00ff88",
            bg="#16213e",
            width=4,
            relief="flat",
            padx=8,
            pady=2
        )
        self.label_izq_der.grid(row=0, column=1, padx=8)
        
        # Contador Der→Izq (rojo)
        self.label_der_izq = tk.Label(
            self,
            text="0",
            font=("Segoe UI", 18, "bold"),
            fg="#ff6b6b",
            bg="#16213e",
            width=4,
            relief="flat",
            padx=8,
            pady=2
        )
        self.label_der_izq.grid(row=0, column=2, padx=8)
    
    def actualizar(self, izq_der: int, der_izq: int) -> None:
        """
        Actualiza los valores de los contadores.
        
        Args:
            izq_der: Conteo de izquierda a derecha
            der_izq: Conteo de derecha a izquierda
        """
        self.label_izq_der.config(text=str(izq_der))
        self.label_der_izq.config(text=str(der_izq))


class PanelContadores(tk.Frame):
    """
    Panel que contiene todos los contadores de categorías.
    """
    
    def __init__(self, parent, categorias: Dict, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(bg="#1a1a2e", padx=15, pady=15)
        self.widgets_contadores: Dict[str, ContadorWidget] = {}
        
        # Título del panel con estilo moderno
        titulo = tk.Label(
            self,
            text="📊 CONTADORES EN TIEMPO REAL",
            font=("Segoe UI", 12, "bold"),
            fg="#00d4ff",
            bg="#1a1a2e"
        )
        titulo.pack(pady=(0, 15))
        
        # Cabecera de columnas con estilo moderno
        frame_cabecera = tk.Frame(self, bg="#1a1a2e")
        frame_cabecera.pack(fill="x", pady=(0, 10))
        
        tk.Label(
            frame_cabecera,
            text="CATEGORÍA",
            font=("Segoe UI", 9, "bold"),
            fg="#808080",
            bg="#1a1a2e",
            width=18,
            anchor="w"
        ).grid(row=0, column=0, sticky="w")
        
        tk.Label(
            frame_cabecera,
            text="→",
            font=("Segoe UI", 12, "bold"),
            fg="#00ff88",
            bg="#1a1a2e",
            width=5
        ).grid(row=0, column=1, padx=5)
        
        tk.Label(
            frame_cabecera,
            text="←",
            font=("Segoe UI", 12, "bold"),
            fg="#ff6b6b",
            bg="#1a1a2e",
            width=5
        ).grid(row=0, column=2, padx=5)
        
        # Separador moderno
        sep = tk.Frame(self, bg="#00d4ff", height=1)
        sep.pack(fill="x", pady=8)
        
        # Crear widgets para cada categoría
        colores_hex = {
            'adulto': '#00FF00',
            'nino': '#00FFFF',
            'silla_ruedas': '#FF00FF',
            'bicicleta': '#FFA500',
            'patinete': '#FF0000',
            'movilidad_reducida': '#800080'
        }
        
        for cat_key, cat_info in categorias.items():
            color = colores_hex.get(cat_key, '#FFFFFF')
            widget = ContadorWidget(
                self,
                cat_key,
                cat_info['nombre'],
                color
            )
            widget.pack(fill="x", pady=2)
            self.widgets_contadores[cat_key] = widget
        
        # Separador antes de totales
        sep2 = tk.Frame(self, bg="#00d4ff", height=2)
        sep2.pack(fill="x", pady=15)
        
        # Frame para totales con estilo destacado
        frame_totales = tk.Frame(self, bg="#16213e", padx=15, pady=15)
        frame_totales.pack(fill="x")
        
        tk.Label(
            frame_totales,
            text="⚡ TOTALES",
            font=("Segoe UI", 12, "bold"),
            fg="#ffd700",
            bg="#16213e"
        ).grid(row=0, column=0, sticky="w", padx=(0, 20))
        
        self.label_total_izq_der = tk.Label(
            frame_totales,
            text="0",
            font=("Segoe UI", 24, "bold"),
            fg="#00ff88",
            bg="#0f0f23",
            width=5,
            relief="flat",
            padx=10,
            pady=5
        )
        self.label_total_izq_der.grid(row=0, column=1, padx=10)
        
        self.label_total_der_izq = tk.Label(
            frame_totales,
            text="0",
            font=("Segoe UI", 24, "bold"),
            fg="#ff6b6b",
            bg="#0f0f23",
            width=5,
            relief="flat",
            padx=10,
            pady=5
        )
        self.label_total_der_izq.grid(row=0, column=2, padx=10)
    
    def actualizar_contadores(self, contadores: Dict) -> None:
        """
        Actualiza todos los contadores con los valores proporcionados.
        
        Args:
            contadores: Diccionario con los contadores por categoría
        """
        total_izq_der = 0
        total_der_izq = 0
        
        for categoria, valores in contadores.items():
            if categoria in self.widgets_contadores:
                izq_der = valores.get('izq_der', 0)
                der_izq = valores.get('der_izq', 0)
                self.widgets_contadores[categoria].actualizar(izq_der, der_izq)
                total_izq_der += izq_der
                total_der_izq += der_izq
        
        # Actualizar totales
        self.label_total_izq_der.config(text=str(total_izq_der))
        self.label_total_der_izq.config(text=str(total_der_izq))


class PanelInfo(tk.Frame):
    """
    Panel con información adicional: GPS, timestamp, FPS.
    """
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(bg="#1a1a2e", padx=15, pady=15)
        
        # Título con estilo moderno
        tk.Label(
            self,
            text="📍 INFORMACIÓN",
            font=("Segoe UI", 12, "bold"),
            fg="#00d4ff",
            bg="#1a1a2e"
        ).pack(pady=(0, 15))
        
        # Estilo común para frames de info
        info_bg = "#1a1a2e"
        label_style = {'font': ("Segoe UI", 9), 'fg': "#808080", 'bg': info_bg, 'width': 10, 'anchor': "w"}
        value_style = {'font': ("Segoe UI", 9), 'fg': "#ffffff", 'bg': info_bg}
        
        # Frame para GPS
        frame_gps = tk.Frame(self, bg=info_bg)
        frame_gps.pack(fill="x", pady=3)
        tk.Label(frame_gps, text="🛰️ GPS:", **label_style).pack(side="left")
        self.label_gps = tk.Label(frame_gps, text="Obteniendo...", fg="#00d4ff", font=("Segoe UI", 9), bg=info_bg)
        self.label_gps.pack(side="left")
        
        # Frame para Ubicación
        frame_ubicacion = tk.Frame(self, bg=info_bg)
        frame_ubicacion.pack(fill="x", pady=3)
        tk.Label(frame_ubicacion, text="📌 Lugar:", **label_style).pack(side="left")
        self.entry_ubicacion = tk.Entry(
            frame_ubicacion,
            font=("Segoe UI", 9),
            width=18,
            bg="#16213e",
            fg="#ffffff",
            insertbackground="#00d4ff",
            relief="flat",
            bd=5
        )
        self.entry_ubicacion.pack(side="left", fill="x", expand=True)
        
        # Frame para Timestamp
        frame_tiempo = tk.Frame(self, bg=info_bg)
        frame_tiempo.pack(fill="x", pady=3)
        tk.Label(frame_tiempo, text="🕐 Hora:", **label_style).pack(side="left")
        self.label_tiempo = tk.Label(
            frame_tiempo, text="--:--:--",
            font=("Segoe UI", 14, "bold"), fg="#ffd700", bg=info_bg
        )
        self.label_tiempo.pack(side="left")
        
        # Frame para FPS
        frame_fps = tk.Frame(self, bg=info_bg)
        frame_fps.pack(fill="x", pady=3)
        tk.Label(frame_fps, text="⚡ FPS:", **label_style).pack(side="left")
        self.label_fps = tk.Label(
            frame_fps, text="0",
            font=("Segoe UI", 14, "bold"), fg="#00ff88", bg=info_bg
        )
        self.label_fps.pack(side="left")
        
        # Frame para Estado con indicador visual
        frame_estado = tk.Frame(self, bg=info_bg)
        frame_estado.pack(fill="x", pady=(10, 3))
        tk.Label(frame_estado, text="📊 Estado:", **label_style).pack(side="left")
        self.label_estado = tk.Label(
            frame_estado, text="● DETENIDO",
            font=("Segoe UI", 10, "bold"), fg="#ff4444", bg=info_bg
        )
        self.label_estado.pack(side="left")
    
    def actualizar_gps(self, lat: Optional[float], lon: Optional[float]) -> None:
        """Actualiza la visualización de coordenadas GPS."""
        if lat is not None and lon is not None:
            self.label_gps.config(text=f"{lat:.6f}, {lon:.6f}")
        else:
            self.label_gps.config(text="No disponible")
    
    def actualizar_tiempo(self) -> None:
        """Actualiza el timestamp."""
        ahora = datetime.now().strftime("%H:%M:%S")
        self.label_tiempo.config(text=ahora)
    
    def actualizar_fps(self, fps: float) -> None:
        """Actualiza el contador de FPS."""
        self.label_fps.config(text=f"{fps:.1f}")
        
        # Cambiar color según rendimiento
        if fps >= 25:
            self.label_fps.config(fg="#2ECC71")  # Verde
        elif fps >= 15:
            self.label_fps.config(fg="#F1C40F")  # Amarillo
        else:
            self.label_fps.config(fg="#E74C3C")  # Rojo
    
    def actualizar_estado(self, estado: str) -> None:
        """Actualiza el estado del sistema."""
        estados = {
            'detenido': ('● DETENIDO', '#ff4444'),
            'ejecutando': ('● ACTIVO', '#00ff88'),
            'pausado': ('● PAUSADO', '#ffd700')
        }
        texto, color = estados.get(estado, ('● DESCONOCIDO', '#808080'))
        self.label_estado.config(text=texto, fg=color)
    
    def obtener_ubicacion(self) -> str:
        """Obtiene el texto de ubicación ingresado."""
        return self.entry_ubicacion.get()
    
    def establecer_ubicacion(self, ubicacion: str) -> None:
        """Establece el texto de ubicación."""
        self.entry_ubicacion.delete(0, tk.END)
        self.entry_ubicacion.insert(0, ubicacion)


class PanelControles(tk.Frame):
    """
    Panel con botones de control de la aplicación.
    """
    
    def __init__(
        self,
        parent,
        callback_iniciar: Callable,
        callback_pausar: Callable,
        callback_reiniciar: Callable,
        callback_exportar: Callable,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.callback_pausar = callback_pausar
        self.pausado = False
        
        self.configure(bg="#1a1a2e", padx=15, pady=15)
        
        # Título con estilo moderno
        titulo_frame = tk.Frame(self, bg="#1a1a2e")
        titulo_frame.pack(fill="x", pady=(0, 15))
        tk.Label(
            titulo_frame,
            text="⚡ CONTROLES",
            font=("Segoe UI", 12, "bold"),
            fg="#00d4ff",
            bg="#1a1a2e"
        ).pack()
        
        # Estilo moderno para botones
        btn_style = {
            'font': ("Segoe UI", 10, "bold"),
            'width': 20,
            'height': 2,
            'cursor': "hand2",
            'relief': "flat",
            'bd': 0,
        }
        
        # Botón Iniciar
        self.btn_iniciar = tk.Button(
            self,
            text="▶  INICIAR CONTEO",
            bg="#00c853",
            fg="white",
            activebackground="#00e676",
            activeforeground="white",
            command=callback_iniciar,
            **btn_style
        )
        self.btn_iniciar.pack(pady=8)
        
        # Botón Pausar/Reanudar
        self.btn_pausar = tk.Button(
            self,
            text="⏸  PAUSAR",
            bg="#ff9800",
            fg="white",
            activebackground="#ffc107",
            activeforeground="white",
            command=self._on_pausar_click,
            state="disabled",
            **btn_style
        )
        self.btn_pausar.pack(pady=8)
        
        # Botón Detener
        self.btn_detener = tk.Button(
            self,
            text="⏹  DETENER",
            bg="#f44336",
            fg="white",
            activebackground="#ef5350",
            activeforeground="white",
            command=callback_reiniciar,
            **btn_style
        )
        self.btn_detener.pack(pady=8)
        
        # Botón Exportar
        self.btn_exportar = tk.Button(
            self,
            text="📊  EXPORTAR CSV",
            bg="#2196f3",
            fg="white",
            activebackground="#42a5f5",
            activeforeground="white",
            command=callback_exportar,
            **btn_style
        )
        self.btn_exportar.pack(pady=8)
        
        # Separador visual
        sep_frame = tk.Frame(self, bg="#00d4ff", height=2)
        sep_frame.pack(fill="x", pady=20)
        
        # Configuración con estilo moderno
        config_label_style = {'font': ("Segoe UI", 9), 'fg': "#a0a0a0", 'bg': "#1a1a2e"}
        
        # Slider para posición de línea
        tk.Label(self, text="📍 Posición de Línea", **config_label_style).pack(anchor="w")
        
        self.slider_linea = tk.Scale(
            self,
            from_=10,
            to=90,
            orient="horizontal",
            bg="#1a1a2e",
            fg="#00d4ff",
            troughcolor="#16213e",
            highlightthickness=0,
            sliderrelief="flat",
            length=180
        )
        self.slider_linea.set(50)
        self.slider_linea.pack(pady=(0, 10))
        
        # Slider para confianza
        tk.Label(self, text="🎯 Umbral de Confianza", **config_label_style).pack(anchor="w")
        
        self.slider_confianza = tk.Scale(
            self,
            from_=10,
            to=90,
            orient="horizontal",
            bg="#1a1a2e",
            fg="#00d4ff",
            troughcolor="#16213e",
            highlightthickness=0,
            sliderrelief="flat",
            length=180
        )
        self.slider_confianza.set(50)
        self.slider_confianza.pack(pady=(0, 10))
    
    def _on_pausar_click(self) -> None:
        """Handler interno para el botón pausar."""
        self.pausado = not self.pausado
        if self.pausado:
            self.btn_pausar.config(text="▶  REANUDAR", bg="#4caf50")
        else:
            self.btn_pausar.config(text="⏸  PAUSAR", bg="#ff9800")
        if self.callback_pausar:
            self.callback_pausar()
    
    def actualizar_estado_botones(self, ejecutando: bool, pausado: bool) -> None:
        """
        Actualiza el estado de los botones según el estado de la aplicación.
        
        Args:
            ejecutando: Si la captura está activa
            pausado: Si está en pausa
        """
        self.pausado = pausado
        if ejecutando and not pausado:
            self.btn_iniciar.config(state="disabled")
            self.btn_pausar.config(state="normal", text="⏸  PAUSAR", bg="#ff9800")
        elif ejecutando and pausado:
            self.btn_iniciar.config(state="disabled")
            self.btn_pausar.config(state="normal", text="▶  REANUDAR", bg="#4caf50")
        else:
            self.btn_iniciar.config(state="normal")
            self.btn_pausar.config(state="disabled")
            self.pausado = False
    
    def obtener_posicion_linea(self) -> float:
        """Obtiene la posición de la línea (0.0 a 1.0)."""
        return self.slider_linea.get() / 100.0
    
    def obtener_umbral_confianza(self) -> float:
        """Obtiene el umbral de confianza (0.0 a 1.0)."""
        return self.slider_confianza.get() / 100.0


class AlertaMovilidadReducida(tk.Toplevel):
    """
    Ventana de alerta para detección de persona con movilidad reducida.
    """
    
    def __init__(self, parent, duracion: int = 3000):
        super().__init__(parent)
        
        self.title("⚠️ ALERTA")
        self.configure(bg="#FF5733")
        
        # Configurar ventana
        ancho = 400
        alto = 150
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (ancho // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (alto // 2)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        
        self.overrideredirect(True)  # Sin bordes
        self.attributes('-topmost', True)
        
        # Contenido
        tk.Label(
            self,
            text="⚠️ ALERTA ⚠️",
            font=("Helvetica", 16, "bold"),
            fg="white",
            bg="#FF5733"
        ).pack(pady=10)
        
        tk.Label(
            self,
            text="Persona con movilidad reducida detectada",
            font=("Helvetica", 12),
            fg="white",
            bg="#FF5733"
        ).pack(pady=5)
        
        tk.Label(
            self,
            text="🦽 Por favor, asegure el paso libre",
            font=("Helvetica", 11),
            fg="white",
            bg="#FF5733"
        ).pack(pady=5)
        
        # Cerrar automáticamente después de la duración
        self.after(duracion, self.destroy)


class GUI:
    """
    Clase principal de la interfaz gráfica.
    
    Maneja la ventana principal, el feed de video y todos los paneles.
    """
    
    def __init__(
        self,
        titulo: str = "Sistema de Conteo Bidireccional - YoloConteo",
        ancho: int = 1200,
        alto: int = 700,
        categorias: Dict = None
    ):
        """
        Inicializa la interfaz gráfica.
        
        Args:
            titulo: Título de la ventana
            ancho: Ancho de la ventana en píxeles
            alto: Alto de la ventana en píxeles
            categorias: Diccionario con las categorías a mostrar
        """
        self.ancho = ancho
        self.alto = alto
        
        # Categorías por defecto
        self.categorias = categorias or {
            'adulto': {'id': 0, 'nombre': 'Adultos', 'color': (0, 255, 0)},
            'nino': {'id': 1, 'nombre': 'Niños', 'color': (255, 255, 0)},
            'silla_ruedas': {'id': 2, 'nombre': 'Sillas de Ruedas', 'color': (255, 0, 255)},
            'bicicleta': {'id': 3, 'nombre': 'Bicicletas', 'color': (0, 165, 255)},
            'patinete': {'id': 4, 'nombre': 'Patinetes', 'color': (0, 0, 255)},
            'movilidad_reducida': {'id': 5, 'nombre': 'Movilidad Reducida', 'color': (128, 0, 128)},
        }
        
        # Crear ventana principal con estilo moderno oscuro
        self.root = tk.Tk()
        self.root.title(titulo)
        self.root.geometry(f"{ancho}x{alto}")
        self.root.configure(bg="#0f0f23")
        self.root.resizable(True, True)
        
        # Intentar usar tema oscuro en Windows
        try:
            self.root.tk.call('tk', 'scaling', 1.2)
        except:
            pass
        
        # Callbacks
        self.callback_iniciar: Optional[Callable] = None
        self.callback_pausar: Optional[Callable] = None
        self.callback_reiniciar: Optional[Callable] = None
        self.callback_exportar: Optional[Callable] = None
        self.callback_cerrar: Optional[Callable] = None
        self.callback_slider_linea: Optional[Callable] = None
        self.callback_slider_confianza: Optional[Callable] = None
        
        # Variables de estado
        self.ejecutando = False
        self.pausado = False
        
        # Imagen actual para el canvas
        self.imagen_tk = None
        
        # Construir interfaz
        self._construir_interfaz()
        
        # Configurar evento de cierre
        self.root.protocol("WM_DELETE_WINDOW", self._on_cerrar)
        
        # Iniciar actualización de tiempo
        self._actualizar_tiempo()
    
    def _construir_interfaz(self) -> None:
        """Construye todos los elementos de la interfaz."""
        # Frame principal horizontal con estilo moderno
        self.frame_principal = tk.Frame(self.root, bg="#0f0f23")
        self.frame_principal.pack(fill="both", expand=True, padx=15, pady=15)
        
        # ========== PANEL IZQUIERDO (Video) ==========
        self.frame_video = tk.Frame(self.frame_principal, bg="#16213e")
        self.frame_video.pack(side="left", fill="both", expand=True, padx=(0, 15))
        
        # Título del video con estilo moderno
        titulo_video = tk.Frame(self.frame_video, bg="#16213e")
        titulo_video.pack(fill="x", pady=10)
        tk.Label(
            titulo_video,
            text="📹 VIDEO EN TIEMPO REAL",
            font=("Segoe UI", 14, "bold"),
            fg="#00d4ff",
            bg="#16213e"
        ).pack()
        
        # Canvas para el video con borde moderno
        canvas_frame = tk.Frame(self.frame_video, bg="#00d4ff", padx=2, pady=2)
        canvas_frame.pack(pady=5, padx=10)
        
        self.canvas_video = tk.Canvas(
            canvas_frame,
            width=640,
            height=480,
            bg="#000000",
            highlightthickness=0
        )
        self.canvas_video.pack()
        
        # Texto inicial en el canvas
        self.canvas_video.create_text(
            320, 240,
            text="▶ Presione INICIAR CONTEO para comenzar",
            fill="#00d4ff",
            font=("Segoe UI", 14),
            tags="texto_inicio"
        )
        
        # ========== PANEL DERECHO con Scroll ==========
        self.frame_derecho = tk.Frame(self.frame_principal, bg="#1a1a2e", width=380)
        self.frame_derecho.pack(side="right", fill="both", padx=(0, 0))
        self.frame_derecho.pack_propagate(False)
        
        # Canvas con scroll para el panel derecho
        canvas_scroll = tk.Canvas(self.frame_derecho, bg="#1a1a2e", highlightthickness=0)
        scrollbar = tk.Scrollbar(self.frame_derecho, orient="vertical", command=canvas_scroll.yview)
        self.frame_scroll_content = tk.Frame(canvas_scroll, bg="#1a1a2e")
        
        self.frame_scroll_content.bind(
            "<Configure>",
            lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
        )
        
        canvas_scroll.create_window((0, 0), window=self.frame_scroll_content, anchor="nw", width=360)
        canvas_scroll.configure(yscrollcommand=scrollbar.set)
        
        # Scroll con rueda del ratón
        def _on_mousewheel(event):
            canvas_scroll.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas_scroll.bind_all("<MouseWheel>", _on_mousewheel)
        
        scrollbar.pack(side="right", fill="y")
        canvas_scroll.pack(side="left", fill="both", expand=True)
        
        # Panel de información
        self.panel_info = PanelInfo(self.frame_scroll_content)
        self.panel_info.pack(fill="x", pady=(0, 5))
        
        # ===== PANEL DE CONTROLES PRINCIPALES =====
        frame_controles_principales = tk.Frame(self.frame_scroll_content, bg="#1a1a2e", padx=15, pady=10)
        frame_controles_principales.pack(fill="x", pady=(0, 5))
        
        tk.Label(
            frame_controles_principales,
            text="⚡ CONTROLES",
            font=("Segoe UI", 12, "bold"),
            fg="#00d4ff",
            bg="#1a1a2e"
        ).pack(pady=(0, 10))
        
        # Frame para botones en grid
        btn_frame = tk.Frame(frame_controles_principales, bg="#1a1a2e")
        btn_frame.pack(fill="x")
        
        btn_style = {
            'font': ("Segoe UI", 10, "bold"),
            'width': 16,
            'height': 2,
            'cursor': "hand2",
            'relief': "flat",
            'bd': 0,
        }
        
        # Botón Iniciar
        self.btn_iniciar = tk.Button(
            btn_frame,
            text="▶  INICIAR",
            bg="#00c853",
            fg="white",
            activebackground="#00e676",
            activeforeground="white",
            command=self._on_iniciar,
            **btn_style
        )
        self.btn_iniciar.grid(row=0, column=0, padx=5, pady=5)
        
        # Botón Pausar
        self.btn_pausar = tk.Button(
            btn_frame,
            text="⏸  PAUSAR",
            bg="#ff9800",
            fg="white",
            activebackground="#ffc107",
            activeforeground="white",
            command=self._on_pausar,
            state="disabled",
            **btn_style
        )
        self.btn_pausar.grid(row=0, column=1, padx=5, pady=5)
        
        # Botón Detener/Reiniciar
        self.btn_detener = tk.Button(
            btn_frame,
            text="⏹  DETENER",
            bg="#f44336",
            fg="white",
            activebackground="#ef5350",
            activeforeground="white",
            command=self._on_detener,
            state="disabled",
            **btn_style
        )
        self.btn_detener.grid(row=1, column=0, padx=5, pady=5)
        
        # Botón Exportar
        self.btn_exportar = tk.Button(
            btn_frame,
            text="📊 EXPORTAR CSV",
            bg="#2196f3",
            fg="white",
            activebackground="#42a5f5",
            activeforeground="white",
            command=self._on_exportar,
            **btn_style
        )
        self.btn_exportar.grid(row=1, column=1, padx=5, pady=5)
        
        # Botón Reiniciar Contadores
        self.btn_reiniciar = tk.Button(
            btn_frame,
            text="🔄 REINICIAR CONTEO",
            bg="#9c27b0",
            fg="white",
            activebackground="#ab47bc",
            activeforeground="white",
            command=self._on_reiniciar,
            font=("Segoe UI", 10, "bold"),
            width=34,
            height=1,
            cursor="hand2",
            relief="flat",
            bd=0
        )
        self.btn_reiniciar.grid(row=2, column=0, columnspan=2, padx=5, pady=10)
        
        # Separador
        tk.Frame(frame_controles_principales, bg="#00d4ff", height=2).pack(fill="x", pady=10)
        
        # ===== CONFIGURACIÓN DE UBICACIÓN =====
        tk.Label(
            frame_controles_principales,
            text="📍 CAMBIAR UBICACIÓN",
            font=("Segoe UI", 10, "bold"),
            fg="#ffd700",
            bg="#1a1a2e"
        ).pack(anchor="w", pady=(5, 5))
        
        ubicacion_frame = tk.Frame(frame_controles_principales, bg="#1a1a2e")
        ubicacion_frame.pack(fill="x", pady=5)
        
        self.entry_nueva_ubicacion = tk.Entry(
            ubicacion_frame,
            font=("Segoe UI", 10),
            width=22,
            bg="#16213e",
            fg="#ffffff",
            insertbackground="#00d4ff",
            relief="flat",
            bd=5
        )
        self.entry_nueva_ubicacion.pack(side="left", padx=(0, 5))
        
        self.btn_cambiar_ubicacion = tk.Button(
            ubicacion_frame,
            text="✓ Aplicar",
            bg="#00bcd4",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            cursor="hand2",
            command=self._on_cambiar_ubicacion
        )
        self.btn_cambiar_ubicacion.pack(side="left")
        
        # Separador
        tk.Frame(frame_controles_principales, bg="#00d4ff", height=2).pack(fill="x", pady=10)
        
        # ===== SLIDERS DE CONFIGURACIÓN =====
        config_label_style = {'font': ("Segoe UI", 9), 'fg': "#a0a0a0", 'bg': "#1a1a2e"}
        
        tk.Label(frame_controles_principales, text="📏 Posición de Línea", **config_label_style).pack(anchor="w")
        self.slider_linea = tk.Scale(
            frame_controles_principales,
            from_=10, to=90,
            orient="horizontal",
            bg="#1a1a2e", fg="#00d4ff",
            troughcolor="#16213e",
            highlightthickness=0,
            length=200
        )
        self.slider_linea.set(50)
        self.slider_linea.pack(pady=(0, 5))
        
        tk.Label(frame_controles_principales, text="🎯 Umbral de Confianza", **config_label_style).pack(anchor="w")
        self.slider_confianza = tk.Scale(
            frame_controles_principales,
            from_=10, to=90,
            orient="horizontal",
            bg="#1a1a2e", fg="#00d4ff",
            troughcolor="#16213e",
            highlightthickness=0,
            length=200
        )
        self.slider_confianza.set(50)
        self.slider_confianza.pack(pady=(0, 10))
        
        # Panel de contadores
        self.panel_contadores = PanelContadores(self.frame_scroll_content, self.categorias)
        self.panel_contadores.pack(fill="x", pady=(5, 10))
        
        # Configurar eventos de sliders
        self.slider_linea.config(command=self._on_cambio_linea)
        self.slider_confianza.config(command=self._on_cambio_confianza)
    
    def establecer_callbacks(
        self,
        iniciar: Callable = None,
        pausar: Callable = None,
        reiniciar: Callable = None,
        exportar: Callable = None,
        cerrar: Callable = None,
        slider_linea: Callable = None,
        slider_confianza: Callable = None
    ) -> None:
        """
        Establece los callbacks para los eventos de la interfaz.
        
        Args:
            iniciar: Callback para botón iniciar
            pausar: Callback para botón pausar
            reiniciar: Callback para botón reiniciar
            exportar: Callback para botón exportar
            cerrar: Callback para cierre de ventana
            slider_linea: Callback para cambio de posición de línea
            slider_confianza: Callback para cambio de umbral de confianza
        """
        self.callback_iniciar = iniciar
        self.callback_pausar = pausar
        self.callback_reiniciar = reiniciar
        self.callback_exportar = exportar
        self.callback_cerrar = cerrar
        self.callback_slider_linea = slider_linea
        self.callback_slider_confianza = slider_confianza
    
    def _on_iniciar(self) -> None:
        """Handler para botón iniciar."""
        self.ejecutando = True
        self.pausado = False
        self.canvas_video.delete("texto_inicio")
        self._actualizar_botones()
        self.panel_info.actualizar_estado('ejecutando')
        
        if self.callback_iniciar:
            self.callback_iniciar()
    
    def _on_pausar(self) -> None:
        """Handler para botón pausar."""
        self.pausado = not self.pausado
        self._actualizar_botones()
        self.panel_info.actualizar_estado('pausado' if self.pausado else 'ejecutando')
        
        if self.callback_pausar:
            self.callback_pausar()
    
    def _on_detener(self) -> None:
        """Handler para botón detener - para la captura pero mantiene contadores."""
        self.ejecutando = False
        self.pausado = False
        self._actualizar_botones()
        self.panel_info.actualizar_estado('detenido')
        
        # Mostrar mensaje en canvas
        self.canvas_video.delete("all")
        self.canvas_video.create_text(
            320, 240,
            text="⏹ Captura detenida\n\nPuede cambiar la ubicación y\npresionar INICIAR para continuar",
            fill="#ffd700",
            font=("Segoe UI", 12),
            justify="center"
        )
        
        if self.callback_cerrar:
            self.callback_cerrar()
    
    def _on_reiniciar(self) -> None:
        """Handler para botón reiniciar contadores."""
        respuesta = messagebox.askyesno(
            "Confirmar Reinicio",
            "¿Está seguro de que desea reiniciar todos los contadores?\n\nEsta acción no se puede deshacer."
        )
        
        if respuesta and self.callback_reiniciar:
            self.callback_reiniciar()
    
    def _on_exportar(self) -> None:
        """Handler para botón exportar."""
        if self.callback_exportar:
            self.callback_exportar()
    
    def _on_cambiar_ubicacion(self) -> None:
        """Handler para cambiar la ubicación."""
        nueva_ubicacion = self.entry_nueva_ubicacion.get().strip()
        if nueva_ubicacion:
            self.panel_info.establecer_ubicacion(nueva_ubicacion)
            self.entry_nueva_ubicacion.delete(0, tk.END)
            messagebox.showinfo("Ubicación Actualizada", f"Nueva ubicación: {nueva_ubicacion}")
        else:
            messagebox.showwarning("Aviso", "Ingrese un nombre de ubicación válido")
    
    def _actualizar_botones(self) -> None:
        """Actualiza el estado de todos los botones según el estado actual."""
        if self.ejecutando and not self.pausado:
            self.btn_iniciar.config(state="disabled")
            self.btn_pausar.config(state="normal", text="⏸  PAUSAR", bg="#ff9800")
            self.btn_detener.config(state="normal")
        elif self.ejecutando and self.pausado:
            self.btn_iniciar.config(state="disabled")
            self.btn_pausar.config(state="normal", text="▶  REANUDAR", bg="#4caf50")
            self.btn_detener.config(state="normal")
        else:
            self.btn_iniciar.config(state="normal")
            self.btn_pausar.config(state="disabled", text="⏸  PAUSAR", bg="#ff9800")
            self.btn_detener.config(state="disabled")
    
    def _on_cerrar(self) -> None:
        """Handler para cierre de ventana."""
        respuesta = messagebox.askyesno(
            "Confirmar Salida",
            "¿Está seguro de que desea salir?\n\nLos datos se guardarán automáticamente."
        )
        
        if respuesta:
            self.ejecutando = False
            if self.callback_cerrar:
                self.callback_cerrar()
            self.root.destroy()
    
    def _on_cambio_linea(self, valor) -> None:
        """Handler para cambio en slider de línea."""
        if self.callback_slider_linea:
            self.callback_slider_linea(float(valor) / 100.0)
    
    def _on_cambio_confianza(self, valor) -> None:
        """Handler para cambio en slider de confianza."""
        if self.callback_slider_confianza:
            self.callback_slider_confianza(float(valor) / 100.0)
    
    def _actualizar_tiempo(self) -> None:
        """Actualiza el timestamp periódicamente."""
        self.panel_info.actualizar_tiempo()
        self.root.after(1000, self._actualizar_tiempo)
    
    def actualizar_frame(self, frame) -> None:
        """
        Actualiza el frame de video en el canvas.
        
        Args:
            frame: Frame de OpenCV (BGR)
        """
        if frame is None:
            return
        
        try:
            # Convertir BGR a RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Redimensionar si es necesario
            alto_canvas = self.canvas_video.winfo_height()
            ancho_canvas = self.canvas_video.winfo_width()
            
            if alto_canvas > 1 and ancho_canvas > 1:
                frame_rgb = cv2.resize(frame_rgb, (ancho_canvas, alto_canvas))
            
            # Convertir a imagen de PIL y luego a PhotoImage
            imagen = Image.fromarray(frame_rgb)
            self.imagen_tk = ImageTk.PhotoImage(image=imagen)
            
            # Actualizar canvas
            self.canvas_video.delete("all")
            self.canvas_video.create_image(0, 0, anchor="nw", image=self.imagen_tk)
            
        except Exception as e:
            logger.error(f"Error al actualizar frame: {e}")
    
    def actualizar_contadores(self, contadores: Dict) -> None:
        """
        Actualiza los contadores en la interfaz.
        
        Args:
            contadores: Diccionario con los contadores por categoría
        """
        self.panel_contadores.actualizar_contadores(contadores)
    
    def actualizar_fps(self, fps: float) -> None:
        """
        Actualiza el contador de FPS.
        
        Args:
            fps: Frames por segundo actuales
        """
        self.panel_info.actualizar_fps(fps)
    
    def actualizar_gps(self, lat: Optional[float], lon: Optional[float]) -> None:
        """
        Actualiza las coordenadas GPS.
        
        Args:
            lat: Latitud
            lon: Longitud
        """
        self.panel_info.actualizar_gps(lat, lon)
    
    def mostrar_alerta_movilidad_reducida(self) -> None:
        """Muestra una alerta visual para persona con movilidad reducida."""
        AlertaMovilidadReducida(self.root)
    
    def obtener_ubicacion(self) -> str:
        """Obtiene el nombre de ubicación ingresado por el usuario."""
        return self.panel_info.obtener_ubicacion()
    
    def establecer_ubicacion(self, ubicacion: str) -> None:
        """Establece el nombre de ubicación en el campo de texto."""
        self.panel_info.establecer_ubicacion(ubicacion)
    
    def mostrar_mensaje(self, titulo: str, mensaje: str, tipo: str = "info") -> None:
        """
        Muestra un mensaje al usuario.
        
        Args:
            titulo: Título del mensaje
            mensaje: Contenido del mensaje
            tipo: Tipo de mensaje ('info', 'warning', 'error')
        """
        if tipo == "info":
            messagebox.showinfo(titulo, mensaje)
        elif tipo == "warning":
            messagebox.showwarning(titulo, mensaje)
        elif tipo == "error":
            messagebox.showerror(titulo, mensaje)
    
    def seleccionar_archivo_guardar(self, extension: str = ".csv") -> str:
        """
        Abre diálogo para seleccionar archivo de guardado.
        
        Args:
            extension: Extensión del archivo
            
        Returns:
            Ruta seleccionada o string vacío
        """
        ruta = filedialog.asksaveasfilename(
            defaultextension=extension,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        return ruta
    
    def iniciar(self) -> None:
        """Inicia el bucle principal de la interfaz."""
        self.root.mainloop()
    
    def detener(self) -> None:
        """Detiene la interfaz y cierra la ventana."""
        self.ejecutando = False
        self.root.quit()
    
    def esta_ejecutando(self) -> bool:
        """Retorna si la interfaz está activa."""
        return self.ejecutando
    
    def esta_pausado(self) -> bool:
        """Retorna si está en pausa."""
        return self.pausado
