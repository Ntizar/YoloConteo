# -*- coding: utf-8 -*-
"""
Módulo SelectorUbicacion - Selector de ubicación con mapa interactivo.
Permite seleccionar ubicación en el mapa y obtener dirección automáticamente.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from typing import Optional, Tuple, Callable
from dataclasses import dataclass

try:
    import tkintermapview
    MAPA_DISPONIBLE = True
except ImportError:
    MAPA_DISPONIBLE = False

try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut
    GEOPY_DISPONIBLE = True
except ImportError:
    GEOPY_DISPONIBLE = False

try:
    import geocoder
    GEOCODER_DISPONIBLE = True
except ImportError:
    GEOCODER_DISPONIBLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class UbicacionInfo:
    """Información de ubicación."""
    latitud: float
    longitud: float
    direccion: str = ""
    calle: str = ""
    numero: str = ""
    ciudad: str = ""
    codigo_postal: str = ""
    pais: str = ""


class SelectorUbicacion:
    """
    Ventana de selección de ubicación con mapa interactivo.
    
    Permite:
    - Ver mapa de OpenStreetMap
    - Hacer clic para seleccionar ubicación
    - Buscar direcciones
    - Usar ubicación actual (GPS/IP)
    - Obtener dirección automática de las coordenadas
    """
    
    def __init__(
        self,
        parent: tk.Tk,
        lat_inicial: float = 40.4168,
        lon_inicial: float = -3.7038,
        callback_seleccion: Callable[[UbicacionInfo], None] = None
    ):
        self.parent = parent
        self.lat_inicial = lat_inicial
        self.lon_inicial = lon_inicial
        self.callback_seleccion = callback_seleccion
        
        self.ubicacion_actual: Optional[UbicacionInfo] = None
        self.marker_actual = None
        self.geocoder = None
        
        # Inicializar geocoder
        if GEOPY_DISPONIBLE:
            self.geocoder = Nominatim(user_agent="yoloconteo_app")
        
        self._crear_ventana()
    
    def _crear_ventana(self):
        """Crea la ventana del selector de ubicación."""
        self.ventana = tk.Toplevel(self.parent)
        self.ventana.title("📍 Seleccionar Ubicación")
        self.ventana.geometry("900x650")
        self.ventana.configure(bg="#0a0a0a")
        self.ventana.transient(self.parent)
        self.ventana.grab_set()
        
        # Header
        header = tk.Frame(self.ventana, bg="#1a1a1a", height=50)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(
            header, text="📍 Seleccione la ubicación en el mapa",
            font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#1a1a1a"
        ).pack(side="left", padx=15, pady=10)
        
        # Instrucciones
        tk.Label(
            header, text="Haga clic en el mapa o busque una dirección",
            font=("Segoe UI", 9), fg="#808080", bg="#1a1a1a"
        ).pack(side="right", padx=15)
        
        # Frame principal
        main_frame = tk.Frame(self.ventana, bg="#0a0a0a")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Panel izquierdo (búsqueda y datos)
        left_panel = tk.Frame(main_frame, bg="#1a1a1a", width=280)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)
        
        self._crear_panel_busqueda(left_panel)
        self._crear_panel_datos(left_panel)
        self._crear_panel_botones(left_panel)
        
        # Panel derecho (mapa)
        map_frame = tk.Frame(main_frame, bg="#1a1a1a")
        map_frame.pack(side="right", fill="both", expand=True)
        
        self._crear_mapa(map_frame)
    
    def _crear_panel_busqueda(self, parent):
        """Crea el panel de búsqueda."""
        search_frame = tk.Frame(parent, bg="#1a1a1a")
        search_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(
            search_frame, text="🔍 Buscar dirección:",
            font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#1a1a1a"
        ).pack(anchor="w", pady=(0, 5))
        
        entry_frame = tk.Frame(search_frame, bg="#1a1a1a")
        entry_frame.pack(fill="x")
        
        self.entry_busqueda = tk.Entry(
            entry_frame, font=("Segoe UI", 10),
            bg="#2a2a2a", fg="#ffffff", insertbackground="#ffffff", relief="flat"
        )
        self.entry_busqueda.pack(side="left", fill="x", expand=True, ipady=5)
        self.entry_busqueda.bind("<Return>", lambda e: self._buscar_direccion())
        
        tk.Button(
            entry_frame, text="🔍", font=("Segoe UI", 10),
            bg="#505050", fg="#ffffff", relief="flat", width=3,
            command=self._buscar_direccion
        ).pack(side="right", padx=(5, 0))
        
        # Botón ubicación actual
        tk.Button(
            search_frame, text="📍 Mi ubicación actual",
            font=("Segoe UI", 9), bg="#404040", fg="#ffffff",
            relief="flat", cursor="hand2",
            command=self._obtener_ubicacion_actual
        ).pack(fill="x", pady=(10, 0), ipady=3)
    
    def _crear_panel_datos(self, parent):
        """Crea el panel de datos de ubicación."""
        datos_frame = tk.Frame(parent, bg="#0a0a0a")
        datos_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(
            datos_frame, text="📋 Datos de ubicación:",
            font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#0a0a0a"
        ).pack(anchor="w", pady=(0, 10))
        
        # Coordenadas
        coords_frame = tk.Frame(datos_frame, bg="#0a0a0a")
        coords_frame.pack(fill="x", pady=2)
        
        tk.Label(coords_frame, text="Latitud:", font=("Segoe UI", 9), fg="#808080", bg="#0a0a0a", width=10, anchor="w").pack(side="left")
        self.lbl_lat = tk.Label(coords_frame, text="-", font=("Segoe UI", 9, "bold"), fg="#e0e0e0", bg="#0a0a0a")
        self.lbl_lat.pack(side="left")
        
        coords_frame2 = tk.Frame(datos_frame, bg="#0a0a0a")
        coords_frame2.pack(fill="x", pady=2)
        
        tk.Label(coords_frame2, text="Longitud:", font=("Segoe UI", 9), fg="#808080", bg="#0a0a0a", width=10, anchor="w").pack(side="left")
        self.lbl_lon = tk.Label(coords_frame2, text="-", font=("Segoe UI", 9, "bold"), fg="#e0e0e0", bg="#0a0a0a")
        self.lbl_lon.pack(side="left")
        
        # Separador
        tk.Frame(datos_frame, bg="#333333", height=1).pack(fill="x", pady=10)
        
        # Dirección
        tk.Label(datos_frame, text="Dirección:", font=("Segoe UI", 9), fg="#808080", bg="#0a0a0a").pack(anchor="w")
        self.lbl_direccion = tk.Label(
            datos_frame, text="Seleccione en el mapa",
            font=("Segoe UI", 9), fg="#ffffff", bg="#0a0a0a",
            wraplength=250, justify="left"
        )
        self.lbl_direccion.pack(anchor="w", pady=(2, 5))
        
        # Calle y número
        calle_frame = tk.Frame(datos_frame, bg="#0a0a0a")
        calle_frame.pack(fill="x", pady=2)
        
        tk.Label(calle_frame, text="Calle:", font=("Segoe UI", 9), fg="#808080", bg="#0a0a0a", width=10, anchor="w").pack(side="left")
        self.lbl_calle = tk.Label(calle_frame, text="-", font=("Segoe UI", 9), fg="#ffffff", bg="#0a0a0a")
        self.lbl_calle.pack(side="left")
        
        num_frame = tk.Frame(datos_frame, bg="#0a0a0a")
        num_frame.pack(fill="x", pady=2)
        
        tk.Label(num_frame, text="Número:", font=("Segoe UI", 9), fg="#808080", bg="#0a0a0a", width=10, anchor="w").pack(side="left")
        self.lbl_numero = tk.Label(num_frame, text="-", font=("Segoe UI", 9), fg="#ffffff", bg="#0a0a0a")
        self.lbl_numero.pack(side="left")
        
        ciudad_frame = tk.Frame(datos_frame, bg="#0a0a0a")
        ciudad_frame.pack(fill="x", pady=2)
        
        tk.Label(ciudad_frame, text="Ciudad:", font=("Segoe UI", 9), fg="#808080", bg="#0a0a0a", width=10, anchor="w").pack(side="left")
        self.lbl_ciudad = tk.Label(ciudad_frame, text="-", font=("Segoe UI", 9), fg="#ffffff", bg="#0a0a0a")
        self.lbl_ciudad.pack(side="left")
        
        # Campo editable para nombre personalizado
        tk.Frame(datos_frame, bg="#333333", height=1).pack(fill="x", pady=10)
        
        tk.Label(datos_frame, text="Nombre personalizado (opcional):", font=("Segoe UI", 9), fg="#808080", bg="#0a0a0a").pack(anchor="w")
        self.entry_nombre = tk.Entry(
            datos_frame, font=("Segoe UI", 10),
            bg="#1a1a1a", fg="#ffffff", insertbackground="#ffffff", relief="flat"
        )
        self.entry_nombre.pack(fill="x", pady=5, ipady=3)
    
    def _crear_panel_botones(self, parent):
        """Crea el panel de botones."""
        btn_frame = tk.Frame(parent, bg="#1a1a1a")
        btn_frame.pack(fill="x", side="bottom", padx=10, pady=15)
        
        tk.Button(
            btn_frame, text="✓ Confirmar ubicación",
            font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#000000",
            relief="flat", cursor="hand2",
            command=self._confirmar_ubicacion
        ).pack(fill="x", pady=(0, 5), ipady=5)
        
        tk.Button(
            btn_frame, text="✕ Cancelar",
            font=("Segoe UI", 10), bg="#404040", fg="#ffffff",
            relief="flat", cursor="hand2",
            command=self.ventana.destroy
        ).pack(fill="x", ipady=3)
    
    def _crear_mapa(self, parent):
        """Crea el widget del mapa."""
        if not MAPA_DISPONIBLE:
            tk.Label(
                parent, text="⚠️ Mapa no disponible\n\nInstale: pip install tkintermapview",
                font=("Segoe UI", 12), fg="#a0a0a0", bg="#1a1a1a"
            ).pack(expand=True)
            return
        
        # Crear mapa
        self.mapa = tkintermapview.TkinterMapView(parent, corner_radius=0)
        self.mapa.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configurar mapa
        self.mapa.set_position(self.lat_inicial, self.lon_inicial)
        self.mapa.set_zoom(15)
        
        # Agregar marker inicial
        self.marker_actual = self.mapa.set_marker(
            self.lat_inicial, self.lon_inicial,
            text="📍 Ubicación inicial"
        )
        
        # Evento de clic
        self.mapa.add_left_click_map_command(self._on_mapa_click)
        
        # Actualizar datos iniciales
        self._actualizar_ubicacion(self.lat_inicial, self.lon_inicial)
    
    def _on_mapa_click(self, coords: Tuple[float, float]):
        """Maneja el clic en el mapa."""
        lat, lon = coords
        self._actualizar_ubicacion(lat, lon)
        
        # Mover marker
        if self.marker_actual:
            self.marker_actual.delete()
        self.marker_actual = self.mapa.set_marker(lat, lon, text="📍")
    
    def _actualizar_ubicacion(self, lat: float, lon: float):
        """Actualiza la ubicación y obtiene la dirección."""
        self.lbl_lat.config(text=f"{lat:.6f}")
        self.lbl_lon.config(text=f"{lon:.6f}")
        self.lbl_direccion.config(text="Obteniendo dirección...")
        
        # Obtener dirección en hilo separado
        threading.Thread(
            target=self._obtener_direccion,
            args=(lat, lon),
            daemon=True
        ).start()
    
    def _obtener_direccion(self, lat: float, lon: float):
        """Obtiene la dirección a partir de coordenadas (geocodificación inversa)."""
        try:
            direccion = ""
            calle = ""
            numero = ""
            ciudad = ""
            codigo_postal = ""
            pais = ""
            
            if GEOPY_DISPONIBLE and self.geocoder:
                try:
                    location = self.geocoder.reverse(f"{lat}, {lon}", language="es", timeout=10)
                    if location:
                        direccion = location.address
                        raw = location.raw.get('address', {})
                        
                        # Extraer componentes
                        calle = raw.get('road', raw.get('street', raw.get('pedestrian', '')))
                        numero = raw.get('house_number', '')
                        ciudad = raw.get('city', raw.get('town', raw.get('village', raw.get('municipality', ''))))
                        codigo_postal = raw.get('postcode', '')
                        pais = raw.get('country', '')
                        
                except GeocoderTimedOut:
                    logger.warning("Timeout al obtener dirección")
                except Exception as e:
                    logger.error(f"Error geopy: {e}")
            
            # Crear objeto de ubicación
            self.ubicacion_actual = UbicacionInfo(
                latitud=lat,
                longitud=lon,
                direccion=direccion,
                calle=calle,
                numero=numero,
                ciudad=ciudad,
                codigo_postal=codigo_postal,
                pais=pais
            )
            
            # Actualizar GUI en hilo principal
            self.ventana.after(0, self._actualizar_gui_direccion)
            
        except Exception as e:
            logger.error(f"Error al obtener dirección: {e}")
            self.ventana.after(0, lambda: self.lbl_direccion.config(text="Error al obtener dirección"))
    
    def _actualizar_gui_direccion(self):
        """Actualiza la GUI con la información de dirección."""
        if self.ubicacion_actual:
            ub = self.ubicacion_actual
            self.lbl_direccion.config(text=ub.direccion or "No disponible")
            self.lbl_calle.config(text=ub.calle or "-")
            self.lbl_numero.config(text=ub.numero or "-")
            self.lbl_ciudad.config(text=ub.ciudad or "-")
            
            # Auto-rellenar nombre si está vacío
            if not self.entry_nombre.get():
                nombre_auto = f"{ub.calle} {ub.numero}".strip() if ub.calle else ub.ciudad
                self.entry_nombre.delete(0, tk.END)
                self.entry_nombre.insert(0, nombre_auto)
    
    def _buscar_direccion(self):
        """Busca una dirección y centra el mapa."""
        query = self.entry_busqueda.get().strip()
        if not query:
            return
        
        if not GEOPY_DISPONIBLE:
            messagebox.showwarning("Aviso", "Geocodificación no disponible")
            return
        
        try:
            location = self.geocoder.geocode(query, language="es", timeout=10)
            if location:
                lat, lon = location.latitude, location.longitude
                
                # Centrar mapa
                if hasattr(self, 'mapa'):
                    self.mapa.set_position(lat, lon)
                    self.mapa.set_zoom(17)
                
                # Actualizar ubicación
                self._on_mapa_click((lat, lon))
            else:
                messagebox.showinfo("Búsqueda", "No se encontró la dirección")
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            messagebox.showerror("Error", f"Error al buscar: {e}")
    
    def _obtener_ubicacion_actual(self):
        """Obtiene la ubicación actual por IP."""
        try:
            if GEOCODER_DISPONIBLE:
                g = geocoder.ip('me')
                if g.ok and g.latlng:
                    lat, lon = g.latlng
                    
                    # Centrar mapa
                    if hasattr(self, 'mapa'):
                        self.mapa.set_position(lat, lon)
                        self.mapa.set_zoom(16)
                    
                    # Actualizar ubicación
                    self._on_mapa_click((lat, lon))
                    return
            
            messagebox.showwarning("Aviso", "No se pudo obtener ubicación actual")
        except Exception as e:
            logger.error(f"Error GPS: {e}")
            messagebox.showerror("Error", f"Error al obtener ubicación: {e}")
    
    def _confirmar_ubicacion(self):
        """Confirma la ubicación seleccionada."""
        if not self.ubicacion_actual:
            messagebox.showwarning("Aviso", "Seleccione una ubicación en el mapa")
            return
        
        # Usar nombre personalizado si se proporcionó
        nombre = self.entry_nombre.get().strip()
        if nombre:
            self.ubicacion_actual.direccion = nombre
        
        # Llamar callback
        if self.callback_seleccion:
            self.callback_seleccion(self.ubicacion_actual)
        
        self.ventana.destroy()


def abrir_selector_ubicacion(parent, lat=40.4168, lon=-3.7038, callback=None):
    """
    Función de conveniencia para abrir el selector de ubicación.
    
    Args:
        parent: Ventana padre
        lat: Latitud inicial
        lon: Longitud inicial
        callback: Función a llamar con la ubicación seleccionada
    
    Returns:
        Instancia del SelectorUbicacion
    """
    if not MAPA_DISPONIBLE:
        messagebox.showerror(
            "Error",
            "El mapa no está disponible.\n\nInstale: pip install tkintermapview"
        )
        return None
    
    return SelectorUbicacion(parent, lat, lon, callback)
