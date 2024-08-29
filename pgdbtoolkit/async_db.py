##### Clase Asíncrona para Operaciones en la Base de Datos #####

import psycopg
import pandas as pd
from psycopg import AsyncConnection
from contextlib import asynccontextmanager
from .log import log
from .base import BaseDbToolkit

##### Context Manager para Conexiones Asíncronas #####

@asynccontextmanager
async def async_db_connection(db_config):
    """Context manager para manejar conexiones asíncronas a la base de datos."""
    conn = await AsyncConnection.connect(**db_config)
    try:
        yield conn
    finally:
        await conn.close()

##### Clase para Gestión de Operaciones Asíncronas #####

class AsyncPgDbToolkit(BaseDbToolkit):
    """Gestiona las operaciones asíncronas de la base de datos."""

    ##### Método para Insertar Registros #####
    
    async def insert_record(self, table_name: str, record: dict) -> None:
        """Inserta un registro en la tabla especificada de manera asíncrona.

        Este método utiliza un context manager para abrir y cerrar la conexión de manera
        eficiente.

        Args:
            table_name (str): Nombre de la tabla en la que se insertará el registro.
            record (dict): Diccionario con los datos del registro a insertar.

        Raises:
            psycopg.Error: Si ocurre un error durante la conexión o la inserción.
        """
        query = self.build_query(table_name, record, query_type="INSERT")
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    await conn.execute(query, tuple(record.values()))
        except psycopg.Error as e:
            log.error(f"Error inserting record into {table_name}: {e}")
            raise

    ##### Método para Consultar Registros #####

    async def fetch_records(self, table_name: str, conditions: dict = None) -> pd.DataFrame:
        """Consulta registros de una tabla con condiciones opcionales de manera asíncrona.

        Este método abre y cierra la conexión utilizando un context manager para asegurar
        la eficiencia en la consulta de registros.

        Args:
            table_name (str): Nombre de la tabla de la cual se consultarán los registros.
            conditions (dict, opcional): Diccionario de condiciones para filtrar los registros.

        Returns:
            pd.DataFrame: DataFrame con los registros consultados.

        Raises:
            Exception: Si ocurre un error durante la consulta.
        """
        query = self.build_query(table_name, conditions, query_type="SELECT")
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    cursor = await conn.execute(query, tuple(conditions.values()) if conditions else ())
                    records = await cursor.fetchall()
                    columns = [desc.name for desc in cursor.get_attributes()] if records else []
            return pd.DataFrame(records, columns=columns)
        except Exception as e:
            log.error(f"Error fetching records from {table_name}: {e}")
            raise

    ##### Método para Actualizar Registros #####

    async def update_record(self, table_name: str, record: dict, conditions: dict) -> None:
        """Actualiza un registro en la tabla especificada basado en las condiciones.

        Args:
            table_name (str): Nombre de la tabla en la que se actualizará el registro.
            record (dict): Diccionario con los datos del registro a actualizar.
            conditions (dict): Diccionario de condiciones para identificar el registro a actualizar.

        Raises:
            Exception: Si ocurre un error durante la actualización.
        """
        query = self.build_query(table_name, record, conditions, query_type="UPDATE")
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    await conn.execute(query, tuple(record.values()) + tuple(conditions.values()))
        except Exception as e:
            log.error(f"Error updating record in {table_name}: {e}")
            raise

    ##### Método para Eliminar Registros #####

    async def delete_record(self, table_name: str, conditions: dict) -> None:
        """Elimina un registro de la tabla especificada basado en las condiciones.

        Args:
            table_name (str): Nombre de la tabla de la cual se eliminará el registro.
            conditions (dict): Diccionario de condiciones para identificar el registro a eliminar.

        Raises:
            Exception: Si ocurre un error durante la eliminación.
        """
        query = self.build_query(table_name, conditions, query_type="DELETE")
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    await conn.execute(query, tuple(conditions.values()))
        except Exception as e:
            log.error(f"Error deleting record from {table_name}: {e}")
            raise

    ##### Método para Ejecutar Consultas Personalizadas #####

    async def execute_query(self, query: str, params: tuple = None) -> pd.DataFrame:
        """Ejecuta un query SQL personalizado de manera asíncrona.

        Args:
            query (str): El query SQL a ejecutar.
            params (tuple, opcional): Parámetros para el query.

        Returns:
            pd.DataFrame: DataFrame con los resultados del query.

        Raises:
            Exception: Si ocurre un error durante la ejecución del query.
        """
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    cursor = await conn.execute(query, params)
                    records = await cursor.fetchall()
                    columns = [desc.name for desc in cursor.get_attributes()] if records else []
            return pd.DataFrame(records, columns=columns)
        except Exception as e:
            log.error(f"Error executing query: {e}")
            raise

    ##### Método Auxiliar para Construcción de Queries #####

    def build_query(self, table_name: str, data: dict = None, conditions: dict = None, query_type: str = "INSERT") -> str:
        """Construye un query SQL basado en el tipo de operación.

        Args:
            table_name (str): Nombre de la tabla.
            data (dict, opcional): Diccionario con los datos del registro.
            conditions (dict, opcional): Diccionario de condiciones para filtrar los registros.
            query_type (str, opcional): Tipo de query a construir ('INSERT', 'UPDATE', 'DELETE', 'SELECT').

        Returns:
            str: Query SQL construido.

        Raises:
            ValueError: Si el tipo de query no es reconocido.
        """
        if query_type == "INSERT":
            columns = ', '.join([f'"{col}"' for col in data.keys()])
            values = ', '.join([f'${i + 1}' for i in range(len(data))])
            return f"INSERT INTO {table_name} ({columns}) VALUES ({values})"
        
        elif query_type == "UPDATE":
            set_str = ', '.join([f'"{k}" = ${i + 1}' for i, k in enumerate(data.keys())])
            condition_str = ' AND '.join([f'"{k}" = ${i + 1 + len(data)}' for i, k in enumerate(conditions.keys())]) if conditions else ""
            return f"UPDATE {table_name} SET {set_str}" + (f" WHERE {condition_str}" if condition_str else "")
        
        elif query_type == "DELETE":
            if not conditions or len(conditions) == 0:
                raise ValueError("DELETE queries require at least one condition.")
            condition_str = ' AND '.join([f'"{k}" = ${i + 1}' for i, k in enumerate(conditions.keys())])
            return f"DELETE FROM {table_name} WHERE {condition_str}"

        elif query_type == "SELECT":
            query = f"SELECT * FROM {table_name}"
            if conditions:
                condition_str = ' AND '.join([f'"{k}" = ${i + 1}' for i, k in enumerate(conditions.keys())])
                query += f" WHERE {condition_str}"
            return query
        
        else:
            raise ValueError(f"Tipo de query {query_type} no reconocido.")
        
