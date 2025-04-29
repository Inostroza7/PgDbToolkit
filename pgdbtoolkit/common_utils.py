# common_utils.py

"""
Utilidades comunes para las conexiones sincrónicas y asíncronas con PostgreSQL.
Este módulo contiene funciones y clases utilizadas tanto por la versión sincrónica
como por la versión asíncrona del toolkit.
"""

import json
import re
import numpy as np
import pandas as pd
import io
from typing import Any, Dict, List, Tuple, Union, Optional

def sanitize_identifier(identifier: str) -> str:
    """
    Sanitiza un identificador SQL para prevenir inyección SQL.

    Args:
        identifier (str): El identificador a sanitizar.

    Returns:
        str: El identificador sanitizado.
    """
    return '"{}"'.format(identifier.replace('"', '""'))

def sanitize_value(value: Any) -> Any:
    """
    Sanitiza un valor para su inserción segura en la base de datos.

    Args:
        value: El valor a sanitizar.

    Returns:
        El valor sanitizado, listo para ser insertado en la base de datos.
    """
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    elif isinstance(value, (int, float, str, bool, type(None))):
        return value
    else:
        return str(value)

def validate_hashable(data: Dict[str, Any]) -> None:
    """
    Valida que todos los valores en un diccionario sean hashables.

    Args:
        data (dict): Diccionario a validar.

    Raises:
        ValueError: Si se encuentra un tipo no hashable.
    """
    for key, value in data.items():
        if isinstance(value, (list, dict)):
            raise ValueError(f"Tipo no hashable {type(value)} encontrado para la clave '{key}'. Por favor, conviértalo a un tipo hashable.")

def sanitize_conditions(conditions: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convierte automáticamente los integers a strings en las condiciones.

    Args:
        conditions (dict): Diccionario de condiciones.

    Returns:
        dict: Diccionario de condiciones con integers convertidos a strings.
    """
    return {k: str(v) if isinstance(v, int) else v for k, v in conditions.items()}

def build_query_parts(
        table_name: str, 
        columns: List[str] = None, 
        data: Dict[str, Any] = None, 
        conditions: Dict[str, Any] = None, 
        order_by: List[Tuple[str, str]] = None, 
        limit: int = None, 
        offset: int = None, 
        query_type: str = "SELECT"
        ) -> Tuple[Dict[str, str], List[Any]]:
    """
    Construye las partes de un query SQL basado en el tipo de operación.
    Esta función es la base para los métodos build_query de ambas clases toolkit.

    Args:
        table_name (str): Nombre de la tabla.
        columns (list, opcional): Lista de columnas a seleccionar (solo para SELECT).
        data (dict, opcional): Diccionario con los datos del registro para INSERT y UPDATE.
        conditions (dict, opcional): Diccionario de condiciones avanzadas para filtrar los registros.
        order_by (list, opcional): Lista de tuplas (columna, dirección) para ordenar los resultados.
        limit (int, opcional): Número máximo de registros a devolver.
        offset (int, opcional): Número de registros a saltar.
        query_type (str, opcional): Tipo de query a construir ('SELECT', 'INSERT', 'UPDATE', 'DELETE').

    Returns:
        tuple: (query_parts, params) donde query_parts es un diccionario con partes del query
    """
    sanitized_table = sanitize_identifier(table_name)
    params = []
    query_parts = {
        "base": "",
        "where": "",
        "order": "",
        "limit_offset": ""
    }

    if query_type == "SELECT":
        # Manejo de columnas
        if isinstance(columns, list) and len(columns) == 1 and str(columns[0]).upper().startswith("COUNT("):
            select_clause = columns[0]
        else:
            select_clause = "*" if not columns else ", ".join(map(sanitize_identifier, columns))
        
        query_parts["base"] = f"SELECT {select_clause} FROM {sanitized_table}"
        
        # Condiciones WHERE
        if conditions:
            where_clause, where_params = _build_where_clause_parts(conditions)
            query_parts["where"] = f" WHERE {where_clause}"
            params.extend(where_params)

        # Ordenamiento
        if order_by:
            order_clause = ", ".join([f"{sanitize_identifier(col)} {direction}" for col, direction in order_by])
            query_parts["order"] = f" ORDER BY {order_clause}"
        
        # Límite y offset
        limit_offset = ""
        if limit:
            limit_offset += " LIMIT %s"
            params.append(limit)
        
        if offset:
            limit_offset += " OFFSET %s"
            params.append(offset)
        
        query_parts["limit_offset"] = limit_offset

    elif query_type == "INSERT":
        if not data:
            raise ValueError("INSERT queries require data.")
        columns = ', '.join(map(sanitize_identifier, data.keys()))
        placeholders = ', '.join(['%s'] * len(data))
        query_parts["base"] = f"INSERT INTO {sanitized_table} ({columns}) VALUES ({placeholders})"
        params.extend(data.values())

    elif query_type == "UPDATE":
        if not data:
            raise ValueError("UPDATE queries require data.")
        set_clause = ', '.join([f"{sanitize_identifier(k)} = %s" for k in data.keys()])
        query_parts["base"] = f"UPDATE {sanitized_table} SET {set_clause}"
        params.extend(data.values())
        
        if conditions:
            where_clause, where_params = _build_where_clause_parts(conditions)
            query_parts["where"] = f" WHERE {where_clause}"
            params.extend(where_params)

    elif query_type == "DELETE":
        # DELETE físico normal
        query_parts["base"] = f"DELETE FROM {sanitized_table}"
        
        if conditions:
            where_clause, where_params = _build_where_clause_parts(conditions)
            query_parts["where"] = f" WHERE {where_clause}"
            params.extend(where_params)
        else:
            raise ValueError("DELETE queries require at least one condition.")

    return query_parts, params

def _build_where_clause_parts(conditions: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """
    Construye la cláusula WHERE para las consultas.

    Args:
        conditions (dict): Diccionario de condiciones.

    Returns:
        tuple: (where_clause, params)
    """
    where_clauses = []
    params = []
    for key, value in conditions.items():
        if isinstance(key, tuple):
            column, operator = key
            if operator.upper() == 'IN':
                # Manejo especial para operador IN
                placeholders = ','.join(['%s'] * len(value))
                where_clauses.append(f"{sanitize_identifier(column)} IN ({placeholders})")
                params.extend(value)  # Extender la lista de parámetros con cada elemento
            else:
                where_clauses.append(f"{sanitize_identifier(column)} {operator} %s")
                params.append(value)
        else:
            if value is None:
                where_clauses.append(f"{sanitize_identifier(key)} IS NULL")
            else:
                where_clauses.append(f"{sanitize_identifier(key)} = %s")
                params.append(value)
    
    return " AND ".join(where_clauses), params

def convert_vector_to_sql(vector: List[float]) -> str:
    """
    Convierte un vector (lista de números flotantes) a una representación SQL.

    Args:
        vector (List[float]): Vector numérico (ej. embeddings).

    Returns:
        str: Representación del vector para uso en SQL.
    """
    return f"ARRAY[{', '.join(map(str, vector))}]::vector"

def is_valid_email(email: str) -> bool:
    """
    Valida si una cadena tiene formato de correo electrónico válido.

    Args:
        email (str): Correo electrónico a validar.
        
    Returns:
        bool: True si el formato es válido, False si no.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_valid_uuid(uuid_str: str) -> bool:
    """
    Valida si una cadena tiene formato UUID válido.

    Args:
        uuid_str (str): UUID a validar.
        
    Returns:
        bool: True si el formato es válido, False si no.
    """
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, uuid_str.lower()))

class QueryBuilder:
    """
    Clase para construir consultas SQL de manera programática.
    Utiliza una interfaz fluida para encadenar condiciones y operaciones.
    """
    
    def __init__(self, table_name: str):
        """
        Inicializa un builder para una tabla específica.
        
        Args:
            table_name (str): Nombre de la tabla.
        """
        self.table_name = sanitize_identifier(table_name)
        self.select_columns = []
        self.where_conditions = []
        self.order_by_clauses = []
        self.group_by_columns = []
        self.having_conditions = []
        self.limit_value = None
        self.offset_value = None
        self.join_clauses = []
        self.params = []
        
    def select(self, *columns: str) -> 'QueryBuilder':
        """
        Especifica las columnas a seleccionar.
        
        Args:
            *columns: Nombres de columnas a seleccionar.
            
        Returns:
            QueryBuilder: El mismo builder para encadenamiento.
        """
        self.select_columns.extend(columns)
        return self
        
    def where(self, condition: str, *params: Any) -> 'QueryBuilder':
        """
        Agrega una condición WHERE.
        
        Args:
            condition (str): Condición SQL (usar %s para parámetros).
            *params: Valores para los parámetros en la condición.
            
        Returns:
            QueryBuilder: El mismo builder para encadenamiento.
        """
        self.where_conditions.append(condition)
        self.params.extend(params)
        return self
        
    def order_by(self, column: str, direction: str = "ASC") -> 'QueryBuilder':
        """
        Agrega una cláusula ORDER BY.
        
        Args:
            column (str): Columna para ordenar.
            direction (str): Dirección de ordenamiento (ASC o DESC).
            
        Returns:
            QueryBuilder: El mismo builder para encadenamiento.
        """
        self.order_by_clauses.append(f"{sanitize_identifier(column)} {direction}")
        return self
        
    def group_by(self, *columns: str) -> 'QueryBuilder':
        """
        Agrega columnas a GROUP BY.
        
        Args:
            *columns: Nombres de columnas para agrupar.
            
        Returns:
            QueryBuilder: El mismo builder para encadenamiento.
        """
        self.group_by_columns.extend(columns)
        return self
        
    def having(self, condition: str, *params: Any) -> 'QueryBuilder':
        """
        Agrega una condición HAVING.
        
        Args:
            condition (str): Condición SQL (usar %s para parámetros).
            *params: Valores para los parámetros en la condición.
            
        Returns:
            QueryBuilder: El mismo builder para encadenamiento.
        """
        self.having_conditions.append(condition)
        self.params.extend(params)
        return self
        
    def limit(self, value: int) -> 'QueryBuilder':
        """
        Establece el LIMIT.
        
        Args:
            value (int): Número máximo de registros.
            
        Returns:
            QueryBuilder: El mismo builder para encadenamiento.
        """
        self.limit_value = value
        return self
        
    def offset(self, value: int) -> 'QueryBuilder':
        """
        Establece el OFFSET.
        
        Args:
            value (int): Número de registros a saltar.
            
        Returns:
            QueryBuilder: El mismo builder para encadenamiento.
        """
        self.offset_value = value
        return self
        
    def join(self, table: str, condition: str) -> 'QueryBuilder':
        """
        Agrega una cláusula JOIN.
        
        Args:
            table (str): Tabla a unir.
            condition (str): Condición de unión.
            
        Returns:
            QueryBuilder: El mismo builder para encadenamiento.
        """
        self.join_clauses.append(f"JOIN {sanitize_identifier(table)} ON {condition}")
        return self
        
    def left_join(self, table: str, condition: str) -> 'QueryBuilder':
        """
        Agrega una cláusula LEFT JOIN.
        
        Args:
            table (str): Tabla a unir.
            condition (str): Condición de unión.
            
        Returns:
            QueryBuilder: El mismo builder para encadenamiento.
        """
        self.join_clauses.append(f"LEFT JOIN {sanitize_identifier(table)} ON {condition}")
        return self
        
    def build(self) -> Tuple[str, List[Any]]:
        """
        Construye la consulta SQL.
        
        Returns:
            Tuple[str, List[Any]]: Tupla con la consulta SQL y los parámetros.
        """
        # Construir SELECT
        columns_str = "*"
        if self.select_columns:
            columns_str = ", ".join(map(sanitize_identifier, self.select_columns))
            
        query = f"SELECT {columns_str} FROM {self.table_name}"
        
        # Agregar JOINs
        if self.join_clauses:
            query += " " + " ".join(self.join_clauses)
            
        # Agregar WHERE
        if self.where_conditions:
            query += " WHERE " + " AND ".join(self.where_conditions)
            
        # Agregar GROUP BY
        if self.group_by_columns:
            group_by_str = ", ".join(map(sanitize_identifier, self.group_by_columns))
            query += f" GROUP BY {group_by_str}"
            
        # Agregar HAVING
        if self.having_conditions:
            query += " HAVING " + " AND ".join(self.having_conditions)
            
        # Agregar ORDER BY
        if self.order_by_clauses:
            query += f" ORDER BY {', '.join(self.order_by_clauses)}"
            
        # Agregar LIMIT
        if self.limit_value is not None:
            query += f" LIMIT %s"
            self.params.append(self.limit_value)
            
        # Agregar OFFSET
        if self.offset_value is not None:
            query += f" OFFSET %s"
            self.params.append(self.offset_value)
            
        return query, self.params

def batch_to_values_sql(batch_data: Union[List[dict], pd.DataFrame], 
                      return_only_values: bool = False,
                      column_names: Optional[List[str]] = None) -> Tuple[str, List]:
    """
    Convierte un lote de datos (lista de diccionarios o DataFrame) a formato SQL VALUES
    para consultas parametrizadas.
    
    Args:
        batch_data: Datos en formato lista de diccionarios o DataFrame.
        return_only_values: Si es True, devuelve sólo los valores sin los nombres de columnas.
        column_names: Lista de nombres de columnas a utilizar (opcional).
        
    Returns:
        Tupla (valores_sql, params_aplanados) para usar en consultas parametrizadas.
    """
    # Convertir DataFrame a lista de diccionarios si es necesario
    if isinstance(batch_data, pd.DataFrame):
        dict_list = batch_data.to_dict('records')
    else:
        dict_list = batch_data
        
    if not dict_list:
        return "", []
    
    # Determinar nombres de columnas
    if column_names is None:
        column_names = list(dict_list[0].keys())
    
    # Generar parámetros de posición
    params = []
    values_parts = []
    
    for row in dict_list:
        row_params = []
        for col in column_names:
            row_params.append(row.get(col))
        params.extend(row_params)
        
        placeholders = ", ".join(["%s"] * len(row_params))
        values_parts.append(f"({placeholders})")
    
    # Unir todas las partes VALUES
    values_sql = ", ".join(values_parts)
    
    # Añadir las columnas al inicio si es necesario
    if not return_only_values:
        columns_str = ", ".join([sanitize_identifier(col) for col in column_names])
        values_sql = f"({columns_str}) VALUES {values_sql}"
    
    return values_sql, params

# Nuevas funciones para operaciones COPY
def prepare_data_for_copy(data: Union[List[dict], pd.DataFrame], columns: Optional[List[str]] = None) -> Tuple[io.StringIO, List[str]]:
    """
    Prepara datos para operación COPY en PostgreSQL.
    
    Args:
        data: Datos en formato lista de diccionarios o DataFrame.
        columns: Lista de columnas a incluir. Si es None, se usan todas las columnas.

    Returns:
        Tupla (buffer_io, columns) con datos formateados para COPY y lista de columnas.
    """
    if isinstance(data, pd.DataFrame):
        df = data
    else:
        df = pd.DataFrame(data)
    
    if columns is None:
        columns = df.columns.tolist()
    else:
        # Asegurar que solo usamos columnas que existen en los datos
        columns = [col for col in columns if col in df.columns]
    
    # Crear un buffer en memoria para los datos
    buffer = io.StringIO()
    
    # Escribir datos al buffer en formato TSV (formato aceptado por COPY)
    df[columns].to_csv(buffer, sep='\t', header=False, index=False, na_rep='\\N')
    
    # Mover cursor al inicio del buffer
    buffer.seek(0)
    
    return buffer, columns

def generate_copy_command(table_name: str, columns: List[str]) -> str:
    """
    Genera un comando COPY para PostgreSQL.
    
    Args:
        table_name: Nombre de la tabla.
        columns: Lista de columnas a incluir en la operación COPY.
        
    Returns:
        Comando SQL COPY completo.
    """
    sanitized_table = sanitize_identifier(table_name)
    sanitized_columns = [sanitize_identifier(col) for col in columns]
    columns_str = ", ".join(sanitized_columns)
    
    return f"COPY {sanitized_table} ({columns_str}) FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '\\N')"