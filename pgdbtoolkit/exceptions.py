# exceptions.py
"""
Excepciones personalizadas para la librería de base de datos.
Este módulo define excepciones específicas que proporcionan
información clara sobre errores relacionados con operaciones
de base de datos.
"""

class DatabaseError(Exception):
    """Excepción base para errores relacionados con la base de datos."""
    pass

class ConnectionError(DatabaseError):
    """Error al conectar con la base de datos."""
    pass

class QueryError(DatabaseError):
    """Error al ejecutar una consulta SQL."""
    pass

class MissingConfigError(DatabaseError):
    """Error cuando falta configuración necesaria para la base de datos."""
    pass

class InvalidDataError(DatabaseError):
    """Error cuando los datos proporcionados son inválidos."""
    pass

class RecordNotFoundError(DatabaseError):
    """Error cuando no se encuentra un registro en la base de datos."""
    pass

class DuplicateRecordError(DatabaseError):
    """Error cuando se intenta insertar un registro duplicado."""
    pass

class TransactionError(DatabaseError):
    """Error durante una transacción de base de datos."""
    pass

class SchemaError(DatabaseError):
    """Error relacionado con el esquema de la base de datos."""
    pass

class MigrationError(DatabaseError):
    """Error relacionado con las migraciones de la base de datos."""
    pass

class PoolError(DatabaseError):
    """Error relacionado con el pool de conexiones."""
    pass

class VectorError(DatabaseError):
    """Error relacionado con operaciones de vectores."""
    pass

class ValidationError(Exception):
    """Excepción para errores de validación de datos."""
    pass

class ConfigurationError(Exception):
    """Excepción para errores de configuración."""
    pass

class AuthorizationError(Exception):
    """Excepción para errores de autorización."""
    pass

class RateLimitError(Exception):
    """Excepción para errores de límite de tasa."""
    pass