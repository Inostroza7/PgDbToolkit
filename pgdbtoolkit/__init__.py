# __init__.py

"""
PostgreSQL Database Toolkit
--------------------------

Una librería completa para interactuar con PostgreSQL de manera
sincrónica y asíncrona, con soporte para vectores y operaciones avanzadas.

Este paquete proporciona herramientas para gestionar bases de datos,
tablas, registros y realizar consultas de manera eficiente,
tanto en contextos sincrónicos como asincrónicos.
"""

__version__ = '1.0.0'
__author__ = 'PostgreSQL DB Toolkit Team'

# Importar clases principales para facilitar el acceso
from .sync_db import PgDbToolkit, db_connection
from .async_db import AsyncPgDbToolkit, async_db_connection
from .base import BaseDbToolkit
from .log import Log
from .config import load_database_config, format_connection_string
from .connection_pool import PgConnectionPool, PgAsyncConnectionPool
from .migrations import Migration, MigrationManager
from .validation import (
    validate_type, validate_not_empty, validate_length, validate_regex, 
    validate_email, validate_uuid, validate_date, validate_numeric, 
    validate_in_options, validate_json, validate_schema, validate_record
)
from .exceptions import (
    DatabaseError, ConnectionError, QueryError, MissingConfigError,
    InvalidDataError, RecordNotFoundError, DuplicateRecordError,
    TransactionError, SchemaError, MigrationError, PoolError, VectorError,
    ValidationError, ConfigurationError, AuthorizationError
)
from typing import Optional

# Configuración de logging
logger = Log(__name__)

# Configurar exportaciones
__all__ = [
    # Clases principales
    'PgDbToolkit',
    'AsyncPgDbToolkit',
    'BaseDbToolkit',
    
    # Context managers
    'db_connection',
    'async_db_connection',
    
    # Pools de conexiones
    'PgConnectionPool',
    'PgAsyncConnectionPool',
    
    # Migraciones
    'Migration',
    'MigrationManager',
    
    # Utilidades
    'Log',
    'load_database_config',
    'format_connection_string',
    
    # Validación
    'validate_type',
    'validate_not_empty',
    'validate_length',
    'validate_regex',
    'validate_email',
    'validate_uuid',
    'validate_date',
    'validate_numeric',
    'validate_in_options',
    'validate_json',
    'validate_schema', 
    'validate_record',
    
    # Excepciones
    'DatabaseError',
    'ConnectionError',
    'QueryError',
    'MissingConfigError',
    'InvalidDataError',
    'RecordNotFoundError',
    'DuplicateRecordError',
    'TransactionError',
    'SchemaError',
    'MigrationError',
    'PoolError',
    'VectorError',
    'ValidationError',
    'ConfigurationError',
    'AuthorizationError',
]

# Funciones de conveniencia para crear instancias

def create_sync_toolkit(
        db_config=None, 
        dbname=None
        ):
    """
    Crea una instancia sincrónica del toolkit de base de datos.
    
    Args:
        db_config (dict, opcional): Configuración de la conexión.
        dbname (str, opcional): Nombre de la base de datos.
    Returns:
        PgDbToolkit: Instancia del toolkit sincrónico.
    """
    return PgDbToolkit(
        db_config=db_config, 
        dbname=dbname
        )

async def create_async_toolkit(
        db_config=None, 
        dbname=None
        ):
    """
    Crea una instancia asincrónica del toolkit de base de datos.
    
    Args:
        db_config (dict, opcional): Configuración de la conexión.
        dbname (str, opcional): Nombre de la base de datos.
    Returns:
        AsyncPgDbToolkit: Instancia del toolkit asincrónico.
    """
    return AsyncPgDbToolkit(
        db_config=db_config, 
        dbname=dbname
        )