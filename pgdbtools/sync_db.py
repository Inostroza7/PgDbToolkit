##### Clase Sincrónica para Operaciones en la Base de Datos #####

import psycopg
import pandas as pd
from contextlib import contextmanager
from .log import log
from .base import BaseDbTools

##### Context Manager para Conexiones Sincrónicas #####

@contextmanager
def db_connection(db_config):
    """Context manager para manejar conexiones sincrónicas a la base de datos."""
    conn = psycopg.connect(**db_config)
    try:
        yield conn
    finally:
        conn.close()

##### Clase para Gestión de Operaciones Sincrónicas #####

class PgDbTools(BaseDbTools):
    """Gestiona las operaciones sincrónicas de la base de datos."""

    ##### Método para Insertar Registros #####

    def insert_record(self, table_name: str, record: dict) -> None:
        """Inserta un registro en la tabla especificada de manera sincrónica.

        Args:
            table_name (str): Nombre de la tabla en la que se insertará el registro.
            record (dict): Diccionario con los datos del registro a insertar.

        Raises:
            psycopg.Error: Si ocurre un error durante la inserción.
        """
        query = self.build_query(table_name, record, query_type="INSERT")
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(record.values()))
                    conn.commit()
        except psycopg.Error as e:
            log.error(f"Error inserting record into {table_name}: {e}")
            raise

    ##### Método para Consultar Registros #####

    def fetch_records(self, table_name: str, conditions: dict = None) -> pd.DataFrame:
        """Consulta registros de una tabla con condiciones opcionales de manera sincrónica.

        Args:
            table_name (str): Nombre de la tabla de la cual se consultarán los registros.
            conditions (dict, opcional): Diccionario de condiciones para filtrar los registros.

        Returns:
            pd.DataFrame: DataFrame con los registros consultados.

        Raises:
            psycopg.Error: Si ocurre un error durante la consulta.
        """
        query = self.build_query(table_name, conditions, query_type="SELECT")
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    if conditions:
                        cur.execute(query, tuple(conditions.values()))
                    else:
                        cur.execute(query)
                    records = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
            return pd.DataFrame(records, columns=columns)
        except psycopg.Error as e:
            log.error(f"Error fetching records from {table_name}: {e}")
            raise

    ##### Método para Actualizar Registros #####

    def update_record(self, table_name: str, record: dict, conditions: dict) -> None:
        """Actualiza un registro en la tabla especificada basado en las condiciones.

        Args:
            table_name (str): Nombre de la tabla en la que se actualizará el registro.
            record (dict): Diccionario con los datos del registro a actualizar.
            conditions (dict): Diccionario de condiciones para identificar el registro a actualizar.

        Raises:
            psycopg.Error: Si ocurre un error durante la actualización.
        """
        query = self.build_query(table_name, record, conditions, query_type="UPDATE")
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(record.values()) + tuple(conditions.values()))
                    conn.commit()
        except psycopg.Error as e:
            log.error(f"Error updating record in {table_name}: {e}")
            raise

    ##### Método para Eliminar Registros #####

    def delete_record(self, table_name: str, conditions: dict) -> None:
        """Elimina un registro de la tabla especificada basado en las condiciones.

        Args:
            table_name (str): Nombre de la tabla de la cual se eliminará el registro.
            conditions (dict): Diccionario de condiciones para identificar el registro a eliminar.

        Raises:
            psycopg.Error: Si ocurre un error durante la eliminación.
        """
        query = self.build_query(table_name, conditions=conditions, query_type="DELETE")
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(conditions.values()))
                    conn.commit()
        except psycopg.Error as e:
            log.error(f"Error deleting record from {table_name}: {e}")
            raise

    ##### Método para Ejecutar Consultas Personalizadas #####

    def execute_query(self, query: str, params: tuple = None) -> pd.DataFrame:
        """Ejecuta un query SQL personalizado de manera sincrónica.

        Args:
            query (str): El query SQL a ejecutar.
            params (tuple, opcional): Parámetros para el query.

        Returns:
            pd.DataFrame: DataFrame con los resultados del query.

        Raises:
            psycopg.Error: Si ocurre un error durante la ejecución del query.
        """
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    records = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
            return pd.DataFrame(records, columns=columns)
        except psycopg.Error as e:
            log.error(f"Error executing query: {e}")
            raise

    ##### Método Auxiliar para Construcción de Queries #####

    def build_query(self, table_name: str, data: dict = None, conditions: dict = None, query_type: str = "INSERT") -> str:
        """Construye un query SQL basado en el tipo de operación.

        Args:
            table_name (str): Nombre de la tabla.
            data (dict): Diccionario con los datos del registro.
            conditions (dict, opcional): Diccionario de condiciones para filtrar los registros.
            query_type (str, opcional): Tipo de query a construir ('INSERT', 'UPDATE', 'DELETE').

        Returns:
            str: Query SQL construido.

        Raises:
            ValueError: Si el tipo de query no es reconocido.
        """
        if query_type == "INSERT":
            columns = ', '.join([f'"{col}"' for col in data.keys()])
            values = ', '.join(['%s'] * len(data))
            return f"INSERT INTO {table_name} ({columns}) VALUES ({values})"
        
        elif query_type == "UPDATE":
            set_str = ', '.join([f'"{k}" = %s' for k in data.keys()])
            condition_str = ' AND '.join([f'"{k}" = %s' for k in conditions.keys()]) if conditions else ""
            return f"UPDATE {table_name} SET {set_str}" + (f" WHERE {condition_str}" if condition_str else "")
        
        elif query_type == "DELETE":
            if not conditions or len(conditions) == 0:
                raise ValueError("DELETE queries require at least one condition.")
            condition_str = ' AND '.join([f'"{k}" = %s' for k in conditions.keys()])
            return f"DELETE FROM {table_name} WHERE {condition_str}"
        
        elif query_type == "SELECT":
            query = f"SELECT * FROM {table_name}"
            if conditions:
                condition_str = ' AND '.join([f'"{k}" = %s' for k in conditions.keys()])
                query += f" WHERE {condition_str}"
            return query
        
        else:
            raise ValueError(f"Tipo de query {query_type} no reconocido.")