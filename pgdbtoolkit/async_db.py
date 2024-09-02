##### Clase Asíncrona para Operaciones en la Base de Datos #####

import psycopg
import pandas as pd
from psycopg import AsyncConnection
from contextlib import asynccontextmanager
import os
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

    ###### Métodos de Base de Datos ######

    async def create_database(self, database_name: str) -> None:
        """Crea una nueva base de datos en el servidor PostgreSQL de manera asíncrona.

        Args:
            database_name (str): Nombre de la base de datos que se desea crear.

        Raises:
            psycopg.Error: Si ocurre un error durante la creación de la base de datos.
        """
        query = f"CREATE DATABASE {database_name}"
        try:
            async with async_db_connection(self.db_config) as conn:
                await conn.set_autocommit(True)
                async with conn.transaction():
                    await conn.execute(query)
            
            # Actualizar la configuración para que utilice la nueva base de datos
            self.db_config['dbname'] = database_name
            os.environ['DB_DATABASE'] = database_name
            log.info(f"Configuration updated to use database {database_name}")
            
        except psycopg.errors.DuplicateDatabase:
            log.warning(f"Database {database_name} already exists.")
            return  # No hacer nada si ya existe
        except psycopg.Error as e:
            log.error(f"Error creating database {database_name}: {e}")
            raise

    async def delete_database(self, database_name: str) -> None:
        """Elimina una base de datos en el servidor PostgreSQL de manera asíncrona.

        Args:
            database_name (str): Nombre de la base de datos que se desea eliminar.

        Raises:
            psycopg.Error: Si ocurre un error durante la eliminación de la base de datos.
        """
        terminate_connections_query = f"""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '{database_name}' AND pid <> pg_backend_pid();
        """

        drop_database_query = f"DROP DATABASE IF EXISTS {database_name}"

        try:
            # Conéctate a la base de datos 'postgres' para ejecutar las siguientes operaciones.
            async with async_db_connection(self.db_config) as conn:
                await conn.set_autocommit(True)

                async with conn.transaction():
                    # Finaliza todas las conexiones activas a la base de datos que quieres eliminar.
                    await conn.execute(terminate_connections_query)

                async with conn.transaction():
                    # Elimina la base de datos.
                    await conn.execute(drop_database_query)

            log.info(f"Database {database_name} deleted successfully.")
        except psycopg.Error as e:
            log.error(f"Error deleting database {database_name}: {e}")
            raise

    async def get_databases(self) -> pd.DataFrame:
        """Obtiene una lista de todas las bases de datos en el servidor PostgreSQL de manera asíncrona.

        Returns:
            pd.DataFrame: DataFrame con los nombres de las bases de datos.

        Raises:
            psycopg.Error: Si ocurre un error durante la consulta.
        """
        query = "SELECT datname FROM pg_database WHERE datistemplate = false"
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    cursor = await conn.execute(query)
                    records = await cursor.fetchall()
                    columns = [desc.name for desc in cursor.get_attributes()] if records else []
            return pd.DataFrame(records, columns=columns)
        except psycopg.Error as e:
            log.error(f"Error fetching databases: {e}")
            raise

    ###### Métodos de Tablas ######

    async def create_table(self, table_name: str, schema: dict) -> None:
        """Crea una nueva tabla en la base de datos con el esquema especificado de manera asíncrona.

        Args:
            table_name (str): Nombre de la tabla que se desea crear.
            schema (dict): Diccionario que define las columnas de la tabla y sus tipos de datos.

        Raises:
            psycopg.Error: Si ocurre un error durante la creación de la tabla.
        """
        schema_str = ', '.join([f"{col} {dtype}" if isinstance(dtype, str) else f"{col} {dtype[0]} {dtype[1]}"
                                for col, dtype in schema.items()])
        
        query = f"CREATE TABLE {table_name} ({schema_str})"
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    await conn.execute(query)
            log.info(f"Table {table_name} created successfully.")
        except psycopg.Error as e:
            log.error(f"Error creating table {table_name}: {e}")
            raise

    async def delete_table(self, table_name: str) -> None:
        """Elimina una tabla de la base de datos de manera asíncrona.

        Args:
            table_name (str): Nombre de la tabla que se desea eliminar.

        Raises:
            psycopg.Error: Si ocurre un error durante la eliminación de la tabla.
        """
        query = f"DROP TABLE IF EXISTS {table_name}"
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    await conn.execute(query)
            log.info(f"Table {table_name} deleted successfully.")
        except psycopg.Error as e:
            log.error(f"Error deleting table {table_name}: {e}")
            raise

    async def alter_table(self,
                          table_name: str,
                          add_column: tuple = None,
                          drop_column: str = None,
                          rename_column: tuple = None,
                          alter_column_type: tuple = None,
                          rename_table: str = None,
                          add_constraint: tuple = None,
                          drop_constraint: str = None,
                          set_column_default: tuple = None,
                          drop_column_default: str = None,
                          set_column_not_null: str = None,
                          drop_column_not_null: str = None) -> None:
        """Realiza múltiples tipos de alteraciones en una tabla existente en la base de datos de manera asíncrona.

        Args:
            table_name (str): Nombre de la tabla que se desea alterar.
            add_column (tuple, opcional): Tupla que contiene el nombre de la columna y el tipo de datos a agregar.
            drop_column (str, opcional): Nombre de la columna que se desea eliminar.
            rename_column (tuple, opcional): Tupla que contiene el nombre actual y el nuevo nombre de la columna.
            alter_column_type (tuple, opcional): Tupla que contiene el nombre de la columna y el nuevo tipo de datos.
            rename_table (str, opcional): Nuevo nombre para la tabla.
            add_constraint (tuple, opcional): Tupla que contiene el nombre de la restricción y la definición de la restricción.
            drop_constraint (str, opcional): Nombre de la restricción que se desea eliminar.
            set_column_default (tuple, opcional): Tupla que contiene el nombre de la columna y el valor por defecto.
            drop_column_default (str, opcional): Nombre de la columna para eliminar su valor por defecto.
            set_column_not_null (str, opcional): Nombre de la columna que se debe configurar como no nula.
            drop_column_not_null (str, opcional): Nombre de la columna para permitir valores nulos.

        Raises:
            psycopg.Error: Si ocurre un error durante la alteración de la tabla.
        """
        alterations = []

        if add_column:
            if isinstance(add_column[1], tuple):
                alterations.append(f"ADD COLUMN {add_column[0]} {add_column[1][0]} {add_column[1][1]}")
            else:
                alterations.append(f"ADD COLUMN {add_column[0]} {add_column[1]}")
        if drop_column:
            alterations.append(f"DROP COLUMN {drop_column}")
        if rename_column:
            alterations.append(f"RENAME COLUMN {rename_column[0]} TO {rename_column[1]}")
        if alter_column_type:
            alterations.append(f"ALTER COLUMN {alter_column_type[0]} TYPE {alter_column_type[1]}")
        if rename_table:
            alterations.append(f"RENAME TO {rename_table}")
        if add_constraint:
            alterations.append(f"ADD CONSTRAINT {add_constraint[0]} {add_constraint[1]}")
        if drop_constraint:
            alterations.append(f"DROP CONSTRAINT {drop_constraint}")
        if set_column_default:
            alterations.append(f"ALTER COLUMN {set_column_default[0]} SET DEFAULT {set_column_default[1]}")
        if drop_column_default:
            alterations.append(f"ALTER COLUMN {drop_column_default} DROP DEFAULT")
        if set_column_not_null:
            alterations.append(f"ALTER COLUMN {set_column_not_null} SET NOT NULL")
        if drop_column_not_null:
            alterations.append(f"ALTER COLUMN {drop_column_not_null} DROP NOT NULL")

        if not alterations:
            raise ValueError("No valid alteration parameters provided.")

        query = f"ALTER TABLE {table_name} " + ", ".join(alterations)

        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    await conn.execute(query)
            log.info(f"Table {table_name} altered successfully with alterations: {', '.join(alterations)}.")
        except psycopg.Error as e:
            log.error(f"Error altering table {table_name}: {e}")
            raise

    async def get_tables(self) -> list:
        """Obtiene una lista con los nombres de todas las tablas en la base de datos de manera asíncrona.

        Returns:
            list: Una lista de cadenas que representan los nombres de las tablas en la base de datos.

        Raises:
            psycopg.Error: Si ocurre un error durante la consulta.
        """
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    cursor = await conn.execute(query)
                    tables = [row[0] for row in await cursor.fetchall()]
            log.info(f"Retrieved {len(tables)} tables from the database.")
            return tables
        except psycopg.Error as e:
            log.error(f"Error retrieving table names: {e}")
            raise

    async def get_table_info(self, table_name: str) -> pd.DataFrame:
        """Obtiene la información de las columnas de una tabla de manera asíncrona, incluyendo nombre, tipo de datos y restricciones.

        Args:
            table_name (str): Nombre de la tabla de la cual se desea obtener la información.

        Returns:
            pd.DataFrame: DataFrame con la información de las columnas de la tabla.

        Raises:
            psycopg.Error: Si ocurre un error durante la consulta.
        """
        query = f"""
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM
            information_schema.columns
        WHERE
            table_name = %s
        ORDER BY
            ordinal_position;
        """

        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    cursor = await conn.execute(query, (table_name,))
                    records = await cursor.fetchall()
                    columns = ['column_name', 'data_type', 'is_nullable', 'column_default']
                    df = pd.DataFrame(records, columns=columns)
                    return df
        except psycopg.Error as e:
            log.error(f"Error fetching table info for {table_name}: {e}")
            raise

    async def truncate_table(self, table_name: str) -> None:
        """Elimina todos los registros de una tabla sin eliminar la tabla de manera asíncrona.

        Args:
            table_name (str): Nombre de la tabla que será truncada.

        Raises:
            psycopg.Error: Si ocurre un error durante la operación.
        """
        query = f"TRUNCATE TABLE {table_name}"
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    await conn.execute(query)
        except psycopg.Error as e:
            log.error(f"Error truncating table {table_name}: {e}")
            raise

    ###### Métodos de Registros ######

    async def insert_record(self, table_name: str, record: dict) -> None:
        """Inserta un registro en la tabla especificada de manera asíncrona.

        Args:
            table_name (str): Nombre de la tabla en la que se insertará el registro.
            record (dict): Diccionario con los datos del registro a insertar.

        Raises:
            psycopg.Error: Si ocurre un error durante la inserción.
        """
        query = self.build_query(table_name, record, query_type="INSERT")
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    await conn.execute(query, tuple(record.values()))
        except psycopg.Error as e:
            log.error(f"Error inserting record into {table_name}: {e}")
            raise

    async def fetch_records(self, table_name: str, conditions: dict = None) -> pd.DataFrame:
        """Consulta registros de una tabla con condiciones opcionales de manera asíncrona.

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

    async def update_record(self, table_name: str, record: dict, conditions: dict) -> None:
        """Actualiza un registro en la tabla especificada basado en las condiciones de manera asíncrona.

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

    async def delete_record(self, table_name: str, conditions: dict) -> None:
        """Elimina un registro de la tabla especificada basado en las condiciones de manera asíncrona.

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