# config.py

"""
Módulo de configuración para la conexión a bases de datos PostgreSQL.
Este módulo maneja la carga de configuración desde variables de entorno o diccionarios.
"""

import os
from typing import Dict, Optional, Any
from dotenv import load_dotenv
from .exceptions import MissingConfigError, ConfigurationError

# Cargar variables de entorno desde .env
load_dotenv(override=True)

# Valores por defecto
DEFAULT_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'user': 'postgres',
    'password': '',
    'dbname': 'postgres',
    'sslmode': 'prefer',
    'connect_timeout': '10'
}

def validate_config(config: Dict[str, Any]) -> bool:
    """
    Valida que la configuración tenga los campos requeridos.
    
    Args:
        config (Dict[str, Any]): Configuración a validar.
        
    Returns:
        bool: True si la configuración es válida, False en caso contrario.
        
    Raises:
        MissingConfigError: Si faltan campos requeridos.
    """
    required_fields = ['host', 'user', 'dbname']
    missing_fields = [field for field in required_fields if field not in config or not config[field]]
    
    if missing_fields:
        raise MissingConfigError(f"Faltan campos requeridos en la configuración: {', '.join(missing_fields)}")
    
    return True

def load_database_config(custom_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Carga la configuración de la base de datos desde un diccionario o el archivo .env.
    
    Args:
        custom_config (Dict[str, Any], opcional): Diccionario con los parámetros de conexión.
        
    Returns:
        Dict[str, Any]: Configuración completa de conexión a la base de datos.
        
    Raises:
        ConfigurationError: Si la configuración es inválida.
    """
    if custom_config:
        config = custom_config.copy()
    else:
        # Cargar desde variables de entorno
        config = {
            'dbname': os.getenv('DB_DATABASE'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'sslmode': os.getenv('DB_SSLMODE', 'prefer'),
            'connect_timeout': os.getenv('DB_CONNECT_TIMEOUT', '10')
        }
    
    # Rellenar valores faltantes con los valores por defecto
    for key, default_value in DEFAULT_CONFIG.items():
        if key not in config or config[key] is None:
            config[key] = default_value
    
    try:
        validate_config(config)
    except MissingConfigError as e:
        raise ConfigurationError(f"Error en la configuración de la base de datos: {str(e)}")
    
    return config

def format_connection_string(config: Dict[str, Any]) -> str:
    """
    Formatea un diccionario de configuración como una cadena de conexión.
    
    Args:
        config (Dict[str, Any]): Configuración de conexión.
        
    Returns:
        str: Cadena de conexión formateada.
    """
    clean_config = {k: v for k, v in config.items() if v is not None}
    return " ".join([f"{key}={value}" for key, value in clean_config.items()])

def get_pool_config(custom_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Obtiene la configuración para un pool de conexiones.
    
    Args:
        custom_config (Dict[str, Any], opcional): Configuración personalizada.
        
    Returns:
        Dict[str, Any]: Configuración para el pool de conexiones.
    """
    db_config = load_database_config(custom_config)
    
    # Valores por defecto para el pool
    pool_config = {
        'min_size': int(os.getenv('DB_POOL_MIN_SIZE', '2')),
        'max_size': int(os.getenv('DB_POOL_MAX_SIZE', '10')),
        'max_idle': int(os.getenv('DB_POOL_MAX_IDLE', '300')),  # 5 minutos
        'max_lifetime': int(os.getenv('DB_POOL_MAX_LIFETIME', '3600')),  # 1 hora
        'timeout': float(os.getenv('DB_POOL_TIMEOUT', '30.0')),
    }
    
    return {**db_config, **pool_config}