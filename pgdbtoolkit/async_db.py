##### Clase Asíncrona para Operaciones en la Base de Datos #####

import psycopg
import pandas as pd
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector_async
from contextlib import asynccontextmanager
import os
from .log import Log
from .base import BaseDbToolkit
import json
import numpy as np
from typing import Optional, List, Dict, Union, Tuple
from pathlib import Path

logger = Log(__name__)

##### Context Manager para Conexiones Asíncronas #####

@asynccontextmanager
async def async_db_connection(db_config):
    """
    Context manager para manejar conexiones asíncronas a la base de datos.
    
    Args:
        db_config (dict): Configuración de la base de datos.

    Yields:
        AsyncConnection: Una conexión asíncrona a la base de datos.
    """
    conn = await AsyncConnection.connect(**db_config)
    try:
        try:
            await register_vector_async(conn)
        except psycopg.ProgrammingError as e:
            logger.warning(f"Error al registrar el tipo vector: {e}. Continuando sin soporte de vectores.")
        yield conn
    finally:
        await conn.close()

##### Clase para Gestión de Operaciones Asíncronas #####

class AsyncPgDbToolkit(BaseDbToolkit):
    """
    Gestiona las operaciones asíncronas de la base de datos PostgreSQL.
    Proporciona métodos para crear, eliminar y modificar bases de datos, tablas y registros.
    """

    @staticmethod
    def validate_hashable(data: dict) -> None:
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

    @staticmethod
    def sanitize_conditions(conditions: dict) -> dict:
        """
        Convierte automáticamente los integers a strings en las condiciones.

        Args:
            conditions (dict): Diccionario de condiciones.

        Returns:
            dict: Diccionario de condiciones con integers convertidos a strings.
        """
        return {k: str(v) if isinstance(v, int) else v for k, v in conditions.items()}

    ###### Métodos de Base de Datos ######

    async def create_database(self, database_name: str) -> None:
        """
        Crea una nueva base de datos en el servidor PostgreSQL y actualiza la configuración.

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
            logger.info(f"Configuration updated to use database {database_name}")
            
        except psycopg.errors.DuplicateDatabase:
            logger.warning(f"Database {database_name} already exists.")
            return
        except psycopg.Error as e:
            logger.error(f"Error creating database {database_name}: {e}")
            raise

    async def delete_database(self, database_name: str) -> None:
        """
        Elimina una base de datos existente en el servidor PostgreSQL.

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
            async with async_db_connection(self.db_config) as conn:
                await conn.set_autocommit(True)
                async with conn.transaction():
                    await conn.execute(terminate_connections_query)
                async with conn.transaction():
                    await conn.execute(drop_database_query)
            logger.info(f"Database {database_name} deleted successfully.")
        except psycopg.Error as e:
            logger.error(f"Error deleting database {database_name}: {e}")
            raise

    async def get_databases(self) -> pd.DataFrame:
        """
        Obtiene una lista de todas las bases de datos en el servidor PostgreSQL.

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
                    columns = [desc.name for desc in cursor.description]
            return pd.DataFrame(records, columns=columns)
        except psycopg.Error as e:
            logger.error(f"Error fetching databases: {e}")
            raise

    ###### Métodos de Tablas ######

    async def create_table(self, table_name: str, schema: dict) -> None:
        """
        Crea una nueva tabla en la base de datos con el esquema especificado.

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
            logger.info(f"Table {table_name} created successfully.")
        except psycopg.Error as e:
            logger.error(f"Error creating table {table_name}: {e}")
            raise

    async def delete_table(self, table_name: str) -> None:
        """
        Elimina una tabla de la base de datos.

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
            logger.info(f"Table {table_name} deleted successfully.")
        except psycopg.Error as e:
            logger.error(f"Error deleting table {table_name}: {e}")
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
        """
        Realiza múltiples tipos de alteraciones en una tabla existente.
        
        Args: [Mismos argumentos que en la versión sync]
        
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
            logger.info(f"Table {table_name} altered successfully with alterations: {', '.join(alterations)}.")
        except psycopg.Error as e:
            logger.error(f"Error altering table {table_name}: {e}")
            raise

    async def get_tables(self) -> list:
        """
        Obtiene una lista con los nombres de todas las tablas en la base de datos.

        Returns:
            list: Una lista de cadenas que representan los nombres de las tablas.

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
            logger.info(f"Retrieved {len(tables)} tables from the database.")
            return tables
        except psycopg.Error as e:
            logger.error(f"Error retrieving table names: {e}")
            raise

    async def get_table_info(self, table_name: str) -> pd.DataFrame:
        """
        Obtiene la información de las columnas de una tabla.

        Args:
            table_name (str): Nombre de la tabla.

        Returns:
            pd.DataFrame: DataFrame con la información de las columnas.

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
            return pd.DataFrame(records, columns=columns)
        except psycopg.Error as e:
            logger.error(f"Error fetching table info for {table_name}: {e}")
            raise

    async def truncate_table(self, table_name: str) -> None:
        """
        Elimina todos los registros de una tabla sin eliminar la tabla.

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
            logger.error(f"Error truncating table {table_name}: {e}")
            raise

    ###### Métodos de Registros ######

    async def insert_records(self, table_name: str, record) -> Union[str, List[str]]:
        """
        Inserta uno o más registros en la tabla especificada de manera asíncrona.
        Este método permite la inserción de registros en una tabla de PostgreSQL utilizando una conexión asíncrona.

        Args:
            table_name (str): Nombre de la tabla en la que se insertará el registro.
            record (Union[dict, List[dict], str, pd.DataFrame]): Los datos a insertar. Puede ser:
                - Un diccionario individual
                - Una lista de diccionarios
                - Una ruta a un archivo CSV
                - Un DataFrame de Pandas

        Returns:
            Union[str, List[str]]: ID o lista de IDs de los registros insertados.

        Raises:
            psycopg.Error: Si ocurre un error durante la inserción.
            ValueError: Si el argumento record no es válido o está vacío.

        Examples:
            # Insertar un solo registro
            >>> id = await db.insert_records("cars", {"name": "Porsche"})

            # Insertar múltiples registros desde una lista
            >>> ids = await db.insert_records("cars", [
            ...     {"name": "Porsche"},
            ...     {"name": "Ferrari"},
            ...     {"name": "Audi"}
            ... ])

            # Insertar desde un DataFrame
            >>> ids = await db.insert_records("cars", df)

            # Insertar desde un CSV
            >>> ids = await db.insert_records("cars", "cars.csv")

        """
        if isinstance(record, str) and record.endswith('.csv') and os.path.isfile(record):
            record = pd.read_csv(record)

        if isinstance(record, pd.DataFrame):
            records = record.to_dict(orient='records')
        elif isinstance(record, list):
            if not record or not all(isinstance(item, dict) for item in record):
                raise ValueError("Si se proporciona una lista, todos los elementos deben ser diccionarios")
            records = record
        elif isinstance(record, dict):
            records = [record]
        else:
            raise ValueError("El argumento 'record' debe ser un diccionario, una lista de diccionarios, un archivo CSV o un DataFrame de Pandas")

        if not records:
            raise ValueError("No hay registros para insertar.")

        columns = list(records[0].keys())
        columns_str = ', '.join([self.sanitize_identifier(col) for col in columns])
        placeholders = ', '.join(['%s'] * len(columns))
        query = f"""
            INSERT INTO {self.sanitize_identifier(table_name)} ({columns_str}) 
            VALUES ({placeholders})
            RETURNING id
        """

        values = [[record[col] for col in columns] for record in records]

        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    if len(records) == 1:
                        cursor = await conn.execute(query, values[0])
                        inserted_id = (await cursor.fetchone())[0]
                        logger.info(f"1 record inserted successfully into {table_name} with id {inserted_id}.")
                        return str(inserted_id)
                    else:
                        inserted_ids = []
                        for value in values:
                            cursor = await conn.execute(query, value)
                            inserted_ids.append(str((await cursor.fetchone())[0]))
                        logger.info(f"{len(records)} records inserted successfully into {table_name}.")
                        return inserted_ids
        except psycopg.Error as e:
            logger.error(f"Error inserting records into {table_name}: {e}")
            raise


    async def fetch_records(self, 
                          table_name: str, 
                          columns: list = None,
                          conditions: dict = None, 
                          order_by: list = None, 
                          limit: int = None,
                          offset: int = None) -> pd.DataFrame:
        """
        Consulta registros con condiciones avanzadas.

        Args:
            table_name (str): Nombre de la tabla.
            columns (list, opcional): Lista de columnas a seleccionar.
            conditions (dict, opcional): Diccionario de condiciones.
            order_by (list, opcional): Lista de tuplas (columna, dirección).
            limit (int, opcional): Número máximo de registros.
            offset (int, opcional): Número de registros a saltar.

        Returns:
            pd.DataFrame: DataFrame con los resultados.

        Raises:
            psycopg.Error: Si ocurre un error durante la consulta.
        """
        query, params = self.build_query(
            table_name, columns, conditions=conditions, 
            order_by=order_by, limit=limit, offset=offset, 
            query_type="SELECT"
        )
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    cursor = await conn.execute(query, params)
                    records = await cursor.fetchall()
                    columns = [desc.name for desc in cursor.description] if records else []
            return pd.DataFrame(records, columns=columns)
        except psycopg.Error as e:
            logger.error(f"Error fetching records from {table_name}: {e}")
            raise

    async def update_record(self, 
                          table_name: str, 
                          record: dict, 
                          conditions: dict) -> None:
        """
        Actualiza registros que cumplan con las condiciones especificadas.

        Args:
            table_name (str): Nombre de la tabla.
            record (dict): Datos a actualizar.
            conditions (dict): Condiciones para identificar registros.

        Raises:
            psycopg.Error: Si ocurre un error durante la actualización.
        """
        try:
            self.validate_hashable(record)
            self.validate_hashable(conditions)
            conditions = self.sanitize_conditions(conditions)
            
            query, params = self.build_query(table_name, record, conditions, query_type="UPDATE")
            
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    await conn.execute(query, params)
            logger.info(f"Record(s) updated successfully in table {table_name}")
        except psycopg.Error as e:
            logger.error(f"Error updating record in {table_name}: {e}")
            raise

    async def delete_record(self, table_name: str, conditions: dict) -> None:
        """
        Elimina registros que cumplan con las condiciones especificadas.

        Args:
            table_name (str): Nombre de la tabla.
            conditions (dict): Condiciones para identificar registros.

        Raises:
            psycopg.Error: Si ocurre un error durante la eliminación.
        """
        query, params = self.build_query(table_name, conditions=conditions, query_type="DELETE")
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    await conn.execute(query, params)
        except psycopg.Error as e:
            logger.error(f"Error deleting record from {table_name}: {e}")
            raise

    async def execute_query(self, query: str, params: tuple = None) -> pd.DataFrame:
        """
        Ejecuta una consulta SQL personalizada.

        Args:
            query (str): Consulta SQL a ejecutar.
            params (tuple, opcional): Parámetros para la consulta.

        Returns:
            pd.DataFrame: DataFrame con los resultados.

        Raises:
            psycopg.Error: Si ocurre un error durante la ejecución.
        """
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    # Log de la query y parámetros para debugging
                    logger.debug(f"Executing query: {query} with params: {params}")
                    
                    cursor = await conn.execute(query, params)
                    
                    if cursor.description is not None:
                        records = await cursor.fetchall()
                        columns = [desc.name for desc in cursor.description]
                        return pd.DataFrame(records, columns=columns)
                    return pd.DataFrame()
        except psycopg.Error as e:
            logger.error(f"Error executing query: {e}")
            raise

        
    ##### Métodos Auxiliares #####

    def build_query(self, 
                    table_name: str, 
                    data: dict = None, 
                    conditions: dict = None,
                    columns: list = None,
                    order_by: list = None,
                    limit: int = None,
                    offset: int = None,
                    query_type: str = "SELECT") -> tuple:
        """
        Construye una consulta SQL basada en el tipo de operación.

        Args:
            table_name (str): Nombre de la tabla.
            data (dict, opcional): Datos para INSERT/UPDATE.
            conditions (dict, opcional): Condiciones WHERE.
            columns (list, opcional): Columnas para SELECT.
            order_by (list, opcional): Orden para SELECT.
            limit (int, opcional): Límite para SELECT.
            offset (int, opcional): Offset para SELECT.
            query_type (str): Tipo de consulta.

        Returns:
            tuple: (query, params)
        """
        table_name = self.sanitize_identifier(table_name)
        params = []

        if query_type == "SELECT":
            select_clause = "*" if not columns else ", ".join(map(self.sanitize_identifier, columns))
            query = f"SELECT {select_clause} FROM {table_name}"
            
            if conditions:
                where_clause, where_params = self._build_where_clause(conditions)
                query += f" WHERE {where_clause}"
                params.extend(where_params)

            if order_by:
                order_clause = ", ".join([f"{col} {direction}" for col, direction in order_by])
                query += f" ORDER BY {order_clause}"
            
            if limit:
                query += " LIMIT %s"
                params.append(limit)
            
            if offset:
                query += " OFFSET %s"
                params.append(offset)

        elif query_type == "INSERT":
            if not data:
                raise ValueError("INSERT queries require data.")
            columns = ', '.join(map(self.sanitize_identifier, data.keys()))
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            params.extend(data.values())

        elif query_type == "UPDATE":
            if not data:
                raise ValueError("UPDATE queries require data.")
            set_clause = ', '.join([f"{self.sanitize_identifier(k)} = %s" for k in data.keys()])
            query = f"UPDATE {table_name} SET {set_clause}"
            params.extend(data.values())
            
            if conditions:
                where_clause, where_params = self._build_where_clause(conditions)
                query += f" WHERE {where_clause}"
                params.extend(where_params)

        elif query_type == "DELETE":
            query = f"DELETE FROM {table_name}"
            if conditions:
                where_clause, where_params = self._build_where_clause(conditions)
                query += f" WHERE {where_clause}"
                params.extend(where_params)
            else:
                raise ValueError("DELETE queries require at least one condition.")

        return query, params

    def _build_where_clause(self, conditions: dict) -> tuple:
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
                where_clauses.append(f"{self.sanitize_identifier(column)} {operator} %s")
            else:
                where_clauses.append(f"{self.sanitize_identifier(key)} = %s")
            params.append(value)
        
        return " AND ".join(where_clauses), params

    def sanitize_identifier(self, identifier: str) -> str:
        """
        Sanitiza un identificador SQL.

        Args:
            identifier (str): Identificador a sanitizar.

        Returns:
            str: Identificador sanitizado.
        """
        return '"{}"'.format(identifier.replace('"', '""'))

    def sanitize_value(self, value):
        """
        Sanitiza un valor para inserción segura.

        Args:
            value: Valor a sanitizar.

        Returns:
            El valor sanitizado.
        """
        if isinstance(value, (list, dict)):
            return json.dumps(value)
        elif isinstance(value, (int, float, str, bool, type(None))):
            return value
        else:
            return str(value)

    async def create_vector_extension(self) -> None:
        """
        Habilita la extensión 'vector' en la base de datos.

        Raises:
            psycopg.Error: Si ocurre un error al habilitar la extensión.
        """
        query = "CREATE EXTENSION IF NOT EXISTS vector;"
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    await conn.execute(query)
            logger.info("Vector extension enabled successfully.")
        except psycopg.Error as e:
            logger.error(f"Error enabling vector extension: {e}")
            raise

    async def search_vectors(self, 
                            search_vector: List[float], 
                            agent_id: Optional[str] = None,
                            limit: int = 5) -> pd.DataFrame:
        """
        Realiza una búsqueda de vectores similares usando la función `search_vectors` en la base de datos.
        
        Args:
            search_vector (List[float]): Vector de búsqueda con dimensión 1536.
            limit (int): Número máximo de resultados a retornar. Por defecto es 5.
            agent_id (Optional[str]): ID opcional del agente para filtrar resultados.

        Returns:
            pd.DataFrame: DataFrame con los resultados de la búsqueda.
        """
        search_vector_str = f"ARRAY[{', '.join(map(str, search_vector))}]::vector"
        
        if agent_id:
            query = f"""
                SELECT * FROM search_vectors({search_vector_str}, {limit}, '{agent_id}'::uuid);
            """
        else:
            query = f"""
                SELECT * FROM search_vectors({search_vector_str}, {limit}, NULL);
            """
        
        try:
            async with async_db_connection(self.db_config) as conn:
                async with conn.transaction():
                    cursor = await conn.execute(query)
                    records = await cursor.fetchall()
                    columns = [desc.name for desc in cursor.description]
                    return pd.DataFrame(records, columns=columns)
        except psycopg.Error as e:
            logger.error(f"Error during vector search: {e}")
            raise

    async def search_records(self, 
                            table_name: str, 
                            search_term: str, 
                            search_column: str = 'name', 
                            additional_conditions: dict = None, 
                            **kwargs) -> pd.DataFrame:
        """
        Realiza una búsqueda de texto en una columna específica.

        Args:
            table_name (str): Nombre de la tabla en la que buscar.
            search_term (str): Término de búsqueda.
            search_column (str): Nombre de la columna en la que buscar (por defecto 'name').
            additional_conditions (dict): Condiciones adicionales para la búsqueda.
            **kwargs: Argumentos adicionales para pasar a fetch_records (e.g., limit, offset).

        Returns:
            pd.DataFrame: DataFrame con los resultados de la búsqueda.
        """
        conditions = {(search_column, 'ILIKE'): search_term}
        if additional_conditions:
            conditions.update(additional_conditions)

        return await self.fetch_records(table_name, conditions=conditions, **kwargs)
    
    async def upload_vectors_file(self,
                                filepath: str,
                                client_id: str,
                                file_name: str = None) -> dict:
        """
        Procesa un archivo CSV/Excel, genera vectores y los almacena en la base de datos.

        Args:
            filepath: Ruta al archivo (CSV o Excel)
            client_id: UUID del cliente
            file_name: Nombre personalizado para el archivo (opcional)

        Returns:
            dict: Información del procesamiento (file_id, total_vectors, file_name)

        Raises:
            ValueError: Si el cliente no existe o el formato de archivo no es soportado
            FileNotFoundError: Si el archivo no existe
        """
        try:
            # Validar archivo
            file_path = Path(filepath)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {filepath}")
            logger.info(f"Processing file: {filepath}")

            # Validar cliente
            client_exists = await self.fetch_records(
                "clients",
                conditions={"id": client_id}
            )
            if client_exists.empty:
                raise ValueError(f"Client with id {client_id} not found")
            logger.info(f"Client {client_id} validated successfully")

            # Leer archivo
            try:
                if file_path.suffix.lower() == '.csv':
                    df = pd.read_csv(filepath)
                elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                    df = pd.read_excel(filepath)
                else:
                    raise ValueError("Unsupported file format. Use CSV or Excel files.")
            except Exception as e:
                raise ValueError(f"Error reading file: {str(e)}")
            
            logger.info(f"File {filepath} read successfully with {len(df)} rows")

            final_file_name = file_name if file_name else file_path.stem

            # Insertar información del archivo
            file_info = {
                "file_name": final_file_name,
                "structure": str(tuple(df.columns)),
                "client_id": client_id
            }
            file_id = await self.insert_records("files", file_info)
            logger.info(f"File information inserted for {final_file_name}")
            logger.info(f"File ID: {file_id}")

            # Procesar documentos
            vectors_data = []
            for idx, row in df.iterrows():
                formatted_data = []
                for col in df.columns:
                    value = row[col]
                    if pd.isna(value):
                        continue
                    if isinstance(value, (float, np.floating)):
                        formatted_value = f"{value:.2f}"
                    else:
                        formatted_value = str(value)
                    formatted_data.append(f"{col}: {formatted_value}")

                vectors_data.append({
                    "row": idx + 1,
                    "file_id": file_id,
                    "data": '\n'.join(formatted_data),
                    "vectors_status_id": 1
                })
            
            try:
                vectors_df = pd.DataFrame(vectors_data)
                await self.insert_records("vectors", vectors_df)
                logger.info(f"Successfully inserted {len(vectors_df)} vectors")
            except Exception as e:
                logger.error(f"Error inserting vectors: {str(e)}")
                raise

            result = {
                "file_id": file_id,
                "total_vectors": len(vectors_data),
                "file_name": final_file_name,
                "status": "success"
            }
            
            logger.info(f"File processing completed successfully: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in upload_vectors_file: {str(e)}")
            raise

    async def delete_file(self, file_id: str) -> bool:
        """
        Realiza un soft delete de un archivo y todos sus registros relacionados.
        
        Args:
            file_id: UUID del archivo a eliminar

        Returns:
            bool: True si el archivo fue eliminado exitosamente, False si el archivo no existe 
                o ya estaba eliminado

        Raises:
            ValueError: Si el file_id no es válido
            psycopg.Error: Si ocurre un error en la base de datos
        """
        try:
            # Verificar que el archivo existe
            file_record = await self.fetch_records(
                "files",
                conditions={"id": file_id}
            )
            
            if file_record.empty:
                logger.warning(f"File with id {file_id} not found")
                return False

            # Verificar si ya está eliminado
            if pd.notnull(file_record['deleted_at'].iloc[0]):
                logger.warning(f"File with id {file_id} is already deleted")
                return False

            # Ejecutar la función de delete_file en la base de datos
            result = await self.execute_query(
                "SELECT delete_file(%s)",
                (file_id,)
            )
            
            # Obtener el resultado booleano
            success = result.iloc[0, 0] if not result.empty else False
            
            if type(success) == np.bool_:
                success = bool(success)

            if success:
                logger.info(f"File {file_id} and related records successfully deleted (soft delete)")
            else:
                logger.warning(f"File {file_id} could not be deleted")
                
            return success

        except ValueError as e:
            logger.error(f"Invalid file_id: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in delete_file: {str(e)}")
            raise