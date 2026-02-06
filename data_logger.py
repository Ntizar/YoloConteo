# -*- coding: utf-8 -*-
"""
Módulo DataLogger - Maneja el guardado de datos en CSV con información GPS.
Organiza los datos en carpetas diarias con coordenadas GPS.
"""

import os
import csv
import threading
from datetime import datetime
from typing import Dict, Optional, List, Tuple
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Intentar importar geocoder para GPS
try:
    import geocoder
    GEOCODER_DISPONIBLE = True
except ImportError:
    GEOCODER_DISPONIBLE = False
    logger.warning("geocoder no está instalado. No se obtendrá ubicación GPS.")

# Intentar importar pandas para manejo de datos
try:
    import pandas as pd
    PANDAS_DISPONIBLE = True
except ImportError:
    PANDAS_DISPONIBLE = False
    logger.warning("pandas no está instalado. Se usará CSV estándar.")


class DataLogger:
    """
    Clase para manejar el registro de datos de conteo con GPS y timestamps.
    
    Guarda los datos en formato CSV con información de ubicación GPS,
    timestamp, categoría detectada y dirección del cruce.
    Organiza los datos en carpetas diarias: datos/YYYY-MM-DD_lat_lon/
    
    Attributes:
        directorio_base: Carpeta raíz para los datos
        latitude: Latitud GPS de la ubicación
        longitude: Longitud GPS de la ubicación
        ubicacion_nombre: Nombre descriptivo de la ubicación
    """
    
    def __init__(
        self,
        csv_path: str = "conteo_bidireccional.csv",
        snapshot_folder: str = "snapshots",
        obtener_gps: bool = True,
        directorio_base: str = "datos"
    ):
        """
        Inicializa el DataLogger con estructura de carpetas diarias.
        
        Args:
            csv_path: Nombre del archivo CSV (se usará dentro de carpeta diaria)
            snapshot_folder: Nombre de subcarpeta para capturas
            obtener_gps: Si se debe intentar obtener coordenadas GPS
            directorio_base: Carpeta raíz donde crear las carpetas diarias
        """
        self.csv_path_original = csv_path
        self.snapshot_folder_name = snapshot_folder
        self.directorio_base = directorio_base
        self.ubicacion_nombre = ""
        self.fecha_sesion = datetime.now().strftime('%Y-%m-%d')
        
        # Coordenadas GPS (se obtienen una vez al inicio)
        self.latitude: Optional[float] = None
        self.longitude: Optional[float] = None
        self.gps_obtenido = False
        
        # Rutas actuales
        self.carpeta_dia: Optional[str] = None
        self.csv_path: Optional[str] = None
        self.snapshot_folder: Optional[str] = None
        
        # Buffer de registros para escritura batch
        self.buffer_registros: List[Dict] = []
        self.lock = threading.Lock()
        
        # Columnas del CSV - formato completo y unificado
        # NOTA: direccion = 0 (Dirección 1, cruce de izquierda a derecha)
        #       direccion = 1 (Dirección 2, cruce de derecha a izquierda)
        self.columnas = [
            'fecha',
            'hora',
            'tipo',
            'direccion',
            'total_tipo',
            'total_dir0',
            'total_dir1',
            'total_sesion',
            'ubicacion',
            'latitude',
            'longitude',
            'sesion_id'
        ]
        
        # Crear directorio base si no existe
        os.makedirs(self.directorio_base, exist_ok=True)
        
        # Obtener GPS si está habilitado
        if obtener_gps:
            self._obtener_gps()
        
        # Crear estructura de carpetas del día
        self._crear_carpeta_dia()
    
    def _crear_carpeta_dia(self) -> None:
        """
        Crea la estructura de carpetas de sesión.
        Formato: datos/Ubicacion_Lat_Lon_Fecha/
        Ejemplo: datos/Calle_Mayor_10_40.4165_n3.7026_2026-01-30/
        """
        try:
            self.fecha_sesion = datetime.now().strftime('%Y-%m-%d')
            
            # Crear nombre de carpeta con ubicación, coordenadas y fecha
            lat_str = f"{self.latitude:.4f}" if self.latitude else "0.0000"
            lon_str = f"{self.longitude:.4f}" if self.longitude else "0.0000"
            
            # Reemplazar puntos negativos para nombres de carpeta válidos
            lat_str = lat_str.replace('-', 'n')
            lon_str = lon_str.replace('-', 'n')
            
            # Formato: Ubicacion_Coordenadas_Fecha
            if self.ubicacion_nombre:
                nombre_ub = self._limpiar_nombre_archivo(self.ubicacion_nombre)
                nombre_carpeta = f"{nombre_ub}_{lat_str}_{lon_str}_{self.fecha_sesion}"
            else:
                nombre_carpeta = f"sesion_{lat_str}_{lon_str}_{self.fecha_sesion}"
            
            self.carpeta_dia = os.path.join(self.directorio_base, nombre_carpeta)
            
            # Crear carpeta de sesión
            os.makedirs(self.carpeta_dia, exist_ok=True)
            
            # Crear carpeta de snapshots dentro
            self.snapshot_folder = os.path.join(self.carpeta_dia, self.snapshot_folder_name)
            os.makedirs(self.snapshot_folder, exist_ok=True)
            
            # Establecer ruta del CSV - nombre simple con hora de inicio
            timestamp = datetime.now().strftime('%H%M%S')
            nombre_csv = f"registros_{timestamp}.csv"
            self.csv_path = os.path.join(self.carpeta_dia, nombre_csv)
            
            # Inicializar CSV
            self._inicializar_csv()
            
            logger.info(f"Carpeta de sesión creada: {self.carpeta_dia}")
            
        except Exception as e:
            logger.error(f"Error al crear carpeta del día: {e}")
            # Fallback a comportamiento original
            self.csv_path = self.csv_path_original
            self.snapshot_folder = self.snapshot_folder_name
            os.makedirs(self.snapshot_folder, exist_ok=True)
            self._inicializar_csv()
    
    def _limpiar_nombre_archivo(self, nombre: str) -> str:
        """
        Limpia un nombre para usar como nombre de archivo válido.
        
        Args:
            nombre: Nombre a limpiar
            
        Returns:
            Nombre limpio válido para archivos
        """
        import re
        # Reemplazar caracteres no válidos
        nombre_limpio = re.sub(r'[<>:"/\\|?*]', '', nombre)
        # Reemplazar espacios y comas por guiones bajos
        nombre_limpio = re.sub(r'[\s,]+', '_', nombre_limpio)
        # Eliminar caracteres especiales pero mantener letras con acentos
        nombre_limpio = re.sub(r'[^\w\-áéíóúÁÉÍÓÚñÑ]', '', nombre_limpio)
        # Limitar longitud
        nombre_limpio = nombre_limpio[:50] if len(nombre_limpio) > 50 else nombre_limpio
        return nombre_limpio or "conteo"
    
    def _inicializar_csv(self) -> None:
        """Inicializa el archivo CSV con las cabeceras si no existe."""
        try:
            if self.csv_path and not os.path.exists(self.csv_path):
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.columnas)
                    writer.writeheader()
                logger.info(f"Archivo CSV inicializado: {self.csv_path}")
            else:
                logger.info(f"Archivo CSV existente encontrado: {self.csv_path}")
        except Exception as e:
            logger.error(f"Error al inicializar CSV: {e}")
    
    def _obtener_gps(self) -> None:
        """
        Obtiene las coordenadas GPS de la ubicación actual.
        
        Utiliza la librería geocoder para obtener la ubicación basada en IP.
        Las coordenadas se obtienen una sola vez al inicio.
        """
        if not GEOCODER_DISPONIBLE:
            logger.warning("No se puede obtener GPS: geocoder no está instalado")
            return
        
        try:
            logger.info("Obteniendo ubicación GPS...")
            g = geocoder.ip('me')
            
            if g.ok and g.latlng:
                self.latitude, self.longitude = g.latlng
                self.gps_obtenido = True
                logger.info(f"Ubicación GPS obtenida: {self.latitude}, {self.longitude}")
                
                # Intentar obtener nombre de la ubicación
                if g.city and g.country:
                    self.ubicacion_nombre = f"{g.city}, {g.country}"
                    logger.info(f"Ubicación: {self.ubicacion_nombre}")
            else:
                logger.warning("No se pudo obtener la ubicación GPS")
                
        except Exception as e:
            logger.error(f"Error al obtener GPS: {e}")
    
    def establecer_ubicacion_manual(self, nombre: str) -> None:
        """
        Establece manualmente el nombre de la ubicación.
        
        Args:
            nombre: Nombre descriptivo de la ubicación
        """
        self.ubicacion_nombre = nombre
        logger.info(f"Ubicación establecida manualmente: {nombre}")
    
    def establecer_coordenadas(self, lat: float, lon: float) -> None:
        """
        Establece manualmente las coordenadas GPS.
        Recrea la carpeta del día si las coordenadas cambian significativamente.
        
        Args:
            lat: Latitud
            lon: Longitud
        """
        coordenadas_cambiaron = (
            self.latitude is None or 
            self.longitude is None or
            abs(self.latitude - lat) > 0.001 or 
            abs(self.longitude - lon) > 0.001
        )
        
        self.latitude = lat
        self.longitude = lon
        self.gps_obtenido = True
        logger.info(f"Coordenadas establecidas manualmente: {lat}, {lon}")
        
        # Si cambió la fecha o las coordenadas, recrear carpeta
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        if fecha_actual != self.fecha_sesion or coordenadas_cambiaron:
            self._crear_carpeta_dia()
    
    def obtener_coordenadas(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Obtiene las coordenadas GPS actuales.
        
        Returns:
            Tupla (latitud, longitud) o (None, None) si no están disponibles
        """
        return (self.latitude, self.longitude)
    
    def obtener_ubicacion(self) -> str:
        """
        Obtiene el nombre de la ubicación actual.
        
        Returns:
            Nombre de la ubicación o string vacío
        """
        return self.ubicacion_nombre
    
    def obtener_carpeta_dia(self) -> Optional[str]:
        """
        Obtiene la ruta de la carpeta del día actual.
        
        Returns:
            Ruta de la carpeta o None
        """
        return self.carpeta_dia
    
    def registrar_cruce(
        self,
        categoria: str,
        direccion: str,
        contadores: Dict
    ) -> None:
        """
        Registra un evento de cruce de línea.
        
        Args:
            categoria: Categoría del objeto que cruzó (tipo)
            direccion: Dirección del cruce ('izq_der' o 'der_izq')
            contadores: Diccionario con los contadores actuales
        
        Nota sobre direcciones:
            - 0 = Dirección 1 (izquierda → derecha en la pantalla)
            - 1 = Dirección 2 (derecha → izquierda en la pantalla)
        """
        timestamp = datetime.now()
        
        # Obtener contadores de la categoría
        contador_cat = contadores.get(categoria, {'izq_der': 0, 'der_izq': 0})
        total_cat = contador_cat['izq_der'] + contador_cat['der_izq']
        
        # Calcular totales de sesión
        total_dir0 = sum(c.get('izq_der', 0) for c in contadores.values())
        total_dir1 = sum(c.get('der_izq', 0) for c in contadores.values())
        total_sesion = total_dir0 + total_dir1
        
        # Mapeo de categorías a nombres legibles
        nombres_tipo = {
            'adulto': 'Adulto',
            'nino': 'Nino',
            'bicicleta': 'Bicicleta',
            'silla_ruedas': 'Silla_Ruedas',
            'movilidad_reducida': 'Movilidad_Reducida'
        }
        
        # Dirección: 0 = izq->der, 1 = der->izq
        dir_valor = 0 if direccion == 'izq_der' else 1
        
        # ID de sesión basado en hora de inicio
        sesion_id = os.path.basename(self.carpeta_dia) if self.carpeta_dia else 'sesion'
        
        registro = {
            'fecha': timestamp.strftime('%Y-%m-%d'),
            'hora': timestamp.strftime('%H:%M:%S'),
            'tipo': nombres_tipo.get(categoria, categoria),
            'direccion': dir_valor,
            'total_tipo': total_cat,
            'total_dir0': total_dir0,
            'total_dir1': total_dir1,
            'total_sesion': total_sesion,
            'ubicacion': self.ubicacion_nombre,
            'latitude': self.latitude if self.latitude else '',
            'longitude': self.longitude if self.longitude else '',
            'sesion_id': sesion_id
        }
        
        # Agregar al buffer de forma thread-safe
        with self.lock:
            self.buffer_registros.append(registro)
        
        # Escribir inmediatamente al CSV
        self._escribir_registro(registro)
        
        logger.debug(f"Cruce registrado: {categoria} - direccion={dir_valor}")
    
    def _escribir_registro(self, registro: Dict) -> None:
        """
        Escribe un registro individual al archivo CSV.
        
        Args:
            registro: Diccionario con los datos a escribir
        """
        # Verificar si cambió el día y recrear carpeta
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        if fecha_actual != self.fecha_sesion:
            self._crear_carpeta_dia()
        
        try:
            if self.csv_path:
                with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.columnas)
                    writer.writerow(registro)
        except Exception as e:
            logger.error(f"Error al escribir registro en CSV: {e}")
    
    def exportar_resumen(self, contadores: Dict, ruta_salida: str = None) -> str:
        """
        Exporta un resumen de los contadores a un archivo CSV.
        Usa el MISMO formato que los registros individuales para consistencia.
        
        Args:
            contadores: Diccionario con los contadores actuales
            ruta_salida: Ruta del archivo de salida (opcional)
            
        Returns:
            Ruta del archivo exportado
        """
        if ruta_salida is None:
            timestamp = datetime.now().strftime('%H%M%S')
            # Guardar en carpeta de sesión si está disponible
            if self.carpeta_dia:
                ruta_salida = os.path.join(self.carpeta_dia, f"resumen_{timestamp}.csv")
            else:
                fecha = datetime.now().strftime('%Y-%m-%d')
                if self.ubicacion_nombre:
                    nombre_ub = self._limpiar_nombre_archivo(self.ubicacion_nombre)
                    ruta_salida = f"resumen_{nombre_ub}_{fecha}_{timestamp}.csv"
                else:
                    ruta_salida = f"resumen_{fecha}_{timestamp}.csv"
        
        try:
            # Mapeo de categorías a nombres legibles
            nombres_tipo = {
                'adulto': 'Adulto',
                'nino': 'Nino',
                'bicicleta': 'Bicicleta',
                'silla_ruedas': 'Silla_Ruedas',
                'movilidad_reducida': 'Movilidad_Reducida'
            }
            
            # MISMO formato que registros para consistencia
            # direccion: 0 = Dir1 (izq->der), 1 = Dir2 (der->izq)
            columnas_resumen = [
                'fecha',
                'hora',
                'tipo',
                'total_dir0',
                'total_dir1',
                'total_tipo',
                'total_sesion',
                'ubicacion',
                'latitude',
                'longitude',
                'sesion_id',
                'notas'
            ]
            
            timestamp_now = datetime.now()
            fecha_str = timestamp_now.strftime('%Y-%m-%d')
            hora_str = timestamp_now.strftime('%H:%M:%S')
            sesion_id = os.path.basename(self.carpeta_dia) if self.carpeta_dia else 'sesion'
            
            # Calcular totales globales
            total_dir0_global = sum(c.get('izq_der', 0) for c in contadores.values())
            total_dir1_global = sum(c.get('der_izq', 0) for c in contadores.values())
            total_sesion = total_dir0_global + total_dir1_global
            
            with open(ruta_salida, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columnas_resumen)
                writer.writeheader()
                
                # Escribir fila por cada tipo
                for categoria, counts in contadores.items():
                    fila = {
                        'fecha': fecha_str,
                        'hora': hora_str,
                        'tipo': nombres_tipo.get(categoria, categoria),
                        'total_dir0': counts.get('izq_der', 0),
                        'total_dir1': counts.get('der_izq', 0),
                        'total_tipo': counts.get('izq_der', 0) + counts.get('der_izq', 0),
                        'total_sesion': total_sesion,
                        'ubicacion': self.ubicacion_nombre,
                        'latitude': self.latitude if self.latitude else '',
                        'longitude': self.longitude if self.longitude else '',
                        'sesion_id': sesion_id,
                        'notas': ''
                    }
                    writer.writerow(fila)
                
                # Fila de totales
                fila_total = {
                    'fecha': fecha_str,
                    'hora': hora_str,
                    'tipo': 'TOTAL',
                    'total_dir0': total_dir0_global,
                    'total_dir1': total_dir1_global,
                    'total_tipo': total_sesion,
                    'total_sesion': total_sesion,
                    'ubicacion': self.ubicacion_nombre,
                    'latitude': self.latitude if self.latitude else '',
                    'longitude': self.longitude if self.longitude else '',
                    'sesion_id': sesion_id,
                    'notas': 'dir0=izq->der | dir1=der->izq'
                }
                writer.writerow(fila_total)
            
            logger.info(f"Resumen exportado a: {ruta_salida}")
            return ruta_salida
            
        except Exception as e:
            logger.error(f"Error al exportar resumen: {e}")
            return ""
    
    def guardar_snapshot(self, frame, prefijo: str = "snapshot") -> str:
        """
        Guarda una captura de pantalla del frame actual.
        
        Args:
            frame: Frame de video a guardar (numpy array)
            prefijo: Prefijo para el nombre del archivo
            
        Returns:
            Ruta del archivo guardado o string vacío si falla
        """
        try:
            import cv2
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre_archivo = f"{prefijo}_{timestamp}.jpg"
            ruta_completa = os.path.join(self.snapshot_folder, nombre_archivo)
            
            cv2.imwrite(ruta_completa, frame)
            logger.info(f"Snapshot guardado: {ruta_completa}")
            return ruta_completa
            
        except Exception as e:
            logger.error(f"Error al guardar snapshot: {e}")
            return ""
    
    def obtener_estadisticas_sesion(self) -> Dict:
        """
        Obtiene estadísticas de la sesión actual.
        
        Returns:
            Diccionario con estadísticas
        """
        with self.lock:
            num_registros = len(self.buffer_registros)
        
        return {
            'registros_totales': num_registros,
            'archivo_csv': self.csv_path,
            'ubicacion': self.ubicacion_nombre,
            'gps_disponible': self.gps_obtenido,
            'coordenadas': (self.latitude, self.longitude)
        }
    
    def obtener_datos_como_dataframe(self) -> Optional['pd.DataFrame']:
        """
        Lee los datos del CSV y los retorna como DataFrame de pandas.
        
        Returns:
            DataFrame con los datos o None si no está disponible
        """
        if not PANDAS_DISPONIBLE:
            logger.warning("pandas no está disponible")
            return None
        
        try:
            if os.path.exists(self.csv_path):
                return pd.read_csv(self.csv_path)
            else:
                logger.warning(f"Archivo CSV no encontrado: {self.csv_path}")
                return None
        except Exception as e:
            logger.error(f"Error al leer CSV con pandas: {e}")
            return None
    
    def limpiar_datos(self) -> None:
        """Limpia el buffer de registros (no elimina el archivo CSV)."""
        with self.lock:
            self.buffer_registros.clear()
        logger.info("Buffer de registros limpiado")
    
    def cerrar(self) -> None:
        """
        Cierra el DataLogger y guarda cualquier dato pendiente.
        """
        # Asegurar que todos los registros estén escritos
        with self.lock:
            registros_pendientes = len(self.buffer_registros)
        
        if registros_pendientes > 0:
            logger.info(f"Guardando {registros_pendientes} registros pendientes...")
        
        logger.info("DataLogger cerrado correctamente")


class SnapshotScheduler:
    """
    Programador de snapshots automáticos.
    
    Guarda capturas de pantalla a intervalos regulares.
    """
    
    def __init__(
        self,
        data_logger: DataLogger,
        intervalo_segundos: int = 300
    ):
        """
        Inicializa el programador de snapshots.
        
        Args:
            data_logger: Instancia del DataLogger
            intervalo_segundos: Intervalo entre snapshots en segundos
        """
        self.data_logger = data_logger
        self.intervalo = intervalo_segundos
        self.ultimo_snapshot = datetime.now()
        self.activo = True
        self.frame_actual = None
        self.lock = threading.Lock()
    
    def actualizar_frame(self, frame) -> None:
        """
        Actualiza el frame actual para snapshots.
        
        Args:
            frame: Frame de video actual
        """
        with self.lock:
            self.frame_actual = frame.copy() if frame is not None else None
    
    def verificar_y_guardar(self) -> Optional[str]:
        """
        Verifica si es momento de guardar un snapshot y lo guarda.
        
        Returns:
            Ruta del snapshot guardado o None
        """
        if not self.activo:
            return None
        
        ahora = datetime.now()
        diferencia = (ahora - self.ultimo_snapshot).total_seconds()
        
        if diferencia >= self.intervalo:
            with self.lock:
                frame = self.frame_actual
            
            if frame is not None:
                ruta = self.data_logger.guardar_snapshot(frame, "auto_snapshot")
                self.ultimo_snapshot = ahora
                return ruta
        
        return None
    
    def detener(self) -> None:
        """Detiene el programador de snapshots."""
        self.activo = False
    
    def reanudar(self) -> None:
        """Reanuda el programador de snapshots."""
        self.activo = True
        self.ultimo_snapshot = datetime.now()
