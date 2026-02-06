# -*- coding: utf-8 -*-
"""
Módulo GUI 2026 - Interfaz Ultra Moderna con Glassmorphism y Diseño Premium
Sistema de Conteo Bidireccional YoloConteo
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Callable, Tuple
import logging
import os
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar selector de ubicación
try:
    from selector_ubicacion import abrir_selector_ubicacion, MAPA_DISPONIBLE
except ImportError:
    MAPA_DISPONIBLE = False
    def abrir_selector_ubicacion(*args, **kwargs):
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 🎨 PALETA DE COLORES - DISEÑO BLANCO Y NEGRO MINIMALISTA
# ═══════════════════════════════════════════════════════════════════════════════

class Colors:
    """Paleta de colores blanco y negro minimalista."""
    
    # Fondos principales (negro)
    BG_DARK = "#0a0a0a"
    BG_CARD = "#1a1a1a"
    BG_CARD_HOVER = "#2a2a2a"
    BG_GLASS = "#151515"
    
    # Acentos primarios (blanco/gris)
    PRIMARY = "#ffffff"
    PRIMARY_LIGHT = "#e5e5e5"
    PRIMARY_DARK = "#cccccc"
    
    # Acentos secundarios (grises)
    ACCENT_CYAN = "#b0b0b0"
    ACCENT_PINK = "#909090"
    ACCENT_PURPLE = "#707070"
    
    # Estados (tonos de gris)
    SUCCESS = "#e0e0e0"       # Gris claro para éxito
    SUCCESS_LIGHT = "#f0f0f0"
    WARNING = "#a0a0a0"       # Gris medio para advertencia
    WARNING_LIGHT = "#c0c0c0"
    DANGER = "#808080"        # Gris oscuro para peligro
    DANGER_LIGHT = "#999999"
    
    # Textos
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#b0b0b0"
    TEXT_MUTED = "#707070"
    
    # Bordes
    BORDER = "#333333"
    BORDER_LIGHT = "#444444"
    
    # Gradientes (colores para simular)
    GRADIENT_START = "#ffffff"
    GRADIENT_END = "#808080"


# ═══════════════════════════════════════════════════════════════════════════════
# 🎴 COMPONENTES VISUALES MODERNOS
# ═══════════════════════════════════════════════════════════════════════════════

class GlassCard(tk.Frame):
    """Tarjeta con efecto glassmorphism."""
    
    def __init__(self, parent, title: str = "", icon: str = "", **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg=Colors.BG_CARD, highlightthickness=1, 
                      highlightbackground=Colors.BORDER)
        
        # Header con icono y título
        if title or icon:
            header = tk.Frame(self, bg=Colors.BG_CARD)
            header.pack(fill="x", padx=16, pady=(12, 8))
            
            if icon:
                tk.Label(header, text=icon, font=("Segoe UI Emoji", 14), 
                        fg=Colors.PRIMARY_LIGHT, bg=Colors.BG_CARD).pack(side="left")
            
            if title:
                tk.Label(header, text=title.upper(), font=("Segoe UI", 10, "bold"),
                        fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                        ).pack(side="left", padx=(8 if icon else 0, 0))
        
        # Contenedor interno
        self.content = tk.Frame(self, bg=Colors.BG_CARD)
        self.content.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        
    def get_content(self):
        return self.content


class ModernButton(tk.Canvas):
    """Botón moderno con efecto hover y animaciones."""
    
    def __init__(self, parent, text: str, icon: str = "", command: Callable = None,
                 bg_color: str = Colors.PRIMARY, fg_color: str = Colors.TEXT_PRIMARY,
                 width: int = 120, height: int = 38, **kwargs):
        super().__init__(parent, width=width, height=height, 
                        highlightthickness=0, bg=Colors.BG_CARD, **kwargs)
        
        self.text = text
        self.icon = icon
        self.command = command
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover = False
        self.enabled = True
        self.width = width
        self.height = height
        
        self._draw()
        
        # Eventos
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
    
    def _draw(self):
        self.delete("all")
        
        # Color según estado
        if not self.enabled:
            fill = Colors.TEXT_MUTED
            text_color = Colors.BG_CARD
        elif self.hover:
            fill = self._lighten_color(self.bg_color, 20)
            text_color = self.fg_color
        else:
            fill = self.bg_color
            text_color = self.fg_color
        
        # Dibujar rectángulo redondeado
        self._round_rectangle(2, 2, self.width-2, self.height-2, 8, fill=fill)
        
        # Texto con icono
        display_text = f"{self.icon} {self.text}" if self.icon else self.text
        self.create_text(self.width//2, self.height//2, text=display_text,
                        fill=text_color, font=("Segoe UI", 9, "bold"))
    
    def _round_rectangle(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def _lighten_color(self, color: str, amount: int) -> str:
        color = color.lstrip('#')
        r = min(255, int(color[0:2], 16) + amount)
        g = min(255, int(color[2:4], 16) + amount)
        b = min(255, int(color[4:6], 16) + amount)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def _on_enter(self, event):
        if self.enabled:
            self.hover = True
            self._draw()
    
    def _on_leave(self, event):
        self.hover = False
        self._draw()
    
    def _on_click(self, event):
        if self.enabled and self.command:
            self.command()
    
    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self._draw()
    
    def configure_button(self, **kwargs):
        if 'text' in kwargs:
            self.text = kwargs['text']
        if 'bg_color' in kwargs:
            self.bg_color = kwargs['bg_color']
        if 'icon' in kwargs:
            self.icon = kwargs['icon']
        self._draw()


class AnimatedCounter(tk.Frame):
    """Contador animado con efecto de incremento suave."""
    
    def __init__(self, parent, label: str, color: str = Colors.SUCCESS, 
                 direction: str = "→", **kwargs):
        super().__init__(parent, bg=Colors.BG_DARK, **kwargs)
        
        self.current_value = 0
        self.target_value = 0
        self.color = color
        self.direction = direction
        
        # Dirección
        self.lbl_dir = tk.Label(self, text=direction, font=("Segoe UI", 16, "bold"),
                               fg=color, bg=Colors.BG_DARK)
        self.lbl_dir.pack()
        
        # Valor
        self.lbl_value = tk.Label(self, text="0", font=("Segoe UI", 32, "bold"),
                                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_DARK)
        self.lbl_value.pack()
        
        # Label
        self.lbl_label = tk.Label(self, text=label, font=("Segoe UI", 9),
                                 fg=Colors.TEXT_MUTED, bg=Colors.BG_DARK)
        self.lbl_label.pack()
    
    def set_value(self, value: int):
        self.target_value = value
        self._animate()
    
    def _animate(self):
        if self.current_value != self.target_value:
            diff = self.target_value - self.current_value
            step = max(1, abs(diff) // 5) * (1 if diff > 0 else -1)
            self.current_value += step
            
            if (diff > 0 and self.current_value > self.target_value) or \
               (diff < 0 and self.current_value < self.target_value):
                self.current_value = self.target_value
            
            self.lbl_value.config(text=str(self.current_value))
            self.after(30, self._animate)


class CategoryCard(tk.Frame):
    """Tarjeta de categoría con barra de progreso visual."""
    
    def __init__(self, parent, name: str, color: str, icon: str = "●", **kwargs):
        super().__init__(parent, bg=Colors.BG_CARD, **kwargs)
        self.configure(highlightthickness=1, highlightbackground=Colors.BORDER)
        
        self.color = color
        self.izq_der = 0
        self.der_izq = 0
        self.max_value = 1
        
        # Contenedor principal
        content = tk.Frame(self, bg=Colors.BG_CARD, padx=12, pady=10)
        content.pack(fill="x")
        
        # Fila superior: icono + nombre
        top_row = tk.Frame(content, bg=Colors.BG_CARD)
        top_row.pack(fill="x")
        
        # Indicador de color
        self.color_indicator = tk.Canvas(top_row, width=12, height=12, 
                                         bg=Colors.BG_CARD, highlightthickness=0)
        self.color_indicator.pack(side="left", padx=(0, 8))
        self.color_indicator.create_oval(2, 2, 10, 10, fill=color, outline="")
        
        # Nombre
        tk.Label(top_row, text=name, font=("Segoe UI", 10, "bold"),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(side="left")
        
        # Total
        self.lbl_total = tk.Label(top_row, text="0", font=("Segoe UI", 10, "bold"),
                                 fg=Colors.TEXT_MUTED, bg=Colors.BG_CARD)
        self.lbl_total.pack(side="right")
        
        # Barra de progreso visual
        self.bar_frame = tk.Frame(content, bg=Colors.BG_DARK, height=6)
        self.bar_frame.pack(fill="x", pady=(8, 6))
        
        self.bar_canvas = tk.Canvas(self.bar_frame, height=6, bg=Colors.BG_DARK, 
                                   highlightthickness=0)
        self.bar_canvas.pack(fill="x")
        
        # Fila inferior: contadores
        bottom_row = tk.Frame(content, bg=Colors.BG_CARD)
        bottom_row.pack(fill="x")
        
        # Dirección 1
        self.lbl_der = tk.Label(bottom_row, text="Dir.1: 0", font=("Segoe UI", 11, "bold"),
                               fg=Colors.SUCCESS, bg=Colors.BG_CARD)
        self.lbl_der.pack(side="left")
        
        # Dirección 2
        self.lbl_izq = tk.Label(bottom_row, text="Dir.2: 0", font=("Segoe UI", 11, "bold"),
                               fg=Colors.DANGER, bg=Colors.BG_CARD)
        self.lbl_izq.pack(side="right")
    
    def update(self, izq_der: int, der_izq: int, max_val: int = 1):
        self.izq_der = izq_der
        self.der_izq = der_izq
        self.max_value = max(1, max_val)
        
        self.lbl_der.config(text=f"Dir.1: {izq_der}")
        self.lbl_izq.config(text=f"Dir.2: {der_izq}")
        self.lbl_total.config(text=str(izq_der + der_izq))
        
        self._draw_bar()
    
    def _draw_bar(self):
        self.bar_canvas.delete("all")
        width = self.bar_canvas.winfo_width()
        if width < 10:
            width = 200
        
        total = self.izq_der + self.der_izq
        if total > 0:
            # Proporción de cada dirección
            ratio_der = self.izq_der / total
            ratio_izq = self.der_izq / total
            
            # Ancho de la barra según el total vs max
            bar_ratio = min(1.0, total / self.max_value)
            bar_width = int(width * bar_ratio)
            
            # Dibujar barra verde (izq a der)
            green_width = int(bar_width * ratio_der)
            if green_width > 0:
                self.bar_canvas.create_rectangle(0, 0, green_width, 6, 
                                                fill=Colors.SUCCESS, outline="")
            
            # Dibujar barra roja (der a izq)
            if bar_width - green_width > 0:
                self.bar_canvas.create_rectangle(green_width, 0, bar_width, 6,
                                                fill=Colors.DANGER, outline="")


class PulsingDot(tk.Canvas):
    """Punto pulsante para indicar estado activo."""
    
    def __init__(self, parent, color: str = Colors.SUCCESS, size: int = 12, **kwargs):
        super().__init__(parent, width=size+4, height=size+4, 
                        highlightthickness=0, **kwargs)
        
        self.color = color
        self.size = size
        self.pulse_size = 0
        self.animating = False
        self._draw()
    
    def _draw(self):
        self.delete("all")
        center = (self.size + 4) // 2
        
        # Halo pulsante
        if self.pulse_size > 0:
            self.create_oval(center - self.size//2 - self.pulse_size,
                           center - self.size//2 - self.pulse_size,
                           center + self.size//2 + self.pulse_size,
                           center + self.size//2 + self.pulse_size,
                           fill="", outline=self.color, width=1)
        
        # Punto principal
        self.create_oval(center - self.size//4, center - self.size//4,
                        center + self.size//4, center + self.size//4,
                        fill=self.color, outline="")
    
    def start_pulse(self):
        self.animating = True
        self._animate_pulse()
    
    def stop_pulse(self):
        self.animating = False
        self.pulse_size = 0
        self._draw()
    
    def _animate_pulse(self):
        if not self.animating:
            return
        
        self.pulse_size = (self.pulse_size + 1) % 8
        self._draw()
        self.after(100, self._animate_pulse)
    
    def set_color(self, color: str):
        self.color = color
        self._draw()


# ═══════════════════════════════════════════════════════════════════════════════
# 🖥️ INTERFAZ PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class GUI:
    """Interfaz gráfica minimalista blanco y negro - Creado por David Antízar."""
    
    def __init__(
        self,
        titulo: str = "YoloConteo Dashboard",
        ancho: int = 1400,
        alto: int = 850,
        categorias: Dict = None
    ):
        self.ancho = ancho
        self.alto = alto
        
        # Colores en escala de grises para categorías (sin patinete)
        self.categorias = categorias or {
            'adulto': {'nombre': 'Adultos', 'color_hex': '#ffffff'},
            'nino': {'nombre': 'Niños', 'color_hex': '#d0d0d0'},
            'bicicleta': {'nombre': 'Bicicletas', 'color_hex': '#a0a0a0'},
            'silla_ruedas': {'nombre': 'Sillas de Ruedas', 'color_hex': '#808080'},
            'movilidad_reducida': {'nombre': 'Movilidad Reducida', 'color_hex': '#606060'},
        }
        
        # Ventana principal
        self.root = tk.Tk()
        self.root.title(titulo)
        self.root.geometry(f"{ancho}x{alto}")
        self.root.minsize(1000, 700)
        self.root.configure(bg=Colors.BG_DARK)
        
        # Configurar estilo ttk
        self._configurar_estilos()
        
        # Variables de estado
        self.ejecutando = False
        self.pausado = False
        self.imagen_tk = None
        self.carpeta_datos = "datos"
        self.tiempo_sesion = 0
        self.timer_activo = False
        
        # Callbacks
        self.callback_iniciar = None
        self.callback_pausar = None
        self.callback_reiniciar = None
        self.callback_exportar = None
        self.callback_cerrar = None
        self.callback_slider_linea = None
        self.callback_slider_confianza = None
        self.callback_cambiar_ubicacion = None
        self.callback_captura = None
        
        # Widgets
        self.contador_widgets: Dict[str, CategoryCard] = {}
        self.buttons: Dict[str, ModernButton] = {}
        
        self._construir_interfaz()
        self.root.protocol("WM_DELETE_WINDOW", self._on_cerrar_ventana)
        self._actualizar_reloj()
    
    def _configurar_estilos(self):
        """Configura estilos personalizados para widgets ttk."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Slider personalizado
        style.configure("Modern.Horizontal.TScale",
                       background=Colors.BG_CARD,
                       troughcolor=Colors.BG_DARK,
                       sliderthickness=16,
                       sliderlength=20)
    
    def _construir_interfaz(self):
        """Construye la interfaz premium 2026."""
        
        # ══════════════ BARRA SUPERIOR (NAVBAR) ══════════════
        navbar = tk.Frame(self.root, bg=Colors.BG_CARD, height=56)
        navbar.pack(fill="x")
        navbar.pack_propagate(False)
        
        # Contenedor interno del navbar
        navbar_inner = tk.Frame(navbar, bg=Colors.BG_CARD)
        navbar_inner.pack(fill="both", expand=True, padx=20)
        
        # Logo y branding
        brand = tk.Frame(navbar_inner, bg=Colors.BG_CARD)
        brand.pack(side="left", pady=10)
        
        # Logo animado
        self.logo_dot = PulsingDot(brand, color=Colors.DANGER, size=14, bg=Colors.BG_CARD)
        self.logo_dot.pack(side="left")
        
        tk.Label(brand, text="YOLO", font=("Segoe UI", 14, "bold"),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(side="left", padx=(8, 0))
        tk.Label(brand, text="Conteo", font=("Segoe UI", 14),
                fg=Colors.PRIMARY_LIGHT, bg=Colors.BG_CARD).pack(side="left")
        
        # Navegación central
        nav_menu = tk.Frame(navbar_inner, bg=Colors.BG_CARD)
        nav_menu.pack(side="left", padx=40)
        
        self.nav_items = {}
        for item, text in [("dashboard", "Dashboard"), ("history", "Historial"), ("help", "Ayuda")]:
            btn = tk.Label(nav_menu, text=text, font=("Segoe UI", 10),
                          fg=Colors.TEXT_PRIMARY if item == "dashboard" else Colors.TEXT_MUTED,
                          bg=Colors.BG_CARD, cursor="hand2", padx=16)
            btn.pack(side="left")
            btn.bind("<Enter>", lambda e, b=btn: b.config(fg=Colors.PRIMARY_LIGHT))
            btn.bind("<Leave>", lambda e, b=btn, i=item: b.config(
                fg=Colors.TEXT_PRIMARY if i == "dashboard" else Colors.TEXT_MUTED))
            
            if item == "history":
                btn.bind("<Button-1>", lambda e: self._mostrar_historial())
            elif item == "help":
                btn.bind("<Button-1>", lambda e: self._mostrar_ayuda())
            
            self.nav_items[item] = btn
        
        # Panel derecho del navbar
        nav_right = tk.Frame(navbar_inner, bg=Colors.BG_CARD)
        nav_right.pack(side="right")
        
        # Crédito del autor
        tk.Label(nav_right, text="Creado por David Antízar",
                font=("Segoe UI", 8), fg=Colors.TEXT_MUTED, bg=Colors.BG_CARD).pack(side="left", padx=(0, 20))
        
        # Fecha
        self.lbl_fecha = tk.Label(nav_right, text=datetime.now().strftime("%d %b %Y"),
                                 font=("Segoe UI", 9), fg=Colors.TEXT_MUTED, bg=Colors.BG_CARD)
        self.lbl_fecha.pack(side="left", padx=(0, 16))
        
        # Reloj
        self.lbl_reloj = tk.Label(nav_right, text="00:00:00",
                                 font=("Segoe UI Semibold", 12),
                                 fg=Colors.WARNING, bg=Colors.BG_CARD)
        self.lbl_reloj.pack(side="left")
        
        # ══════════════ CONTENIDO PRINCIPAL ══════════════
        main = tk.Frame(self.root, bg=Colors.BG_DARK)
        main.pack(fill="both", expand=True, padx=16, pady=16)
        
        # Grid responsive
        main.columnconfigure(0, weight=7)   # Panel video
        main.columnconfigure(1, weight=3)   # Panel lateral
        main.rowconfigure(0, weight=1)
        
        # ═══════ PANEL IZQUIERDO ═══════
        left_panel = tk.Frame(main, bg=Colors.BG_DARK)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left_panel.rowconfigure(0, weight=1)
        left_panel.rowconfigure(1, weight=0)
        left_panel.columnconfigure(0, weight=1)
        
        # ─── Video Card ───
        video_card = GlassCard(left_panel, title="Video en Tiempo Real", icon="📹")
        video_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        video_content = video_card.get_content()
        video_content.rowconfigure(0, weight=0)
        video_content.rowconfigure(1, weight=1)
        video_content.columnconfigure(0, weight=1)
        
        # Status bar del video
        status_bar = tk.Frame(video_content, bg=Colors.BG_CARD)
        status_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        
        # Indicador de estado
        status_left = tk.Frame(status_bar, bg=Colors.BG_CARD)
        status_left.pack(side="left")
        
        self.status_dot = PulsingDot(status_left, color=Colors.DANGER, size=10, bg=Colors.BG_CARD)
        self.status_dot.pack(side="left")
        
        self.lbl_estado = tk.Label(status_left, text="DETENIDO", 
                                   font=("Segoe UI", 9, "bold"),
                                   fg=Colors.DANGER, bg=Colors.BG_CARD)
        self.lbl_estado.pack(side="left", padx=(6, 0))
        
        # FPS y tiempo
        status_right = tk.Frame(status_bar, bg=Colors.BG_CARD)
        status_right.pack(side="right")
        
        self.lbl_tiempo_sesion = tk.Label(status_right, text="⏱ 00:00:00",
                                         font=("Segoe UI", 9),
                                         fg=Colors.TEXT_MUTED, bg=Colors.BG_CARD)
        self.lbl_tiempo_sesion.pack(side="right", padx=(16, 0))
        
        self.lbl_fps = tk.Label(status_right, text="FPS: --",
                               font=("Segoe UI", 9),
                               fg=Colors.TEXT_MUTED, bg=Colors.BG_CARD)
        self.lbl_fps.pack(side="right")
        
        # Canvas de video
        video_frame = tk.Frame(video_content, bg=Colors.BG_DARK, 
                              highlightthickness=2, highlightbackground=Colors.BORDER)
        video_frame.grid(row=1, column=0, sticky="nsew")
        video_frame.rowconfigure(0, weight=1)
        video_frame.columnconfigure(0, weight=1)
        
        self.canvas_video = tk.Canvas(video_frame, bg="#000000", highlightthickness=0)
        self.canvas_video.grid(row=0, column=0, sticky="nsew")
        
        # Mensaje inicial estilizado
        self.canvas_video.create_text(400, 240, 
            text="▶  PRESIONE INICIAR PARA COMENZAR",
            fill=Colors.PRIMARY_LIGHT, font=("Segoe UI", 14, "bold"))
        self.canvas_video.create_text(400, 280,
            text="Sistema de detección y conteo bidireccional",
            fill=Colors.TEXT_MUTED, font=("Segoe UI", 10))
        
        # ─── Controls Card ───
        controls_card = GlassCard(left_panel, title="Controles", icon="🎮")
        controls_card.grid(row=1, column=0, sticky="ew")
        controls_content = controls_card.get_content()
        
        # Fila de botones
        btn_row = tk.Frame(controls_content, bg=Colors.BG_CARD)
        btn_row.pack(fill="x", pady=(0, 12))
        
        # Botones principales con diseño moderno
        self.buttons['iniciar'] = ModernButton(btn_row, "INICIAR", "▶", 
                                               self._on_iniciar, Colors.SUCCESS, width=110)
        self.buttons['iniciar'].pack(side="left", padx=4)
        
        self.buttons['pausar'] = ModernButton(btn_row, "PAUSAR", "⏸",
                                              self._on_pausar, Colors.WARNING, width=110)
        self.buttons['pausar'].pack(side="left", padx=4)
        self.buttons['pausar'].set_enabled(False)
        
        self.buttons['detener'] = ModernButton(btn_row, "DETENER", "⏹",
                                               self._on_detener, Colors.DANGER, width=110)
        self.buttons['detener'].pack(side="left", padx=4)
        self.buttons['detener'].set_enabled(False)
        
        self.buttons['exportar'] = ModernButton(btn_row, "EXPORTAR", "📊",
                                                self._on_exportar, "#404040", width=115)
        self.buttons['exportar'].pack(side="left", padx=4)
        
        self.buttons['reiniciar'] = ModernButton(btn_row, "REINICIAR", "🔄",
                                                 self._on_reiniciar, Colors.ACCENT_PURPLE, width=115)
        self.buttons['reiniciar'].pack(side="left", padx=4)
        
        # Sliders row
        slider_row = tk.Frame(controls_content, bg=Colors.BG_CARD)
        slider_row.pack(fill="x")
        
        # Slider línea
        slider1_frame = tk.Frame(slider_row, bg=Colors.BG_CARD)
        slider1_frame.pack(side="left", padx=(0, 24))
        
        tk.Label(slider1_frame, text="📏 Posición Línea", font=("Segoe UI", 9),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(anchor="w")
        
        slider1_container = tk.Frame(slider1_frame, bg=Colors.BG_CARD)
        slider1_container.pack(fill="x")
        
        self.slider_linea = tk.Scale(slider1_container, from_=10, to=90, 
                                    orient="horizontal", length=180,
                                    bg=Colors.BG_CARD, fg=Colors.PRIMARY_LIGHT,
                                    troughcolor=Colors.BG_DARK, activebackground=Colors.PRIMARY,
                                    highlightthickness=0, sliderrelief="flat",
                                    command=self._on_cambio_linea)
        self.slider_linea.set(50)
        self.slider_linea.pack(side="left")
        
        self.lbl_linea_val = tk.Label(slider1_container, text="50%", width=4,
                                     font=("Segoe UI", 9, "bold"),
                                     fg=Colors.PRIMARY_LIGHT, bg=Colors.BG_CARD)
        self.lbl_linea_val.pack(side="left", padx=(8, 0))
        
        # Slider confianza
        slider2_frame = tk.Frame(slider_row, bg=Colors.BG_CARD)
        slider2_frame.pack(side="left")
        
        tk.Label(slider2_frame, text="🎯 Umbral Confianza", font=("Segoe UI", 9),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(anchor="w")
        
        slider2_container = tk.Frame(slider2_frame, bg=Colors.BG_CARD)
        slider2_container.pack(fill="x")
        
        self.slider_confianza = tk.Scale(slider2_container, from_=10, to=90,
                                        orient="horizontal", length=180,
                                        bg=Colors.BG_CARD, fg=Colors.WARNING,
                                        troughcolor=Colors.BG_DARK, activebackground=Colors.WARNING,
                                        highlightthickness=0, sliderrelief="flat",
                                        command=self._on_cambio_confianza)
        self.slider_confianza.set(50)
        self.slider_confianza.pack(side="left")
        
        self.lbl_conf_val = tk.Label(slider2_container, text="50%", width=4,
                                    font=("Segoe UI", 9, "bold"),
                                    fg=Colors.WARNING, bg=Colors.BG_CARD)
        self.lbl_conf_val.pack(side="left", padx=(8, 0))
        
        # ═══════ PANEL DERECHO ═══════
        right_panel = tk.Frame(main, bg=Colors.BG_DARK)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right_panel.rowconfigure(2, weight=1)
        right_panel.columnconfigure(0, weight=1)
        
        # ─── Ubicación Card ───
        ubicacion_card = GlassCard(right_panel, title="Ubicación", icon="📍")
        ubicacion_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ub_content = ubicacion_card.get_content()
        
        # Dirección
        self.lbl_direccion = tk.Label(ub_content, text="Esperando ubicación...",
                                     font=("Segoe UI", 10), fg=Colors.TEXT_PRIMARY,
                                     bg=Colors.BG_CARD, wraplength=280, anchor="w", justify="left")
        self.lbl_direccion.pack(fill="x", pady=(0, 8))
        
        # Coordenadas
        coords_row = tk.Frame(ub_content, bg=Colors.BG_CARD)
        coords_row.pack(fill="x", pady=(0, 8))
        
        # Lat
        lat_frame = tk.Frame(coords_row, bg=Colors.BG_DARK, padx=8, pady=4)
        lat_frame.pack(side="left", padx=(0, 8))
        tk.Label(lat_frame, text="LAT", font=("Segoe UI", 7, "bold"),
                fg=Colors.TEXT_MUTED, bg=Colors.BG_DARK).pack(side="left")
        self.entry_lat = tk.Entry(lat_frame, width=11, font=("Segoe UI", 9),
                                 bg=Colors.BG_DARK, fg=Colors.SUCCESS,
                                 insertbackground=Colors.SUCCESS, relief="flat", bd=0)
        self.entry_lat.pack(side="left", padx=(4, 0))
        
        # Lon
        lon_frame = tk.Frame(coords_row, bg=Colors.BG_DARK, padx=8, pady=4)
        lon_frame.pack(side="left")
        tk.Label(lon_frame, text="LON", font=("Segoe UI", 7, "bold"),
                fg=Colors.TEXT_MUTED, bg=Colors.BG_DARK).pack(side="left")
        self.entry_lon = tk.Entry(lon_frame, width=11, font=("Segoe UI", 9),
                                 bg=Colors.BG_DARK, fg=Colors.SUCCESS,
                                 insertbackground=Colors.SUCCESS, relief="flat", bd=0)
        self.entry_lon.pack(side="left", padx=(4, 0))
        
        # Nombre ubicación
        nombre_row = tk.Frame(ub_content, bg=Colors.BG_CARD)
        nombre_row.pack(fill="x")
        
        self.entry_ubicacion = tk.Entry(nombre_row, font=("Segoe UI", 10),
                                        bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                                        insertbackground=Colors.TEXT_PRIMARY, relief="flat")
        self.entry_ubicacion.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=6)
        self.entry_ubicacion.insert(0, "Nombre del punto...")
        self.entry_ubicacion.bind("<FocusIn>", lambda e: self._on_entry_focus(e, "Nombre del punto..."))
        
        # Botones de ubicación
        btn_ub_frame = tk.Frame(nombre_row, bg=Colors.BG_CARD)
        btn_ub_frame.pack(side="right")
        
        self.btn_mapa = tk.Button(btn_ub_frame, text="🗺️", font=("Segoe UI", 11),
                                 bg=Colors.PRIMARY, fg=Colors.TEXT_PRIMARY,
                                 relief="flat", cursor="hand2", width=3,
                                 command=self._abrir_mapa)
        self.btn_mapa.pack(side="left", padx=(0, 4))
        
        self.btn_captura = tk.Button(btn_ub_frame, text="📷", font=("Segoe UI", 11),
                                    bg="#505050", fg=Colors.TEXT_PRIMARY,
                                    relief="flat", cursor="hand2", width=3,
                                    command=self._capturar_pantalla)
        self.btn_captura.pack(side="left", padx=(0, 4))
        
        self.btn_aplicar = tk.Button(btn_ub_frame, text="✓", font=("Segoe UI", 11, "bold"),
                                    bg=Colors.SUCCESS, fg=Colors.TEXT_PRIMARY,
                                    relief="flat", cursor="hand2", width=3,
                                    command=self._on_cambiar_ubicacion)
        self.btn_aplicar.pack(side="left")
        
        # ─── Totales Card ───
        totales_card = GlassCard(right_panel, title="Totales", icon="⚡")
        totales_card.grid(row=1, column=0, sticky="ew", pady=8)
        totales_content = totales_card.get_content()
        
        # Contenedor de totales
        totales_row = tk.Frame(totales_content, bg=Colors.BG_DARK)
        totales_row.pack(fill="x", pady=8)
        
        # Total dirección 1
        self.counter_der = AnimatedCounter(totales_row, "Dirección 1", 
                                          Colors.SUCCESS, "→")
        self.counter_der.pack(side="left", expand=True)
        
        # Separador
        tk.Frame(totales_row, bg=Colors.BORDER, width=1).pack(side="left", fill="y", padx=16)
        
        # Total dirección 2
        self.counter_izq = AnimatedCounter(totales_row, "Dirección 2",
                                          Colors.DANGER, "←")
        self.counter_izq.pack(side="left", expand=True)
        
        # ─── Categorías Card ───
        cat_card = GlassCard(right_panel, title="Categorías", icon="📊")
        cat_card.grid(row=2, column=0, sticky="nsew")
        cat_content = cat_card.get_content()
        
        # Scrollable frame para categorías
        cat_scroll = tk.Frame(cat_content, bg=Colors.BG_CARD)
        cat_scroll.pack(fill="both", expand=True)
        
        # Crear cards de categoría
        for cat_key, cat_info in self.categorias.items():
            color = cat_info.get('color_hex', '#ffffff')
            if isinstance(color, tuple):
                color = '#{:02x}{:02x}{:02x}'.format(color[2], color[1], color[0])
            
            card = CategoryCard(cat_scroll, cat_info['nombre'], color)
            card.pack(fill="x", pady=4)
            self.contador_widgets[cat_key] = card
    
    # ══════════════════════════════════════════════════════════════════════════
    # 🎛️ HANDLERS Y EVENTOS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _on_entry_focus(self, event, placeholder):
        """Limpia placeholder al hacer focus."""
        if event.widget.get() == placeholder:
            event.widget.delete(0, tk.END)
    
    def _on_iniciar(self):
        self.ejecutando = True
        self.pausado = False
        self.canvas_video.delete("all")
        self._actualizar_estado_visual()
        self._iniciar_timer_sesion()
        if self.callback_iniciar:
            self.callback_iniciar()
    
    def _on_pausar(self):
        self.pausado = not self.pausado
        self._actualizar_estado_visual()
        if self.pausado:
            self._detener_timer_sesion()
        else:
            self._iniciar_timer_sesion()
        if self.callback_pausar:
            self.callback_pausar()
    
    def _on_detener(self):
        self.ejecutando = False
        self.pausado = False
        self._actualizar_estado_visual()
        self._detener_timer_sesion()
        
        # Mensaje de detenido
        self.canvas_video.delete("all")
        w = self.canvas_video.winfo_width()
        h = self.canvas_video.winfo_height()
        self.canvas_video.create_text(w//2, h//2 - 20,
            text="⏹  DETENIDO", fill=Colors.WARNING,
            font=("Segoe UI", 16, "bold"))
        self.canvas_video.create_text(w//2, h//2 + 20,
            text="Puede cambiar la ubicación y volver a iniciar",
            fill=Colors.TEXT_MUTED, font=("Segoe UI", 10))
        
        if self.callback_cerrar:
            self.callback_cerrar()
    
    def _on_reiniciar(self):
        if messagebox.askyesno("Confirmar Reinicio", 
                              "¿Reiniciar todos los contadores a cero?\n\nEsta acción no se puede deshacer.",
                              icon="warning"):
            self.tiempo_sesion = 0
            self._actualizar_display_tiempo()
            if self.callback_reiniciar:
                self.callback_reiniciar()
    
    def _on_exportar(self):
        if self.callback_exportar:
            self.callback_exportar()
    
    def _on_cambiar_ubicacion(self):
        nombre = self.entry_ubicacion.get().strip()
        if nombre == "Nombre del punto...":
            nombre = ""
        lat = self.entry_lat.get().strip()
        lon = self.entry_lon.get().strip()
        
        if self.callback_cambiar_ubicacion:
            self.callback_cambiar_ubicacion(nombre, lat, lon)
            self._mostrar_notificacion("✓ Ubicación actualizada", Colors.SUCCESS)
    
    def _capturar_pantalla(self):
        """Captura la pantalla actual del video y la guarda."""
        if self.callback_captura:
            ruta = self.callback_captura()
            if ruta:
                self._mostrar_notificacion("📷 Captura guardada", Colors.SUCCESS)
            else:
                self._mostrar_notificacion("⚠ Error al guardar captura", Colors.WARNING)
        else:
            self._mostrar_notificacion("⚠ Inicie primero la detección", Colors.WARNING)
    
    def _on_cambio_linea(self, valor):
        self.lbl_linea_val.config(text=f"{int(float(valor))}%")
        if self.callback_slider_linea:
            self.callback_slider_linea(float(valor) / 100.0)
    
    def _on_cambio_confianza(self, valor):
        self.lbl_conf_val.config(text=f"{int(float(valor))}%")
        if self.callback_slider_confianza:
            self.callback_slider_confianza(float(valor) / 100.0)
    
    def _on_cerrar_ventana(self):
        if messagebox.askyesno("Salir", "¿Cerrar YoloConteo?\n\nLos datos no guardados se perderán."):
            self.ejecutando = False
            if self.callback_cerrar:
                self.callback_cerrar()
            self.root.destroy()
    
    def _actualizar_estado_visual(self):
        """Actualiza todos los elementos visuales según el estado."""
        if self.ejecutando and not self.pausado:
            # Activo
            self.lbl_estado.config(text="ACTIVO", fg=Colors.SUCCESS)
            self.status_dot.set_color(Colors.SUCCESS)
            self.status_dot.start_pulse()
            self.logo_dot.set_color(Colors.SUCCESS)
            self.logo_dot.start_pulse()
            
            self.buttons['iniciar'].set_enabled(False)
            self.buttons['pausar'].set_enabled(True)
            self.buttons['pausar'].configure_button(text="PAUSAR", icon="⏸", bg_color=Colors.WARNING)
            self.buttons['detener'].set_enabled(True)
            
        elif self.ejecutando and self.pausado:
            # Pausado
            self.lbl_estado.config(text="PAUSADO", fg=Colors.WARNING)
            self.status_dot.set_color(Colors.WARNING)
            self.status_dot.stop_pulse()
            self.logo_dot.set_color(Colors.WARNING)
            self.logo_dot.stop_pulse()
            
            self.buttons['iniciar'].set_enabled(False)
            self.buttons['pausar'].set_enabled(True)
            self.buttons['pausar'].configure_button(text="REANUDAR", icon="▶", bg_color=Colors.SUCCESS)
            self.buttons['detener'].set_enabled(True)
            
        else:
            # Detenido
            self.lbl_estado.config(text="DETENIDO", fg=Colors.DANGER)
            self.status_dot.set_color(Colors.DANGER)
            self.status_dot.stop_pulse()
            self.logo_dot.set_color(Colors.DANGER)
            self.logo_dot.stop_pulse()
            
            self.buttons['iniciar'].set_enabled(True)
            self.buttons['pausar'].set_enabled(False)
            self.buttons['pausar'].configure_button(text="PAUSAR", icon="⏸", bg_color=Colors.WARNING)
            self.buttons['detener'].set_enabled(False)
    
    def _iniciar_timer_sesion(self):
        """Inicia el timer de sesión."""
        self.timer_activo = True
        self._tick_timer()
    
    def _detener_timer_sesion(self):
        """Detiene el timer de sesión."""
        self.timer_activo = False
    
    def _tick_timer(self):
        """Incrementa el timer cada segundo."""
        if self.timer_activo:
            self.tiempo_sesion += 1
            self._actualizar_display_tiempo()
            self.root.after(1000, self._tick_timer)
    
    def _actualizar_display_tiempo(self):
        """Actualiza el display del tiempo de sesión."""
        horas = self.tiempo_sesion // 3600
        minutos = (self.tiempo_sesion % 3600) // 60
        segundos = self.tiempo_sesion % 60
        self.lbl_tiempo_sesion.config(text=f"⏱ {horas:02d}:{minutos:02d}:{segundos:02d}")
    
    def _actualizar_reloj(self):
        """Actualiza el reloj del sistema."""
        now = datetime.now()
        self.lbl_reloj.config(text=now.strftime("%H:%M:%S"))
        self.lbl_fecha.config(text=now.strftime("%d %b %Y"))
        self.root.after(1000, self._actualizar_reloj)
    
    def _mostrar_notificacion(self, mensaje: str, color: str = Colors.PRIMARY):
        """Muestra una notificación temporal."""
        notif = tk.Toplevel(self.root)
        notif.overrideredirect(True)
        notif.configure(bg=color)
        
        # Posicionar en esquina inferior derecha
        x = self.root.winfo_x() + self.root.winfo_width() - 300
        y = self.root.winfo_y() + self.root.winfo_height() - 80
        notif.geometry(f"280x50+{x}+{y}")
        
        tk.Label(notif, text=mensaje, font=("Segoe UI", 10, "bold"),
                fg=Colors.TEXT_PRIMARY, bg=color).pack(expand=True)
        
        # Auto-cerrar después de 2 segundos
        notif.after(2000, notif.destroy)
    
    # ══════════════════════════════════════════════════════════════════════════
    # 🗺️ FUNCIONES DE MAPA Y UBICACIÓN
    # ══════════════════════════════════════════════════════════════════════════
    
    def _abrir_mapa(self):
        """Abre el selector de ubicación con mapa."""
        if not MAPA_DISPONIBLE:
            messagebox.showwarning(
                "Mapa no disponible",
                "El mapa interactivo requiere librerías adicionales.\n\n"
                "Instale con:\npip install tkintermapview geopy"
            )
            return
        
        lat, lon = self.obtener_coordenadas()
        if lat is None:
            lat = 40.4168
        if lon is None:
            lon = -3.7038
        
        abrir_selector_ubicacion(
            self.root,
            lat=lat,
            lon=lon,
            callback=self._on_ubicacion_seleccionada
        )
    
    def _on_ubicacion_seleccionada(self, ubicacion):
        """Callback cuando se selecciona ubicación en el mapa."""
        if ubicacion:
            self.entry_lat.delete(0, tk.END)
            self.entry_lat.insert(0, f"{ubicacion.latitud:.6f}")
            
            self.entry_lon.delete(0, tk.END)
            self.entry_lon.insert(0, f"{ubicacion.longitud:.6f}")
            
            nombre = ubicacion.direccion or f"{ubicacion.calle} {ubicacion.numero}".strip()
            if nombre:
                self.entry_ubicacion.delete(0, tk.END)
                self.entry_ubicacion.insert(0, nombre)
                self.lbl_direccion.config(text=nombre[:60] + "..." if len(nombre) > 60 else nombre)
            
            if self.callback_cambiar_ubicacion:
                self.callback_cambiar_ubicacion(nombre, str(ubicacion.latitud), str(ubicacion.longitud))
            
            self._mostrar_notificacion("📍 Ubicación seleccionada", Colors.SUCCESS)
    
    # ══════════════════════════════════════════════════════════════════════════
    # 📜 VENTANAS SECUNDARIAS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _mostrar_historial(self):
        """Muestra ventana de historial."""
        hist = tk.Toplevel(self.root)
        hist.title("Historial de Datos")
        hist.geometry("550x450")
        hist.configure(bg=Colors.BG_DARK)
        hist.transient(self.root)
        
        # Header
        header = tk.Frame(hist, bg=Colors.BG_CARD, height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="📂 Historial de Sesiones", font=("Segoe UI", 12, "bold"),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(side="left", padx=16, pady=12)
        
        # Lista
        list_frame = tk.Frame(hist, bg=Colors.BG_CARD)
        list_frame.pack(fill="both", expand=True, padx=16, pady=16)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        lista = tk.Listbox(list_frame, bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                          font=("Segoe UI", 10), selectbackground=Colors.PRIMARY,
                          selectforeground=Colors.TEXT_PRIMARY, relief="flat",
                          highlightthickness=1, highlightbackground=Colors.BORDER,
                          yscrollcommand=scrollbar.set)
        lista.pack(fill="both", expand=True)
        scrollbar.config(command=lista.yview)
        
        # Cargar datos
        if os.path.exists(self.carpeta_datos):
            carpetas = sorted(os.listdir(self.carpeta_datos), reverse=True)
            for carpeta in carpetas:
                ruta = os.path.join(self.carpeta_datos, carpeta)
                if os.path.isdir(ruta):
                    csvs = [f for f in os.listdir(ruta) if f.endswith('.csv')]
                    lista.insert(tk.END, f"📁 {carpeta}  ({len(csvs)} archivos)")
        else:
            lista.insert(tk.END, "  No hay datos guardados todavía")
        
        # Botón abrir
        def abrir_carpeta():
            if os.path.exists(self.carpeta_datos):
                os.startfile(self.carpeta_datos)
        
        btn_frame = tk.Frame(hist, bg=Colors.BG_DARK)
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))
        
        tk.Button(btn_frame, text="📂 Abrir Carpeta de Datos", font=("Segoe UI", 10, "bold"),
                 bg=Colors.PRIMARY, fg=Colors.TEXT_PRIMARY, relief="flat",
                 cursor="hand2", padx=16, pady=8, command=abrir_carpeta).pack()
    
    def _mostrar_ayuda(self):
        """Muestra ventana de ayuda."""
        ayuda = tk.Toplevel(self.root)
        ayuda.title("Ayuda - YoloConteo")
        ayuda.geometry("550x700")
        ayuda.configure(bg=Colors.BG_DARK)
        ayuda.transient(self.root)
        
        # Header
        header = tk.Frame(ayuda, bg=Colors.BG_CARD, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text="❓", font=("Segoe UI Emoji", 20),
                fg=Colors.PRIMARY_LIGHT, bg=Colors.BG_CARD).pack(side="left", padx=16)
        tk.Label(header, text="Centro de Ayuda", font=("Segoe UI", 14, "bold"),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(side="left")
        
        # Contenido
        content = tk.Frame(ayuda, bg=Colors.BG_DARK)
        content.pack(fill="both", expand=True, padx=16, pady=16)
        
        texto_ayuda = """
🚀 INICIO RÁPIDO

1. INICIAR   → Activa la cámara y detección
2. PAUSAR    → Pausa sin cerrar la cámara
3. DETENER   → Detiene completamente
4. EXPORTAR  → Guarda resumen en CSV
5. REINICIAR → Contadores a cero
6. 📷        → Captura pantalla actual


📍 UBICACIÓN

• GPS se detecta automáticamente
• 🗺️ Seleccionar en mapa
• 📷 Capturar imagen de la ubicación
• ✓ Aplicar cambios


📊 SISTEMA DE CONTEO Y DIRECCIONES

En el CSV las direcciones se guardan como:
• 0 = Dirección 1 (izquierda → derecha)
• 1 = Dirección 2 (derecha → izquierda)

La línea vertical marca el punto de conteo.
Ajuste su posición con el slider.


📁 FORMATO DE DATOS CSV

Columnas del registro:
• fecha: YYYY-MM-DD
• hora: HH:MM:SS
• tipo: Adulto, Bicicleta, etc.
• direccion: 0 o 1
• total_tipo: Total de ese tipo
• total_dir0: Total dirección 0
• total_dir1: Total dirección 1
• total_sesion: Total de la sesión
• ubicacion: Nombre del lugar
• latitude, longitude: Coordenadas
• sesion_id: Identificador de sesión


📂 ESTRUCTURA DE CARPETAS

datos/Ubicacion_Lat_Lon_Fecha/
  ├── registros_HORA.csv
  ├── resumen_HORA.csv
  └── snapshots/
      └── captura_manual_*.jpg


🚲 CATEGORÍAS DETECTABLES

• Adultos: Detección automática
• Bicicletas: Detección automática
• Niños: Modelo personalizado
• Sillas de ruedas: Modelo personalizado


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

       Creado por David Antízar
          YoloConteo © 2026
        """
        
        text_widget = tk.Text(content, bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY,
                             font=("Segoe UI", 10), relief="flat", wrap="word",
                             padx=16, pady=16, highlightthickness=1,
                             highlightbackground=Colors.BORDER)
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("1.0", texto_ayuda)
        text_widget.config(state="disabled")
        
        # Cerrar
        tk.Button(ayuda, text="Cerrar", font=("Segoe UI", 10, "bold"),
                 bg=Colors.DANGER, fg=Colors.TEXT_PRIMARY, relief="flat",
                 cursor="hand2", padx=24, pady=8,
                 command=ayuda.destroy).pack(pady=16)
    
    # ══════════════════════════════════════════════════════════════════════════
    # 🔌 MÉTODOS PÚBLICOS (API)
    # ══════════════════════════════════════════════════════════════════════════
    
    def establecer_callbacks(self, iniciar=None, pausar=None, reiniciar=None,
                            exportar=None, cerrar=None, slider_linea=None,
                            slider_confianza=None, cambiar_ubicacion=None,
                            captura=None):
        """Establece los callbacks para los eventos de la GUI."""
        self.callback_iniciar = iniciar
        self.callback_pausar = pausar
        self.callback_reiniciar = reiniciar
        self.callback_exportar = exportar
        self.callback_cerrar = cerrar
        self.callback_slider_linea = slider_linea
        self.callback_slider_confianza = slider_confianza
        self.callback_cambiar_ubicacion = cambiar_ubicacion
        self.callback_captura = captura
    
    def actualizar_frame(self, frame):
        """Actualiza el frame de video en el canvas."""
        if frame is None:
            return
        
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            canvas_w = self.canvas_video.winfo_width()
            canvas_h = self.canvas_video.winfo_height()
            
            if canvas_w > 10 and canvas_h > 10:
                frame_h, frame_w = frame_rgb.shape[:2]
                ratio = min(canvas_w / frame_w, canvas_h / frame_h)
                new_w = int(frame_w * ratio)
                new_h = int(frame_h * ratio)
                
                frame_rgb = cv2.resize(frame_rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                
                imagen = Image.fromarray(frame_rgb)
                self.imagen_tk = ImageTk.PhotoImage(image=imagen)
                
                self.canvas_video.delete("all")
                x = (canvas_w - new_w) // 2
                y = (canvas_h - new_h) // 2
                self.canvas_video.create_image(x, y, anchor="nw", image=self.imagen_tk)
                
        except Exception as e:
            logger.error(f"Error al actualizar frame: {e}")
    
    def actualizar_contadores(self, contadores: Dict):
        """Actualiza todos los contadores de categorías."""
        total_der = 0
        total_izq = 0
        max_cat = 1
        
        # Calcular máximo para las barras
        for cat, vals in contadores.items():
            cat_total = vals.get('izq_der', 0) + vals.get('der_izq', 0)
            max_cat = max(max_cat, cat_total)
        
        # Actualizar cada categoría
        for cat, vals in contadores.items():
            if cat in self.contador_widgets:
                izq_der = vals.get('izq_der', 0)
                der_izq = vals.get('der_izq', 0)
                self.contador_widgets[cat].update(izq_der, der_izq, max_cat)
                total_der += izq_der
                total_izq += der_izq
        
        # Actualizar totales animados
        self.counter_der.set_value(total_der)
        self.counter_izq.set_value(total_izq)
    
    def actualizar_fps(self, fps: float):
        """Actualiza el indicador de FPS."""
        color = Colors.SUCCESS if fps >= 20 else (Colors.WARNING if fps >= 10 else Colors.DANGER)
        self.lbl_fps.config(text=f"FPS: {fps:.1f}", fg=color)
    
    def actualizar_gps(self, lat, lon):
        """Actualiza las coordenadas GPS."""
        if lat is not None and lon is not None:
            self.entry_lat.delete(0, tk.END)
            self.entry_lat.insert(0, f"{lat:.6f}")
            self.entry_lon.delete(0, tk.END)
            self.entry_lon.insert(0, f"{lon:.6f}")
    
    def obtener_ubicacion(self) -> str:
        """Obtiene el nombre de ubicación actual."""
        text = self.entry_ubicacion.get()
        return "" if text == "Nombre del punto..." else text
    
    def establecer_ubicacion(self, ubicacion: str):
        """Establece el nombre de ubicación."""
        self.entry_ubicacion.delete(0, tk.END)
        self.entry_ubicacion.insert(0, ubicacion)
        self.lbl_direccion.config(text=ubicacion)
    
    def obtener_coordenadas(self) -> Tuple[Optional[float], Optional[float]]:
        """Obtiene las coordenadas actuales."""
        try:
            lat = float(self.entry_lat.get())
            lon = float(self.entry_lon.get())
            return lat, lon
        except:
            return None, None
    
    def mostrar_mensaje(self, titulo: str, mensaje: str, tipo: str = "info"):
        """Muestra un mensaje al usuario."""
        if tipo == "info":
            messagebox.showinfo(titulo, mensaje)
        elif tipo == "warning":
            messagebox.showwarning(titulo, mensaje)
        elif tipo == "error":
            messagebox.showerror(titulo, mensaje)
    
    def mostrar_alerta_movilidad_reducida(self):
        """Muestra alerta especial para movilidad reducida."""
        self.lbl_estado.config(text="⚠️ MOV. REDUCIDA", fg=Colors.ACCENT_PINK)
        self.status_dot.set_color(Colors.ACCENT_PINK)
        self._mostrar_notificacion("♿ Persona con movilidad reducida detectada", Colors.ACCENT_PINK)
        
        self.root.after(3000, lambda: self._actualizar_estado_visual() if self.ejecutando else None)
    
    def iniciar(self):
        """Inicia el loop principal de la GUI."""
        self.root.mainloop()
    
    def esta_ejecutando(self) -> bool:
        """Retorna si está ejecutando."""
        return self.ejecutando
    
    def esta_pausado(self) -> bool:
        """Retorna si está pausado."""
        return self.pausado
