# base.py

"""
Clase base para las herramientas de base de datos.
Este módulo proporciona funcionalidades comunes para las implementaciones
sincrónicas y asíncronas de las herramientas de base de datos.
"""

from typing import Dict, Any, Optional
from .config import load_database_config
from .common_utils import (
    sanitize_identifier, sanitize_value, validate_hashable, 
    sanitize_conditions, build_query_parts, 
    _build_where_clause_parts
)

class BaseDbToolkit:
    """
    Clase base que proporciona configuraciones y métodos comunes 
    para las clases de operaciones de base de datos.
    """

    def __init__(
            self, 
            db_config: Optional[Dict[str, Any]] = None, 
            dbname: Optional[str] = None
            ):
        """
        Inicializa la clase base con la configuración de la base de datos.

        Args:
            db_config (dict, opcional): Diccionario con los parámetros de conexión.
            dbname (str, opcional): Nombre de la base de datos a utilizar.
        """
        self.db_config = load_database_config(db_config)

        if dbname:
            self.db_config['dbname'] = dbname

    def change_database(self, dbname: str) -> None:
        """
        Cambia el nombre de la base de datos en la configuración.

        Args:
            dbname (str): Nombre de la nueva base de datos a utilizar.
        """
        self.db_config['dbname'] = dbname

    def sanitize_identifier(self, identifier: str) -> str:
        """
        Sanitiza un identificador SQL para prevenir inyección SQL.

        Args:
            identifier (str): El identificador a sanitizar.

        Returns:
            str: El identificador sanitizado.
        """
        return sanitize_identifier(identifier)

    def sanitize_value(self, value: Any) -> Any:
        """
        Sanitiza un valor para su inserción segura en la base de datos.

        Args:
            value: El valor a sanitizar.

        Returns:
            El valor sanitizado.
        """
        return sanitize_value(value)

    def validate_hashable(self, data: Dict[str, Any]) -> None:
        """
        Valida que todos los valores en un diccionario sean hashables.

        Args:
            data (dict): Diccionario a validar.

        Raises:
            ValueError: Si se encuentra un tipo no hashable.
        """
        validate_hashable(data)

    def sanitize_conditions(self, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convierte automáticamente los integers a strings en las condiciones.

        Args:
            conditions (dict): Diccionario de condiciones.

        Returns:
            dict: Diccionario de condiciones con integers convertidos a strings.
        """
        return sanitize_conditions(conditions)

    def build_query(self, 
                    table_name: str, 
                    columns: list = None, 
                    data: dict = None, 
                    conditions: dict = None, 
                    order_by: list = None, 
                    limit: int = None, 
                    offset: int = None, 
                    query_type: str = "SELECT") -> tuple:
        """
        Construye un query SQL completo basado en el tipo de operación.
        
        Args:
            Todos los argumentos son pasados a la función build_query_parts.
            
        Returns:
            tuple: (query_string, params)
        """
        # Obtener las partes del query desde la función común
        query_parts, params = build_query_parts(
            table_name=table_name,
            columns=columns,
            data=data,
            conditions=conditions,
            order_by=order_by,
            limit=limit,
            offset=offset,
            query_type=query_type
        )
        
        # Construir el query completo
        query = query_parts["base"] + query_parts["where"] + query_parts["order"] + query_parts["limit_offset"]
        
        return query, params

    def _build_where_clause(self, conditions: Dict[str, Any]) -> tuple:
        """
        Construye la cláusula WHERE para las consultas.

        Args:
            conditions (dict): Diccionario de condiciones.

        Returns:
            tuple: (where_clause, params)
        """
        return _build_where_clause_parts(conditions)