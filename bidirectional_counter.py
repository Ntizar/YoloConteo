# -*- coding: utf-8 -*-
"""
Módulo BidirectionalCounter - Maneja la lógica de conteo bidireccional con tracking.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
from collections import defaultdict
import logging
from dataclasses import dataclass, field
from enum import Enum

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Intentar importar DeepSort
try:
    from deep_sort_realtime.deepsort_tracker import DeepSort
    DEEPSORT_DISPONIBLE = True
except ImportError:
    DEEPSORT_DISPONIBLE = False
    logger.warning("deep_sort_realtime no está instalado. Se usará tracker simple.")


class Direccion(Enum):
    """Enumeración para las direcciones de cruce."""
    IZQUIERDA_A_DERECHA = "izq_der"
    DERECHA_A_IZQUIERDA = "der_izq"
    NINGUNA = "ninguna"


@dataclass
class TrackInfo:
    """Información de tracking para un objeto."""
    track_id: int
    categoria: str
    ultima_posicion_x: float
    posicion_inicial_x: float
    cruzado: bool = False
    direccion_cruce: Optional[Direccion] = None
    frames_vistos: int = 1
    historial_posiciones: List[Tuple[float, float]] = field(default_factory=list)
    ultimo_lado: str = 'ninguno'  # 'izquierda', 'derecha', 'ninguno'
    puede_cruzar: bool = True  # Permite cruzar de nuevo después de alejarse


class BidirectionalCounter:
    """
    Clase para manejar el conteo bidireccional de objetos con tracking.
    
    Utiliza DeepSort o un tracker simple para asignar IDs únicos a cada objeto
    y detectar cuando cruzan la línea de conteo.
    
    Attributes:
        linea_posicion: Posición X de la línea de conteo (en píxeles)
        contadores: Diccionario con los contadores por categoría y dirección
        tracks: Diccionario con información de tracking de cada objeto
    """
    
    def __init__(
        self,
        ancho_frame: int = 640,
        alto_frame: int = 480,
        linea_posicion_relativa: float = 0.5,
        margen_cruce: int = 30,
        categorias: List[str] = None,
        usar_deepsort: bool = True,
        callback_cruce: Callable = None
    ):
        """
        Inicializa el contador bidireccional.
        
        Args:
            ancho_frame: Ancho del frame de video en píxeles
            alto_frame: Alto del frame de video en píxeles
            linea_posicion_relativa: Posición de la línea (0.0 a 1.0)
            margen_cruce: Margen en píxeles para detectar cruce
            categorias: Lista de categorías a contar
            usar_deepsort: Si se debe usar DeepSort para tracking
            callback_cruce: Función a llamar cuando se detecta un cruce
        """
        self.ancho_frame = ancho_frame
        self.alto_frame = alto_frame
        self.margen_cruce = margen_cruce
        self.callback_cruce = callback_cruce
        
        # Calcular posición de la línea en píxeles
        self.linea_posicion_relativa = linea_posicion_relativa
        self.linea_x = int(ancho_frame * linea_posicion_relativa)
        
        # Categorías por defecto (sin patinete)
        self.categorias = categorias or [
            'adulto', 'nino', 'bicicleta', 
            'silla_ruedas', 'movilidad_reducida'
        ]
        
        # Inicializar contadores
        self.contadores = self._inicializar_contadores()
        
        # Diccionario para tracking de objetos
        self.tracks: Dict[int, TrackInfo] = {}
        self.siguiente_track_id = 1
        
        # Inicializar tracker
        self.usar_deepsort = usar_deepsort and DEEPSORT_DISPONIBLE
        self.tracker = None
        self._inicializar_tracker()
        
        logger.info(f"Contador bidireccional inicializado. Línea en X={self.linea_x}")
    
    def _inicializar_contadores(self) -> Dict:
        """
        Inicializa la estructura de contadores.
        
        Returns:
            Diccionario con contadores a cero para cada categoría y dirección
        """
        contadores = {}
        for categoria in self.categorias:
            contadores[categoria] = {
                'izq_der': 0,
                'der_izq': 0
            }
        return contadores
    
    def _inicializar_tracker(self) -> None:
        """Inicializa el tracker DeepSort o tracker simple."""
        if self.usar_deepsort:
            try:
                self.tracker = DeepSort(
                    max_age=30,
                    n_init=3,
                    max_iou_distance=0.7,
                    max_cosine_distance=0.3,
                    nn_budget=100
                )
                logger.info("DeepSort tracker inicializado")
            except Exception as e:
                logger.error(f"Error al inicializar DeepSort: {e}")
                self.usar_deepsort = False
                logger.info("Usando tracker simple como fallback")
        else:
            logger.info("Usando tracker simple")
    
    def actualizar_posicion_linea(self, posicion_relativa: float) -> None:
        """
        Actualiza la posición de la línea de conteo.
        
        Args:
            posicion_relativa: Nueva posición (0.0 a 1.0)
        """
        self.linea_posicion_relativa = max(0.1, min(0.9, posicion_relativa))
        self.linea_x = int(self.ancho_frame * self.linea_posicion_relativa)
        logger.info(f"Posición de línea actualizada a X={self.linea_x}")
    
    def actualizar_dimensiones(self, ancho: int, alto: int) -> None:
        """
        Actualiza las dimensiones del frame.
        
        Args:
            ancho: Nuevo ancho en píxeles
            alto: Nuevo alto en píxeles
        """
        self.ancho_frame = ancho
        self.alto_frame = alto
        self.linea_x = int(ancho * self.linea_posicion_relativa)
    
    def procesar_detecciones(self, detecciones: List[Dict], frame: np.ndarray = None) -> List[Dict]:
        """
        Procesa las detecciones, aplica tracking y detecta cruces de línea.
        
        Args:
            detecciones: Lista de detecciones del detector YOLO
            frame: Frame actual (necesario para DeepSort)
            
        Returns:
            Lista de detecciones con IDs de tracking asignados
        """
        if not detecciones:
            return []
        
        if self.usar_deepsort and frame is not None:
            return self._procesar_con_deepsort(detecciones, frame)
        else:
            return self._procesar_con_tracker_simple(detecciones)
    
    def _procesar_con_deepsort(self, detecciones: List[Dict], frame: np.ndarray) -> List[Dict]:
        """
        Procesa detecciones usando DeepSort tracker.
        
        Args:
            detecciones: Lista de detecciones
            frame: Frame actual
            
        Returns:
            Detecciones con IDs de tracking
        """
        # Preparar detecciones para DeepSort
        # Formato: [[x1, y1, w, h], confidence, class_name]
        detecciones_deepsort = []
        for det in detecciones:
            x1, y1, x2, y2 = det['bbox']
            ancho = x2 - x1
            alto = y2 - y1
            detecciones_deepsort.append((
                [x1, y1, ancho, alto],
                det['confianza'],
                det['categoria']
            ))
        
        # Actualizar tracker
        tracks = self.tracker.update_tracks(detecciones_deepsort, frame=frame)
        
        # Procesar tracks activos
        detecciones_con_id = []
        for track in tracks:
            if not track.is_confirmed():
                continue
            
            track_id = track.track_id
            ltrb = track.to_ltrb()  # [left, top, right, bottom]
            x1, y1, x2, y2 = map(int, ltrb)
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            
            # Obtener categoría del track
            categoria = track.get_det_class() if hasattr(track, 'get_det_class') else 'adulto'
            
            # Actualizar información de tracking
            self._actualizar_track(track_id, categoria, cx, cy)
            
            # Verificar cruce de línea
            self._verificar_cruce(track_id)
            
            # Crear detección con ID
            det_con_id = {
                'bbox': [x1, y1, x2, y2],
                'categoria': categoria,
                'confianza': 0.0,  # DeepSort no proporciona confianza directamente
                'centro': (cx, cy),
                'track_id': track_id,
                'ancho': x2 - x1,
                'alto': y2 - y1
            }
            detecciones_con_id.append(det_con_id)
        
        return detecciones_con_id
    
    def _procesar_con_tracker_simple(self, detecciones: List[Dict]) -> List[Dict]:
        """
        Procesa detecciones usando un tracker simple basado en IoU.
        
        Args:
            detecciones: Lista de detecciones
            
        Returns:
            Detecciones con IDs de tracking
        """
        detecciones_con_id = []
        tracks_usados = set()
        
        for det in detecciones:
            cx, cy = det['centro']
            categoria = det['categoria']
            
            # Buscar track existente cercano
            track_id = self._encontrar_track_cercano(cx, cy, categoria, tracks_usados)
            
            if track_id is None:
                # Crear nuevo track
                track_id = self.siguiente_track_id
                self.siguiente_track_id += 1
                self.tracks[track_id] = TrackInfo(
                    track_id=track_id,
                    categoria=categoria,
                    ultima_posicion_x=cx,
                    posicion_inicial_x=cx,
                    historial_posiciones=[(cx, cy)]
                )
            else:
                # Actualizar track existente
                self._actualizar_track(track_id, categoria, cx, cy)
            
            tracks_usados.add(track_id)
            
            # Verificar cruce de línea
            self._verificar_cruce(track_id)
            
            # Agregar ID a la detección
            det_con_id = det.copy()
            det_con_id['track_id'] = track_id
            detecciones_con_id.append(det_con_id)
        
        # Limpiar tracks antiguos
        self._limpiar_tracks_antiguos(tracks_usados)
        
        return detecciones_con_id
    
    def _encontrar_track_cercano(
        self, 
        cx: float, 
        cy: float, 
        categoria: str,
        tracks_usados: set
    ) -> Optional[int]:
        """
        Busca un track existente cercano a la posición dada.
        
        Args:
            cx: Coordenada X del centro
            cy: Coordenada Y del centro
            categoria: Categoría del objeto
            tracks_usados: Set de tracks ya asignados
            
        Returns:
            ID del track encontrado o None
        """
        distancia_minima = float('inf')
        track_encontrado = None
        umbral_distancia = 100  # Píxeles
        
        for track_id, track_info in self.tracks.items():
            if track_id in tracks_usados:
                continue
            
            if track_info.categoria != categoria:
                continue
            
            if track_info.historial_posiciones:
                ultimo_x, ultimo_y = track_info.historial_posiciones[-1]
                distancia = np.sqrt((cx - ultimo_x)**2 + (cy - ultimo_y)**2)
                
                if distancia < distancia_minima and distancia < umbral_distancia:
                    distancia_minima = distancia
                    track_encontrado = track_id
        
        return track_encontrado
    
    def _actualizar_track(self, track_id: int, categoria: str, cx: float, cy: float) -> None:
        """
        Actualiza la información de un track existente.
        
        Args:
            track_id: ID del track
            categoria: Categoría del objeto
            cx: Nueva coordenada X
            cy: Nueva coordenada Y
        """
        if track_id not in self.tracks:
            self.tracks[track_id] = TrackInfo(
                track_id=track_id,
                categoria=categoria,
                ultima_posicion_x=cx,
                posicion_inicial_x=cx,
                historial_posiciones=[(cx, cy)]
            )
        else:
            track = self.tracks[track_id]
            track.ultima_posicion_x = cx
            track.frames_vistos += 1
            track.historial_posiciones.append((cx, cy))
            
            # Mantener solo las últimas 50 posiciones
            if len(track.historial_posiciones) > 50:
                track.historial_posiciones = track.historial_posiciones[-50:]
    
    def _verificar_cruce(self, track_id: int) -> None:
        """
        Verifica si el CENTRO del objeto ha cruzado la línea de conteo.
        Un cruce se detecta cuando el centro pasa de un lado al otro.
        
        Args:
            track_id: ID del track a verificar
        """
        if track_id not in self.tracks:
            return
        
        track = self.tracks[track_id]
        
        # Necesitamos al menos 2 posiciones para detectar cruce
        if len(track.historial_posiciones) < 2:
            return
        
        # Obtener posición anterior y actual del CENTRO
        pos_anterior_x = track.historial_posiciones[-2][0]
        pos_actual_x = track.historial_posiciones[-1][0]
        
        linea = self.linea_x
        
        # Verificar si el centro cruzó la línea de un lado a otro
        # Cruce de izquierda a derecha: estaba a la izquierda Y ahora está a la derecha
        if pos_anterior_x < linea and pos_actual_x >= linea:
            # Verificar que puede cruzar (evita conteo múltiple del mismo cruce)
            if track.puede_cruzar:
                self._registrar_cruce(track_id, Direccion.IZQUIERDA_A_DERECHA)
                track.puede_cruzar = False
                track.ultimo_lado = 'derecha'
        
        # Cruce de derecha a izquierda: estaba a la derecha Y ahora está a la izquierda
        elif pos_anterior_x > linea and pos_actual_x <= linea:
            if track.puede_cruzar:
                self._registrar_cruce(track_id, Direccion.DERECHA_A_IZQUIERDA)
                track.puede_cruzar = False
                track.ultimo_lado = 'izquierda'
        
        # Permitir cruzar de nuevo cuando se aleje de la línea
        else:
            distancia_a_linea = abs(pos_actual_x - linea)
            if distancia_a_linea > self.margen_cruce:
                track.puede_cruzar = True
    
    def _registrar_cruce(self, track_id: int, direccion: Direccion) -> None:
        """
        Registra un cruce de línea.
        
        Args:
            track_id: ID del track que cruzó
            direccion: Dirección del cruce
        """
        if track_id not in self.tracks:
            return
        
        track = self.tracks[track_id]
        track.cruzado = True
        track.direccion_cruce = direccion
        
        # Incrementar contador correspondiente
        categoria = track.categoria
        if categoria in self.contadores:
            if direccion == Direccion.IZQUIERDA_A_DERECHA:
                self.contadores[categoria]['izq_der'] += 1
                direccion_str = "Izq→Der"
            else:
                self.contadores[categoria]['der_izq'] += 1
                direccion_str = "Der→Izq"
            
            logger.info(f"Cruce detectado: {categoria} - {direccion_str} (Track ID: {track_id})")
            
            # Llamar callback si está definido
            if self.callback_cruce:
                self.callback_cruce(categoria, direccion, track_id)
    
    def _limpiar_tracks_antiguos(self, tracks_activos: set, max_age: int = 30) -> None:
        """
        Elimina tracks que no han sido vistos recientemente.
        
        Args:
            tracks_activos: Set de tracks activos en el frame actual
            max_age: Número máximo de frames sin ver antes de eliminar
        """
        tracks_a_eliminar = []
        
        for track_id, track_info in self.tracks.items():
            if track_id not in tracks_activos:
                # Marcar para eliminar si ha pasado mucho tiempo
                # En una implementación real, llevaríamos cuenta de frames sin ver
                if track_info.cruzado:
                    tracks_a_eliminar.append(track_id)
        
        for track_id in tracks_a_eliminar:
            del self.tracks[track_id]
    
    def obtener_contadores(self) -> Dict:
        """
        Obtiene el estado actual de todos los contadores.
        
        Returns:
            Diccionario con los contadores por categoría y dirección
        """
        return self.contadores.copy()
    
    def obtener_contador_categoria(self, categoria: str) -> Dict:
        """
        Obtiene los contadores de una categoría específica.
        
        Args:
            categoria: Nombre de la categoría
            
        Returns:
            Diccionario con contadores izq_der y der_izq
        """
        return self.contadores.get(categoria, {'izq_der': 0, 'der_izq': 0})
    
    def obtener_total_cruces(self) -> Dict:
        """
        Obtiene el total de cruces en cada dirección.
        
        Returns:
            Diccionario con totales
        """
        total_izq_der = sum(c['izq_der'] for c in self.contadores.values())
        total_der_izq = sum(c['der_izq'] for c in self.contadores.values())
        
        return {
            'izq_der': total_izq_der,
            'der_izq': total_der_izq,
            'total': total_izq_der + total_der_izq
        }
    
    def reiniciar_contadores(self) -> None:
        """Reinicia todos los contadores a cero."""
        self.contadores = self._inicializar_contadores()
        self.tracks.clear()
        self.siguiente_track_id = 1
        logger.info("Contadores reiniciados")
    
    def dibujar_linea_conteo(
        self, 
        frame: np.ndarray, 
        color: Tuple[int, int, int] = (0, 255, 255),
        grosor: int = 3
    ) -> np.ndarray:
        """
        Dibuja la línea de conteo en el frame.
        
        Args:
            frame: Frame donde dibujar
            color: Color de la línea (BGR)
            grosor: Grosor de la línea en píxeles
            
        Returns:
            Frame con la línea dibujada
        """
        import cv2
        
        frame_con_linea = frame.copy()
        
        # Dibujar línea vertical
        cv2.line(
            frame_con_linea,
            (self.linea_x, 0),
            (self.linea_x, self.alto_frame),
            color,
            grosor
        )
        
        # Agregar flechas indicando direcciones
        # Flecha izquierda a derecha
        cv2.arrowedLine(
            frame_con_linea,
            (self.linea_x - 50, 30),
            (self.linea_x + 50, 30),
            (0, 255, 0),
            2,
            tipLength=0.3
        )
        
        # Flecha derecha a izquierda
        cv2.arrowedLine(
            frame_con_linea,
            (self.linea_x + 50, 60),
            (self.linea_x - 50, 60),
            (0, 0, 255),
            2,
            tipLength=0.3
        )
        
        # Etiquetas
        cv2.putText(
            frame_con_linea,
            "Izq->Der",
            (self.linea_x + 55, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 0),
            1
        )
        
        cv2.putText(
            frame_con_linea,
            "Der->Izq",
            (self.linea_x - 100, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 0, 255),
            1
        )
        
        return frame_con_linea
    
    def obtener_estadisticas(self) -> Dict:
        """
        Obtiene estadísticas detalladas del conteo.
        
        Returns:
            Diccionario con estadísticas
        """
        stats = {
            'contadores': self.contadores.copy(),
            'totales': self.obtener_total_cruces(),
            'tracks_activos': len(self.tracks),
            'posicion_linea': self.linea_x,
            'tracks_que_cruzaron': sum(1 for t in self.tracks.values() if t.cruzado)
        }
        return stats
