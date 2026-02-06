# -*- coding: utf-8 -*-
"""
YoloConteo - Sistema de Conteo Bidireccional de Personas y Vehículos de Movilidad Personal

Este es el archivo principal que integra todos los módulos de la aplicación:
- DetectorYOLO: Detección de objetos con YOLO
- BidirectionalCounter: Conteo bidireccional con tracking
- DataLogger: Registro de datos con GPS
- GUI: Interfaz gráfica con Tkinter

Autor: YoloConteo
Fecha: 2025
"""

import cv2
import numpy as np
import threading
import time
from datetime import datetime
from typing import Optional
import logging
import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar módulos de la aplicación
from config import (
    YOLO_MODEL_PATH, CATEGORIAS, CLASE_A_CATEGORIA,
    CAMERA_INDEX, VIDEO_WIDTH, VIDEO_HEIGHT,
    LINEA_POSICION_DEFAULT, LINEA_COLOR, LINEA_GROSOR,
    CSV_FILENAME, SNAPSHOT_FOLDER, SNAPSHOT_INTERVAL,
    WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT,
    ALERTA_MOVILIDAD_REDUCIDA
)
from detector_yolo import DetectorYOLO
from bidirectional_counter import BidirectionalCounter, Direccion
from data_logger import DataLogger, SnapshotScheduler

# Intentar usar la nueva GUI, si falla usar la anterior
try:
    from gui_nueva import GUI
    logger_temp = logging.getLogger(__name__)
    logger_temp.info("Usando GUI nueva (dashboard)")
except ImportError:
    from gui import GUI
    logger_temp = logging.getLogger(__name__)
    logger_temp.info("Usando GUI original")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YoloConteoApp:
    """
    Clase principal de la aplicación de conteo bidireccional.
    
    Integra todos los componentes: detector YOLO, contador bidireccional,
    logger de datos y la interfaz gráfica.
    """
    
    def __init__(self):
        """Inicializa la aplicación."""
        logger.info("=" * 60)
        logger.info("Iniciando YoloConteo - Sistema de Conteo Bidireccional")
        logger.info("=" * 60)
        
        # Estado de la aplicación
        self.ejecutando = False
        self.pausado = False
        self.captura: Optional[cv2.VideoCapture] = None
        self.hilo_video: Optional[threading.Thread] = None
        
        # Variables para cálculo de FPS
        self.fps = 0.0
        self.frame_count = 0
        self.tiempo_inicio_fps = time.time()
        
        # Frame actual para procesamiento
        self.frame_actual = None
        self.lock_frame = threading.Lock()
        
        # Inicializar componentes
        self._inicializar_componentes()
        
        # Configurar callbacks de la GUI
        self._configurar_callbacks()
        
        logger.info("Aplicación inicializada correctamente")
    
    def _inicializar_componentes(self) -> None:
        """Inicializa todos los componentes de la aplicación."""
        
        # 1. Inicializar DataLogger (obtiene GPS)
        logger.info("Inicializando DataLogger...")
        self.data_logger = DataLogger(
            csv_path=CSV_FILENAME,
            snapshot_folder=SNAPSHOT_FOLDER,
            obtener_gps=True
        )
        
        # 2. Inicializar Detector YOLO
        logger.info("Inicializando Detector YOLO...")
        self.detector = DetectorYOLO(
            model_path=YOLO_MODEL_PATH,
            confidence_threshold=0.5,
            categorias=CATEGORIAS,
            clase_a_categoria=CLASE_A_CATEGORIA
        )
        
        # 3. Inicializar Contador Bidireccional
        logger.info("Inicializando Contador Bidireccional...")
        self.contador = BidirectionalCounter(
            ancho_frame=VIDEO_WIDTH,
            alto_frame=VIDEO_HEIGHT,
            linea_posicion_relativa=LINEA_POSICION_DEFAULT,
            categorias=list(CATEGORIAS.keys()),
            usar_deepsort=True,
            callback_cruce=self._on_cruce_detectado
        )
        
        # 4. Inicializar Programador de Snapshots
        logger.info("Inicializando Programador de Snapshots...")
        self.snapshot_scheduler = SnapshotScheduler(
            self.data_logger,
            intervalo_segundos=SNAPSHOT_INTERVAL
        )
        
        # 5. Inicializar GUI
        logger.info("Inicializando Interfaz Gráfica...")
        self.gui = GUI(
            titulo=WINDOW_TITLE,
            ancho=WINDOW_WIDTH,
            alto=WINDOW_HEIGHT,
            categorias=CATEGORIAS
        )
        
        # Actualizar GPS en la GUI
        lat, lon = self.data_logger.obtener_coordenadas()
        self.gui.actualizar_gps(lat, lon)
        
        # Establecer ubicación si se obtuvo
        ubicacion = self.data_logger.obtener_ubicacion()
        if ubicacion:
            self.gui.establecer_ubicacion(ubicacion)
    
    def _configurar_callbacks(self) -> None:
        """Configura los callbacks de la interfaz gráfica."""
        self.gui.establecer_callbacks(
            iniciar=self._on_iniciar,
            pausar=self._on_pausar,
            reiniciar=self._on_reiniciar,
            exportar=self._on_exportar,
            cerrar=self._on_cerrar,
            slider_linea=self._on_cambio_linea,
            slider_confianza=self._on_cambio_confianza,
            cambiar_ubicacion=self._on_cambiar_ubicacion,
            captura=self._on_capturar_pantalla
        )
    
    def _on_capturar_pantalla(self) -> str:
        """
        Callback para capturar la pantalla actual del video.
        
        Returns:
            Ruta del archivo guardado o string vacío si falla
        """
        with self.lock_frame:
            if self.frame_actual is not None:
                return self.data_logger.guardar_snapshot(
                    self.frame_actual, 
                    prefijo="captura_manual"
                )
        return ""
    
    def _on_cambiar_ubicacion(self, nombre: str, lat: str, lon: str) -> None:
        """
        Callback para cambiar ubicación y coordenadas manualmente.
        
        Args:
            nombre: Nombre de la ubicación
            lat: Latitud como string
            lon: Longitud como string
        """
        try:
            # Establecer nombre
            if nombre:
                self.data_logger.establecer_ubicacion_manual(nombre)
            
            # Establecer coordenadas si son válidas
            if lat and lon:
                lat_float = float(lat)
                lon_float = float(lon)
                self.data_logger.establecer_coordenadas(lat_float, lon_float)
                logger.info(f"Ubicación actualizada: {nombre} ({lat_float}, {lon_float})")
        except ValueError as e:
            logger.error(f"Error al parsear coordenadas: {e}")
            self.gui.mostrar_mensaje(
                "Error de Coordenadas",
                "Las coordenadas deben ser números válidos (ej: 40.4168, -3.7038)",
                "error"
            )
    
    def _inicializar_webcam(self) -> bool:
        """
        Inicializa la captura de video desde la webcam.
        
        Returns:
            True si se inicializó correctamente, False en caso contrario
        """
        try:
            # Primero liberar cualquier captura anterior
            if self.captura is not None:
                self.captura.release()
                self.captura = None
                time.sleep(0.5)  # Dar tiempo a liberar recursos
            
            logger.info(f"Abriendo webcam (índice: {CAMERA_INDEX})...")
            
            # Intentar con DirectShow en Windows para mejor compatibilidad
            self.captura = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
            
            if not self.captura.isOpened():
                # Intentar sin DirectShow como fallback
                logger.warning("Intentando sin DirectShow...")
                self.captura = cv2.VideoCapture(CAMERA_INDEX)
            
            if not self.captura.isOpened():
                logger.error("No se pudo abrir la webcam")
                self.gui.mostrar_mensaje(
                    "Error de Cámara",
                    "No se pudo acceder a la webcam.\nVerifique que esté conectada y no esté en uso por otra aplicación.",
                    "error"
                )
                return False
            
            # Configurar resolución
            self.captura.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
            self.captura.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)
            self.captura.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reducir buffer para menos latencia
            
            # Leer un frame de prueba
            ret, test_frame = self.captura.read()
            if not ret or test_frame is None:
                logger.error("Webcam abierta pero no puede leer frames")
                self.captura.release()
                self.captura = None
                self.gui.mostrar_mensaje(
                    "Error de Cámara",
                    "La webcam se abrió pero no puede capturar video.\nPruebe reiniciar la aplicación.",
                    "error"
                )
                return False
            
            # Obtener resolución real
            ancho_real = int(self.captura.get(cv2.CAP_PROP_FRAME_WIDTH))
            alto_real = int(self.captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            logger.info(f"Webcam inicializada correctamente: {ancho_real}x{alto_real}")
            
            # Actualizar dimensiones del contador
            self.contador.actualizar_dimensiones(ancho_real, alto_real)
            
            return True
            
        except Exception as e:
            logger.error(f"Error al inicializar webcam: {e}")
            self.gui.mostrar_mensaje(
                "Error de Cámara",
                f"Error al inicializar la webcam:\n{str(e)}",
                "error"
            )
            return False
    
    def _liberar_webcam(self) -> None:
        """Libera los recursos de la webcam."""
        if self.captura is not None:
            self.captura.release()
            self.captura = None
            logger.info("Webcam liberada")
    
    def _bucle_video(self) -> None:
        """Bucle principal de captura y procesamiento de video."""
        logger.info("Iniciando bucle de video...")
        
        while self.ejecutando:
            # Verificar pausa
            if self.pausado:
                time.sleep(0.1)
                continue
            
            # Capturar frame
            if self.captura is None or not self.captura.isOpened():
                time.sleep(0.1)
                continue
            
            ret, frame = self.captura.read()
            
            if not ret:
                logger.warning("No se pudo leer frame de la webcam")
                time.sleep(0.1)
                continue
            
            # Procesar frame
            frame_procesado = self._procesar_frame(frame)
            
            # Actualizar frame actual (thread-safe)
            with self.lock_frame:
                self.frame_actual = frame_procesado.copy()
            
            # Actualizar snapshot scheduler
            self.snapshot_scheduler.actualizar_frame(frame_procesado)
            self.snapshot_scheduler.verificar_y_guardar()
            
            # Calcular FPS
            self._calcular_fps()
            
            # Actualizar GUI (debe hacerse en el hilo principal)
            try:
                self.gui.root.after(0, self._actualizar_gui, frame_procesado)
            except Exception:
                pass  # La ventana puede haberse cerrado
            
            # Pequeña pausa para no sobrecargar CPU
            time.sleep(0.01)
        
        logger.info("Bucle de video finalizado")
    
    def _procesar_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Procesa un frame: detección, tracking y dibujo.
        
        Args:
            frame: Frame de entrada (BGR)
            
        Returns:
            Frame procesado con detecciones dibujadas
        """
        # 1. Realizar detección
        detecciones = self.detector.detectar(frame)
        
        # 2. Aplicar tracking y verificar cruces
        detecciones_con_id = self.contador.procesar_detecciones(detecciones, frame)
        
        # 3. Dibujar línea de conteo
        frame_procesado = self.contador.dibujar_linea_conteo(
            frame,
            color=LINEA_COLOR,
            grosor=LINEA_GROSOR
        )
        
        # 4. Dibujar detecciones
        frame_procesado = self.detector.dibujar_detecciones(
            frame_procesado,
            detecciones_con_id,
            dibujar_centro=True
        )
        
        # 5. Agregar información en pantalla
        frame_procesado = self._agregar_info_frame(frame_procesado)
        
        return frame_procesado
    
    def _agregar_info_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Agrega información adicional en el frame (FPS, timestamp, etc.).
        
        Args:
            frame: Frame donde agregar información
            
        Returns:
            Frame con información agregada
        """
        # FPS en esquina superior izquierda
        cv2.putText(
            frame,
            f"FPS: {self.fps:.1f}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        
        # Timestamp en esquina superior derecha
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(
            frame,
            timestamp,
            (frame.shape[1] - 100, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )
        
        # Totales en esquina inferior
        totales = self.contador.obtener_total_cruces()
        texto_totales = f"Total: {totales['total']} | Izq->Der: {totales['izq_der']} | Der->Izq: {totales['der_izq']}"
        cv2.putText(
            frame,
            texto_totales,
            (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )
        
        return frame
    
    def _calcular_fps(self) -> None:
        """Calcula los frames por segundo."""
        self.frame_count += 1
        tiempo_actual = time.time()
        diferencia = tiempo_actual - self.tiempo_inicio_fps
        
        if diferencia >= 1.0:  # Actualizar cada segundo
            self.fps = self.frame_count / diferencia
            self.frame_count = 0
            self.tiempo_inicio_fps = tiempo_actual
    
    def _actualizar_gui(self, frame: np.ndarray) -> None:
        """
        Actualiza la interfaz gráfica con el nuevo frame y datos.
        
        Args:
            frame: Frame procesado para mostrar
        """
        try:
            # Actualizar frame de video
            self.gui.actualizar_frame(frame)
            
            # Actualizar contadores
            contadores = self.contador.obtener_contadores()
            self.gui.actualizar_contadores(contadores)
            
            # Actualizar FPS
            self.gui.actualizar_fps(self.fps)
            
        except Exception as e:
            logger.error(f"Error al actualizar GUI: {e}")
    
    def _on_cruce_detectado(self, categoria: str, direccion: Direccion, track_id: int) -> None:
        """
        Callback cuando se detecta un cruce de línea.
        
        Args:
            categoria: Categoría del objeto
            direccion: Dirección del cruce
            track_id: ID del track
        """
        # Registrar en el DataLogger
        contadores = self.contador.obtener_contadores()
        direccion_str = 'izq_der' if direccion == Direccion.IZQUIERDA_A_DERECHA else 'der_izq'
        
        self.data_logger.registrar_cruce(
            categoria=categoria,
            direccion=direccion_str,
            contadores=contadores
        )
        
        # Verificar alerta de movilidad reducida
        if ALERTA_MOVILIDAD_REDUCIDA and categoria in ['silla_ruedas', 'movilidad_reducida']:
            try:
                self.gui.root.after(0, self.gui.mostrar_alerta_movilidad_reducida)
            except Exception:
                pass
        
        logger.info(f"Cruce registrado: {categoria} - {direccion_str} (ID: {track_id})")
    
    # ==================== CALLBACKS DE LA GUI ====================
    
    def _on_iniciar(self) -> None:
        """Callback para iniciar el conteo."""
        logger.info("Iniciando conteo...")
        
        # Verificar si ya estamos ejecutando
        if self.ejecutando:
            logger.warning("Ya está ejecutando, ignorando...")
            return
        
        # Inicializar webcam
        if not self._inicializar_webcam():
            # Restaurar estado de botones en GUI si falla
            self.gui.ejecutando = False
            self.gui._actualizar_estado_botones()
            return
        
        # Actualizar ubicación desde la GUI
        ubicacion = self.gui.obtener_ubicacion()
        if ubicacion:
            self.data_logger.establecer_ubicacion_manual(ubicacion)
        
        # Actualizar coordenadas desde la GUI
        try:
            lat, lon = self.gui.obtener_coordenadas()
            if lat is not None and lon is not None:
                self.data_logger.establecer_coordenadas(lat, lon)
        except Exception as e:
            logger.warning(f"No se pudieron obtener coordenadas de GUI: {e}")
        
        # Iniciar captura
        self.ejecutando = True
        self.pausado = False
        
        # Iniciar hilo de video
        self.hilo_video = threading.Thread(target=self._bucle_video, daemon=True)
        self.hilo_video.start()
        
        logger.info("Conteo iniciado")
    
    def _on_pausar(self) -> None:
        """Callback para pausar/reanudar el conteo."""
        self.pausado = not self.pausado
        estado = "pausado" if self.pausado else "reanudado"
        logger.info(f"Conteo {estado}")
    
    def _on_reiniciar(self) -> None:
        """Callback para reiniciar los contadores."""
        self.contador.reiniciar_contadores()
        self.data_logger.limpiar_datos()
        
        # Actualizar GUI
        contadores = self.contador.obtener_contadores()
        self.gui.actualizar_contadores(contadores)
        
        logger.info("Contadores reiniciados")
        self.gui.mostrar_mensaje(
            "Contadores Reiniciados",
            "Todos los contadores han sido reiniciados a cero.",
            "info"
        )
    
    def _on_exportar(self) -> None:
        """Callback para exportar los datos."""
        logger.info("Exportando datos...")
        
        # Obtener contadores actuales
        contadores = self.contador.obtener_contadores()
        
        # Actualizar ubicación desde la GUI
        ubicacion = self.gui.obtener_ubicacion()
        if ubicacion:
            self.data_logger.establecer_ubicacion_manual(ubicacion)
        
        # Generar nombre automático con timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_default = f"conteo_{timestamp}.csv"
        
        # Pedir ruta de guardado
        try:
            from tkinter import filedialog
            ruta = filedialog.asksaveasfilename(
                initialfile=nombre_default,
                defaultextension=".csv",
                filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")],
                title="Guardar datos de conteo"
            )
        except Exception as e:
            logger.error(f"Error al abrir diálogo: {e}")
            # Guardar directamente si falla el diálogo
            ruta = nombre_default
        
        if ruta:
            # Exportar
            ruta_exportada = self.data_logger.exportar_resumen(contadores, ruta)
            
            if ruta_exportada:
                self.gui.mostrar_mensaje(
                    "Exportación Exitosa",
                    f"Los datos se han exportado correctamente a:\n{ruta_exportada}",
                    "info"
                )
                logger.info(f"Datos exportados a: {ruta_exportada}")
            else:
                self.gui.mostrar_mensaje(
                    "Error de Exportación",
                    "No se pudieron exportar los datos.",
                    "error"
                )
        else:
            logger.info("Exportación cancelada por el usuario")
    
    def _on_cerrar(self) -> None:
        """Callback para detener la captura (sin cerrar la aplicación)."""
        logger.info("Deteniendo captura...")
        
        # Detener captura
        self.ejecutando = False
        self.pausado = False
        
        # Esperar a que termine el hilo de video
        if self.hilo_video is not None and self.hilo_video.is_alive():
            self.hilo_video.join(timeout=2.0)
            self.hilo_video = None
        
        # Liberar webcam
        self._liberar_webcam()
        
        # Limpiar frame actual
        with self.lock_frame:
            self.frame_actual = None
        
        logger.info("Captura detenida - puede cambiar ubicación y reiniciar")
    
    def _cerrar_aplicacion(self) -> None:
        """Cierra completamente la aplicación."""
        logger.info("Cerrando aplicación...")
        
        # Detener captura si está activa
        self.ejecutando = False
        
        # Esperar a que termine el hilo de video
        if self.hilo_video is not None and self.hilo_video.is_alive():
            self.hilo_video.join(timeout=2.0)
        
        # Liberar webcam
        self._liberar_webcam()
        
        # Guardar snapshot final
        with self.lock_frame:
            if self.frame_actual is not None:
                self.data_logger.guardar_snapshot(self.frame_actual, "final")
        
        # Exportar resumen final
        contadores = self.contador.obtener_contadores()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.data_logger.exportar_resumen(
            contadores,
            f"resumen_final_{timestamp}.csv"
        )
        
        # Cerrar logger
        self.data_logger.cerrar()
        
        # Liberar detector
        self.detector.liberar()
        
        logger.info("Aplicación cerrada correctamente")
    
    def _on_cambio_linea(self, posicion: float) -> None:
        """
        Callback para cambio de posición de línea.
        
        Args:
            posicion: Nueva posición (0.0 a 1.0)
        """
        self.contador.actualizar_posicion_linea(posicion)
        logger.debug(f"Posición de línea actualizada: {posicion}")
    
    def _on_cambio_confianza(self, umbral: float) -> None:
        """
        Callback para cambio de umbral de confianza.
        
        Args:
            umbral: Nuevo umbral (0.0 a 1.0)
        """
        self.detector.actualizar_umbral_confianza(umbral)
        logger.debug(f"Umbral de confianza actualizado: {umbral}")
    
    def ejecutar(self) -> None:
        """Ejecuta la aplicación principal."""
        logger.info("Iniciando interfaz gráfica...")
        
        try:
            self.gui.iniciar()
        except KeyboardInterrupt:
            logger.info("Interrupción por teclado detectada")
            self._cerrar_aplicacion()
        except Exception as e:
            logger.error(f"Error en la aplicación: {e}")
            self._cerrar_aplicacion()
            raise
        finally:
            # Asegurar limpieza al cerrar
            self._cerrar_aplicacion()


def main():
    """Función principal de entrada."""
    print("=" * 60)
    print("  YoloConteo - Sistema de Conteo Bidireccional")
    print("  Detección de Personas y Vehículos de Movilidad Personal")
    print("=" * 60)
    print()
    
    try:
        # Crear e iniciar aplicación
        app = YoloConteoApp()
        app.ejecutar()
        
    except ImportError as e:
        print(f"\nError de importación: {e}")
        print("\nAsegúrese de tener instaladas todas las dependencias:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
        
    except Exception as e:
        print(f"\nError inesperado: {e}")
        logger.exception("Error fatal en la aplicación")
        sys.exit(1)


if __name__ == "__main__":
    main()
