# log.py

"""
Módulo de registro (logging) para la librería pg_toolkit.
Proporciona una clase para gestionar los logs de manera centralizada.
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, Any

# Configuración base para los loggers
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_LOG_LEVEL = logging.INFO

class Log:
    """
    Clase para gestionar los logs del sistema de manera centralizada.
    Proporciona métodos para registrar mensajes con diferentes niveles de severidad.
    """
    
    # Diccionario para mantener una referencia a los loggers creados
    _loggers: Dict[str, logging.Logger] = {}
    
    # Flag para indicar si la configuración global ya se ha aplicado
    _configured = False
    
    # Configuración global
    _log_level = DEFAULT_LOG_LEVEL
    _log_format = DEFAULT_FORMAT
    _log_date_format = DEFAULT_DATE_FORMAT
    _log_file = None
    
    def __init__(self, name: str):
        """
        Inicializa un logger con el nombre especificado.
        
        Args:
            name (str): Nombre del logger, generalmente __name__.
        """
        if name in Log._loggers:
            self.logger = Log._loggers[name]
        else:
            self.logger = logging.getLogger(name)
            Log._loggers[name] = self.logger
            
            # Aplicar configuración global si no se ha hecho
            if not Log._configured:
                Log.configure()
                
            # Aplicar nivel de log específico
            self.logger.setLevel(Log._log_level)
    
    @classmethod
    def configure(cls, 
                  level: int = None, 
                  format_str: str = None, 
                  date_format: str = None, 
                  log_file: str = None,
                  console: bool = True):
        """
        Configura el sistema de logs globalmente.
        
        Args:
            level (int, opcional): Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            format_str (str, opcional): Formato de los mensajes de log.
            date_format (str, opcional): Formato de fecha y hora para los logs.
            log_file (str, opcional): Ruta al archivo de log.
            console (bool, opcional): Si se deben mostrar los logs en consola.
        """
        cls._log_level = level or cls._log_level or DEFAULT_LOG_LEVEL
        cls._log_format = format_str or cls._log_format or DEFAULT_FORMAT
        cls._log_date_format = date_format or cls._log_date_format or DEFAULT_DATE_FORMAT
        cls._log_file = log_file or cls._log_file
        
        # Configurar handler raíz
        root_logger = logging.getLogger()
        
        # Eliminar handlers existentes
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Crear formateador
        formatter = logging.Formatter(cls._log_format, cls._log_date_format)
        
        # Agregar handler de consola si se solicita
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # Agregar handler de archivo si se proporciona
        if cls._log_file:
            log_dir = os.path.dirname(cls._log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
                
            file_handler = logging.FileHandler(cls._log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # Establecer nivel para el logger raíz
        root_logger.setLevel(cls._log_level)
        
        # Marcar como configurado
        cls._configured = True
        
        # Actualizar la configuración para los loggers existentes
        for logger in cls._loggers.values():
            logger.setLevel(cls._log_level)
    
    @classmethod
    def set_level(cls, level: int):
        """
        Establece el nivel de log global.
        
        Args:
            level (int): Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        """
        cls._log_level = level
        logging.getLogger().setLevel(level)
        
        # Actualizar loggers existentes
        for logger in cls._loggers.values():
            logger.setLevel(level)
    
    def debug(self, message: str, *args, **kwargs):
        """
        Registra un mensaje con nivel DEBUG.
        
        Args:
            message (str): Mensaje a registrar.
            *args, **kwargs: Argumentos adicionales para el logger.
        """
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """
        Registra un mensaje con nivel INFO.
        
        Args:
            message (str): Mensaje a registrar.
            *args, **kwargs: Argumentos adicionales para el logger.
        """
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """
        Registra un mensaje con nivel WARNING.
        
        Args:
            message (str): Mensaje a registrar.
            *args, **kwargs: Argumentos adicionales para el logger.
        """
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """
        Registra un mensaje con nivel ERROR.
        
        Args:
            message (str): Mensaje a registrar.
            *args, **kwargs: Argumentos adicionales para el logger.
        """
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """
        Registra un mensaje con nivel CRITICAL.
        
        Args:
            message (str): Mensaje a registrar.
            *args, **kwargs: Argumentos adicionales para el logger.
        """
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, exc_info=True, **kwargs):
        """
        Registra un mensaje con nivel ERROR incluyendo información de la excepción.
        
        Args:
            message (str): Mensaje a registrar.
            *args, **kwargs: Argumentos adicionales para el logger.
            exc_info (bool, opcional): Si se debe incluir información de la excepción.
        """
        self.logger.exception(message, *args, exc_info=exc_info, **kwargs)

# Configurar logger por defecto
Log.configure()