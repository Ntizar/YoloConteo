# -*- coding: utf-8 -*-
"""
Módulo DetectorYOLO - Maneja la carga del modelo YOLO y las detecciones.
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Tuple, Optional
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DetectorYOLO:
    """
    Clase para manejar la detección de objetos usando YOLO.
    
    Attributes:
        model: Modelo YOLO cargado
        confidence_threshold: Umbral de confianza para las detecciones
        categorias: Diccionario con las categorías y sus propiedades
        clase_a_categoria: Mapeo de clases YOLO a categorías de la aplicación
    """
    
    def __init__(
        self, 
        model_path: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        categorias: Dict = None,
        clase_a_categoria: Dict = None
    ):
        """
        Inicializa el detector YOLO.
        
        Args:
            model_path: Ruta al archivo del modelo YOLO
            confidence_threshold: Umbral mínimo de confianza para aceptar detecciones
            categorias: Diccionario con las categorías de la aplicación
            clase_a_categoria: Mapeo de nombres de clases YOLO a categorías
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.device = 'cpu'  # Cambiar a 'cuda' si hay GPU disponible
        
        # Categorías por defecto si no se proporcionan (sin patinete, colores B/N)
        self.categorias = categorias or {
            'adulto': {'id': 0, 'nombre': 'Adultos', 'color': (255, 255, 255)},
            'nino': {'id': 1, 'nombre': 'Niños', 'color': (200, 200, 200)},
            'bicicleta': {'id': 2, 'nombre': 'Bicicletas', 'color': (160, 160, 160)},
            'silla_ruedas': {'id': 3, 'nombre': 'Sillas de Ruedas', 'color': (128, 128, 128)},
            'movilidad_reducida': {'id': 4, 'nombre': 'Movilidad Reducida', 'color': (96, 96, 96)},
        }
        
        # Mapeo de clases YOLO a categorías (sin patinete)
        self.clase_a_categoria = clase_a_categoria or {
            'person': 'adulto',
            'pedestrian': 'adulto',
            'child': 'nino',
            'children': 'nino',
            'wheelchair': 'silla_ruedas',
            'bicycle': 'bicicleta',
            'bike': 'bicicleta',
            'mobility aid': 'movilidad_reducida',
            'walker': 'movilidad_reducida',
            'crutches': 'movilidad_reducida',
        }
        
        # Cargar el modelo
        self._cargar_modelo()
    
    def _cargar_modelo(self) -> bool:
        """
        Carga el modelo YOLO desde el archivo especificado.
        
        Returns:
            True si el modelo se cargó correctamente, False en caso contrario
        """
        try:
            logger.info(f"Cargando modelo YOLO desde: {self.model_path}")
            self.model = YOLO(self.model_path)
            
            # Intentar usar GPU si está disponible
            try:
                import torch
                if torch.cuda.is_available():
                    self.device = 'cuda'
                    logger.info("GPU CUDA detectada, usando aceleración por GPU")
                else:
                    logger.info("No se detectó GPU, usando CPU")
            except ImportError:
                logger.info("PyTorch no instalado con CUDA, usando CPU")
            
            logger.info("Modelo YOLO cargado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al cargar el modelo YOLO: {e}")
            return False
    
    def detectar(self, frame: np.ndarray) -> List[Dict]:
        """
        Realiza detección de objetos en un frame.
        
        Args:
            frame: Imagen en formato numpy array (BGR)
            
        Returns:
            Lista de detecciones, cada una con:
            - bbox: [x1, y1, x2, y2] coordenadas del bounding box
            - categoria: Categoría de la aplicación
            - confianza: Nivel de confianza de la detección
            - clase_original: Nombre de la clase original de YOLO
            - centro: (cx, cy) coordenadas del centro del bbox
        """
        if self.model is None:
            logger.warning("Modelo no cargado, no se pueden realizar detecciones")
            return []
        
        detecciones = []
        
        try:
            # Realizar inferencia
            resultados = self.model(
                frame, 
                conf=self.confidence_threshold,
                device=self.device,
                verbose=False
            )
            
            # Procesar resultados
            for resultado in resultados:
                boxes = resultado.boxes
                
                if boxes is None:
                    continue
                
                for i in range(len(boxes)):
                    # Obtener coordenadas del bounding box
                    bbox = boxes.xyxy[i].cpu().numpy()
                    x1, y1, x2, y2 = map(int, bbox)
                    
                    # Obtener confianza y clase
                    confianza = float(boxes.conf[i].cpu().numpy())
                    clase_id = int(boxes.cls[i].cpu().numpy())
                    
                    # Obtener nombre de la clase
                    clase_nombre = self.model.names.get(clase_id, 'unknown').lower()
                    
                    # Mapear a categoría de la aplicación
                    categoria = self._mapear_categoria(clase_nombre)
                    
                    if categoria is None:
                        continue  # Ignorar clases no mapeadas
                    
                    # Calcular centro del bounding box
                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2
                    
                    deteccion = {
                        'bbox': [x1, y1, x2, y2],
                        'categoria': categoria,
                        'confianza': confianza,
                        'clase_original': clase_nombre,
                        'centro': (cx, cy),
                        'ancho': x2 - x1,
                        'alto': y2 - y1
                    }
                    
                    detecciones.append(deteccion)
            
        except Exception as e:
            logger.error(f"Error durante la detección: {e}")
        
        return detecciones
    
    def _mapear_categoria(self, clase_nombre: str) -> Optional[str]:
        """
        Mapea un nombre de clase YOLO a una categoría de la aplicación.
        
        Args:
            clase_nombre: Nombre de la clase detectada por YOLO
            
        Returns:
            Nombre de la categoría de la aplicación o None si no hay mapeo
        """
        # Buscar mapeo directo
        if clase_nombre in self.clase_a_categoria:
            return self.clase_a_categoria[clase_nombre]
        
        # Buscar por coincidencia parcial
        for clave, categoria in self.clase_a_categoria.items():
            if clave in clase_nombre or clase_nombre in clave:
                return categoria
        
        return None
    
    def dibujar_detecciones(
        self, 
        frame: np.ndarray, 
        detecciones: List[Dict],
        dibujar_centro: bool = True
    ) -> np.ndarray:
        """
        Dibuja las detecciones en el frame con bounding boxes coloreados.
        
        Args:
            frame: Imagen donde dibujar
            detecciones: Lista de detecciones a dibujar
            dibujar_centro: Si se debe dibujar un punto en el centro
            
        Returns:
            Frame con las detecciones dibujadas
        """
        frame_dibujado = frame.copy()
        
        for det in detecciones:
            # Obtener información de la detección
            x1, y1, x2, y2 = det['bbox']
            categoria = det['categoria']
            confianza = det['confianza']
            cx, cy = det['centro']
            
            # Obtener color de la categoría
            color = self.categorias.get(categoria, {}).get('color', (255, 255, 255))
            nombre_categoria = self.categorias.get(categoria, {}).get('nombre', categoria)
            
            # Dibujar bounding box
            cv2.rectangle(frame_dibujado, (x1, y1), (x2, y2), color, 2)
            
            # Dibujar etiqueta con fondo
            etiqueta = f"{nombre_categoria}: {confianza:.2f}"
            (ancho_texto, alto_texto), _ = cv2.getTextSize(
                etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            
            # Fondo de la etiqueta
            cv2.rectangle(
                frame_dibujado,
                (x1, y1 - alto_texto - 10),
                (x1 + ancho_texto + 5, y1),
                color,
                -1
            )
            
            # Texto de la etiqueta
            cv2.putText(
                frame_dibujado,
                etiqueta,
                (x1 + 2, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA
            )
            
            # Dibujar punto central si se solicita
            if dibujar_centro:
                cv2.circle(frame_dibujado, (cx, cy), 4, color, -1)
            
            # Agregar ID de tracking si existe
            if 'track_id' in det:
                track_id = det['track_id']
                cv2.putText(
                    frame_dibujado,
                    f"ID:{track_id}",
                    (x1, y2 + 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    1,
                    cv2.LINE_AA
                )
        
        return frame_dibujado
    
    def obtener_clases_disponibles(self) -> List[str]:
        """
        Obtiene la lista de clases que el modelo puede detectar.
        
        Returns:
            Lista de nombres de clases
        """
        if self.model is None:
            return []
        return list(self.model.names.values())
    
    def actualizar_umbral_confianza(self, nuevo_umbral: float) -> None:
        """
        Actualiza el umbral de confianza para las detecciones.
        
        Args:
            nuevo_umbral: Nuevo valor de umbral (0.0 a 1.0)
        """
        self.confidence_threshold = max(0.0, min(1.0, nuevo_umbral))
        logger.info(f"Umbral de confianza actualizado a: {self.confidence_threshold}")
    
    def liberar(self) -> None:
        """
        Libera los recursos del modelo.
        """
        self.model = None
        logger.info("Recursos del detector liberados")


# Función auxiliar para estimar si una persona es niño basándose en tamaño
def estimar_edad_por_tamano(bbox: List[int], frame_height: int) -> str:
    """
    Estima si una persona detectada es niño o adulto basándose en el tamaño
    del bounding box relativo al frame.
    
    Esta es una heurística simple y no es 100% precisa.
    
    Args:
        bbox: [x1, y1, x2, y2] coordenadas del bounding box
        frame_height: Altura total del frame
        
    Returns:
        'nino' o 'adulto' según la estimación
    """
    _, y1, _, y2 = bbox
    altura_bbox = y2 - y1
    ratio_altura = altura_bbox / frame_height
    
    # Umbral aproximado: si ocupa menos del 30% de la altura, podría ser niño
    # (asumiendo que el adulto promedio ocuparía más)
    if ratio_altura < 0.3:
        return 'nino'
    return 'adulto'
