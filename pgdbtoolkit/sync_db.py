##### Clase Sincrónica para Operaciones en la Base de Datos #####

import psycopg
from pgvector.psycopg import register_vector
import pandas as pd
from contextlib import contextmanager
import os
from .log import log
from .base import BaseDbToolkit
import json
import numpy as np

##### Context Manager para Conexiones Sincrónicas #####

@contextmanager
def db_connection(db_config):
    """
    Context manager para manejar conexiones sincrónicas a la base de datos.
    
    Args:
        db_config (dict): Configuración de la base de datos.

    Yields:
        psycopg.Connection: Una conexión a la base de datos.
    """
    conn = psycopg.connect(**db_config)
    try:
        try:
            register_vector(conn)
        except psycopg.ProgrammingError as e:
            log.warning(f"Error al registrar el tipo vector: {e}. Continuando sin soporte de vectores.")
        yield conn
    finally:
        conn.close()

##### Clase para Gestión de Operaciones Sincrónicas #####

class PgDbToolkit(BaseDbToolkit):
    """
    Gestiona las operaciones sincrónicas de la base de datos PostgreSQL.
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

    def create_database(self, database_name: str) -> None:
        """
        Crea una nueva base de datos en el servidor PostgreSQL y actualiza la configuración.

        Args:
            database_name (str): Nombre de la base de datos que se desea crear.

        Raises:
            psycopg.Error: Si ocurre un error durante la creación de la base de datos.

        Example:
            >>> toolkit.create_database('mi_nueva_base_de_datos')
        """
        query = f"CREATE DATABASE {database_name}"
        try:
            with db_connection(self.db_config) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(query)
            
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
        
    def delete_database(self, database_name: str) -> None:
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
            # Conéctate a la base de datos 'postgres' para ejecutar las siguientes operaciones.
            with db_connection(self.db_config) as conn:
                conn.autocommit = True

                with conn.cursor() as cur:
                    # Finaliza todas las conexiones activas a la base de datos que quieres eliminar.
                    cur.execute(terminate_connections_query)

                with conn.cursor() as cur:
                    # Elimina la base de datos.
                    cur.execute(drop_database_query)

            log.info(f"Database {database_name} deleted successfully.")
        except psycopg.Error as e:
            log.error(f"Error deleting database {database_name}: {e}")
            raise

    def get_databases(self) -> pd.DataFrame:
        """
        Obtiene una lista de todas las bases de datos en el servidor PostgreSQL.

        Returns:
            pd.DataFrame: DataFrame con los nombres de las bases de datos.

        Raises:
            psycopg.Error: Si ocurre un error durante la consulta.
        """
        query = "SELECT datname FROM pg_database WHERE datistemplate = false"
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    records = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
            return pd.DataFrame(records, columns=columns)
        except psycopg.Error as e:
            log.error(f"Error fetching databases: {e}")
            raise

    ###### Métodos de Tablas ######

    def create_table(self, table_name: str, schema: dict) -> None:
        """
        Crea una nueva tabla en la base de datos con el esquema especificado.

        Args:
            table_name (str): Nombre de la tabla que se desea crear.
            schema (dict): Diccionario que define las columnas de la tabla y sus tipos de datos.

        Raises:
            psycopg.Error: Si ocurre un error durante la creación de la tabla.

        Example:
            >>> pg.create_table('orders', 
                                {"id": "SERIAL PRIMARY KEY", 
                                 "user_id": ("INTEGER", "REFERENCES users(id)")})
        """
        # Convertir el diccionario schema en una cadena SQL
        schema_str = ', '.join([f"{col} {dtype}" if isinstance(dtype, str) else f"{col} {dtype[0]} {dtype[1]}"
                                for col, dtype in schema.items()])
        
        query = f"CREATE TABLE {table_name} ({schema_str})"
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    conn.commit()
            log.info(f"Table {table_name} created successfully.")
        except psycopg.Error as e:
            log.error(f"Error creating table {table_name}: {e}")
            raise

    def delete_table(self, table_name: str) -> None:
        """
        Elimina una tabla de la base de datos.

        Este método ejecuta una consulta SQL para eliminar una tabla existente con el
        nombre especificado. Si la tabla no existe, la consulta no genera errores gracias
        a la cláusula `IF EXISTS`. En caso de que ocurra un error diferente, se captura y
        se registra en el log, elevando una excepción para su manejo.

        Args:
            table_name (str): Nombre de la tabla que se desea eliminar.

        Raises:
            psycopg.Error: Si ocurre un error durante la eliminación de la tabla.

        Example:
            >>> pg.delete_table('test_table')
        """
        query = f"DROP TABLE IF EXISTS {table_name}"
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    conn.commit()
            log.info(f"Table {table_name} deleted successfully.")
        except psycopg.Error as e:
            log.error(f"Error deleting table {table_name}: {e}")
            raise

    def alter_table(self,
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
        Realiza múltiples tipos de alteraciones en una tabla existente en la base de datos.

        Dependiendo de los parámetros proporcionados, este método puede agregar o eliminar columnas,
        renombrar columnas o tablas, cambiar tipos de datos, agregar o eliminar restricciones,
        y modificar propiedades de columnas como valores predeterminados o la nulabilidad.

        Todas las alteraciones proporcionadas se ejecutarán en una sola transacción.

        Args:
            table_name (str): Nombre de la tabla que se desea alterar.
            add_column (tuple, opcional): Tupla que contiene el nombre de la columna y el tipo de datos a agregar.
                                        Si es una clave foránea, debe ser una tupla en la forma 
                                        ('columna', ('tipo_de_dato', 'REFERENCES tabla(columna)')).
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

        Example:
            >>> pg.alter_table('usuarios', add_column=('email', 'VARCHAR(100)'), drop_column='user_id')
        """
        alterations = []

        if add_column:
            if isinstance(add_column[1], tuple):
                # Caso de clave foránea: ("columna", ("tipo_de_dato", "REFERENCES tabla(columna)"))
                alterations.append(f"ADD COLUMN {add_column[0]} {add_column[1][0]} {add_column[1][1]}")
            else:
                # Caso de columna normal: ("columna", "tipo_de_dato")
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
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    conn.commit()
            log.info(f"Table {table_name} altered successfully with alterations: {', '.join(alterations)}.")
        except psycopg.Error as e:
            log.error(f"Error altering table {table_name}: {e}")
            raise

    def get_tables(self) -> list:
        """
        Obtiene una lista con los nombres de todas las tablas en la base de datos.

        Esta función consulta las tablas en la base de datos actual y devuelve sus nombres
        en forma de lista.

        Returns:
            list: Una lista de cadenas que representan los nombres de las tablas en la base de datos.

        Raises:
            psycopg.Error: Si ocurre un error durante la consulta.

        Example:
            >>> tables = pg.get_tables()
            >>> print(tables)
            ['usuarios', 'orders', 'productos']
        """
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    tables = [row[0] for row in cur.fetchall()]
            log.info(f"Retrieved {len(tables)} tables from the database.")
            return tables
        except psycopg.Error as e:
            log.error(f"Error retrieving table names: {e}")
            raise


    def get_table_info(self, table_name: str) -> pd.DataFrame:
        """
        Obtiene la información de las columnas de una tabla, incluyendo nombre, tipo de datos y restricciones.

        Este método consulta las tablas del sistema en PostgreSQL para recuperar la información
        sobre las columnas de una tabla específica, incluyendo el nombre de la columna, el tipo de datos,
        si la columna puede contener valores nulos y el valor por defecto.

        Args:
            table_name (str): Nombre de la tabla de la cual se desea obtener la información.

        Returns:
            pd.DataFrame: DataFrame con la información de las columnas de la tabla.
                        Contiene las columnas: 'column_name', 'data_type', 'is_nullable', 'column_default'.

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
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (table_name,))
                    records = cur.fetchall()
                    columns = ['column_name', 'data_type', 'is_nullable', 'column_default']
                    df = pd.DataFrame(records, columns=columns)
                    return df
        except psycopg.Error as e:
            log.error(f"Error fetching table info for {table_name}: {e}")
            raise


    def truncate_table(self, table_name: str) -> None:
        """
        Elimina todos los registros de una tabla sin eliminar la tabla.

        Args:
            table_name (str): Nombre de la tabla que será truncada.

        Raises:
            psycopg.Error: Si ocurre un error durante la operación.
        """
        query = f"TRUNCATE TABLE {table_name}"
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    conn.commit()
        except psycopg.Error as e:
            log.error(f"Error truncating table {table_name}: {e}")
            raise

    ###### Métodos de Registros ######

    def insert_record(self, table_name: str, record) -> None:
        """
        Inserta uno o más registros en la tabla especificada de manera sincrónica.
        Soporta la inserción desde un diccionario, un archivo CSV o un DataFrame de Pandas.

        Args:
            table_name (str): Nombre de la tabla en la que se insertará el registro.
            record (dict, str o pd.DataFrame): Diccionario, archivo CSV o DataFrame de Pandas que contiene los datos.

        Raises:
            psycopg.Error: Si ocurre un error durante la inserción.
        """
        # Si el record es un archivo CSV
        if isinstance(record, str) and record.endswith('.csv') and os.path.isfile(record):
            # Cargar el archivo CSV en un DataFrame
            record = pd.read_csv(record)

        # Si el record es un DataFrame de Pandas
        if isinstance(record, pd.DataFrame):
            # Convertir el DataFrame a una lista de diccionarios
            records = record.to_dict(orient='records')
        # Si el record es un diccionario, lo convertimos en una lista con un solo elemento
        elif isinstance(record, dict):
            records = [record]
        else:
            raise ValueError("El argumento 'record' debe ser un diccionario, un archivo CSV o un DataFrame de Pandas.")

        # Obtener columnas de los registros
        if not records:
            raise ValueError("No records to insert.")
        columns = records[0].keys()
        columns_str = ', '.join([self.sanitize_identifier(col) for col in columns])
        placeholders = ', '.join(['%s'] * len(columns))

        # Crear la consulta SQL para la inserción
        query = f"INSERT INTO {self.sanitize_identifier(table_name)} ({columns_str}) VALUES ({placeholders})"
        
        # Preparar los valores de los registros
        values = [tuple(rec[col] for col in columns) for rec in records]

        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    # Insertar múltiples registros de una vez
                    cur.executemany(query, values)
                    conn.commit()
                log.info(f"{len(records)} records inserted successfully into {table_name}.")
        except psycopg.Error as e:
            log.error(f"Error inserting records into {table_name}: {e}")
            raise

    def fetch_records(self, 
                      table_name: str, 
                      columns: list = None,
                      conditions: dict = None, 
                      order_by: list = None, 
                      limit: int = None,
                      offset: int = None) -> pd.DataFrame:
        """
        Consulta registros de una tabla con condiciones avanzadas, permite seleccionar columnas específicas,
        ordenar por múltiples columnas, limitar resultados y aplicar un offset.

        Args:
            table_name (str): Nombre de la tabla de la cual se consultarán los registros.
            columns (list, opcional): Lista de columnas a seleccionar. Por defecto selecciona todas (*).
            conditions (dict, opcional): Diccionario de condiciones para filtrar los registros.
            order_by (list, opcional): Lista de tuplas (columna, dirección) para ordenar los resultados.
            limit (int, opcional): Número máximo de registros a devolver.
            offset (int, opcional): Número de registros a saltar antes de comenzar a devolver resultados.

        Returns:
            pd.DataFrame: DataFrame con los registros consultados.

        Raises:
            psycopg.Error: Si ocurre un error durante la consulta.
        """
        query, params = self.build_query(
            table_name, columns, conditions=conditions, 
            order_by=order_by, limit=limit, offset=offset, 
            query_type="SELECT"
        )
        return self.execute_query(query, params)

    def update_record(self, 
                      table_name: str, 
                      record: dict, 
                      conditions: dict,
                      ) -> None:
        """
        Actualiza un registro en la tabla especificada basado en las condiciones.

        Args:
            table_name (str): Nombre de la tabla en la que se actualizará el registro.
            record (dict): Diccionario con los datos del registro a actualizar.
            conditions (dict): Diccionario de condiciones para identificar el registro a actualizar.

        Raises:
            ValueError: Si se encuentran tipos de datos inválidos en record o conditions.
            psycopg.Error: Si ocurre un error durante la actualización en la base de datos.
        """
        try:
            self.validate_hashable(record)
            self.validate_hashable(conditions)
            conditions = self.sanitize_conditions(conditions)
            
            query, params = self.build_query(table_name, record, conditions, query_type="UPDATE")
            
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    conn.commit()
            log.info(f"Registro actualizado exitosamente en la tabla {table_name}")
        except ValueError as e:
            log.error(f"Error de validación al actualizar registro en {table_name}: {e}")
            raise
        except psycopg.Error as e:
            log.error(f"Error de base de datos al actualizar registro en {table_name}: {e}")
            raise
        except Exception as e:
            log.error(f"Error inesperado al actualizar registro en {table_name}: {e}")
            raise


    def delete_record(self, table_name: str, conditions: dict) -> None:
        """
        Elimina un registro de la tabla especificada basado en las condiciones.

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

    def execute_query(self, query: str, params: tuple = None) -> pd.DataFrame:
        """
        Ejecuta un query SQL personalizado de manera sincrónica.

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
                    if cur.description:  # Solo intenta fetchall si hay resultados
                        records = cur.fetchall()
                        columns = [desc[0] for desc in cur.description]
                        return pd.DataFrame(records, columns=columns)
                    else:
                        conn.commit()  # Para operaciones de modificación
                        return pd.DataFrame()  # Retornar un DataFrame vacío para mantener compatibilidad
        except psycopg.Error as e:
            log.error(f"Error executing query: {e}")
            raise

    ##### Método Auxiliar para Construcción de Queries #####

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
        Construye un query SQL avanzado basado en el tipo de operación.

        Args:
            table_name (str): Nombre de la tabla.
            columns (list, opcional): Lista de columnas a seleccionar (solo para SELECT).
            data (dict, opcional): Diccionario con los datos del registro para INSERT y UPDATE.
            conditions (dict, opcional): Diccionario de condiciones avanzadas para filtrar los registros.
            order_by (list, opcional): Lista de tuplas (columna, dirección) para ordenar los resultados.
            limit (int, opcional): Número máximo de registros a devolver.
            query_type (str, opcional): Tipo de query a construir ('SELECT', 'INSERT', 'UPDATE', 'DELETE').

        Returns:
            tuple: (query_string, params)
        """
        table_name = self.sanitize_identifier(table_name)
        params = []

        if query_type == "SELECT":
            if columns and len(columns) == 1 and columns[0].upper().startswith("COUNT("):
                # Manejo especial para consultas de COUNT
                select_clause = columns[0]
            else:
                select_clause = "*" if not columns else ", ".join(map(self.sanitize_identifier, columns))
            
            query = f"SELECT {select_clause} FROM {table_name}"
            
            if conditions:
                where_clauses = []
                for key, value in conditions.items():
                    if isinstance(key, tuple):
                        column, operator = key
                        if operator.upper() == 'ILIKE':
                            # Añadir comodines automáticamente para ILIKE
                            value = f"%{value}%" if '%' not in value else value
                        where_clauses.append(f"{self.sanitize_identifier(column)} {operator} %s")
                    else:
                        where_clauses.append(f"{self.sanitize_identifier(key)} = %s")
                    params.append(value)
                
                query += " WHERE " + " AND ".join(where_clauses)

            
            if order_by:
                order_clause = ", ".join([f"{self.sanitize_identifier(col)} {direction}" for col, direction in order_by])
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

        else:
            raise ValueError(f"Query type '{query_type}' not recognized.")

        return query, params

    def _build_where_clause(self, conditions: dict) -> tuple:
        """
        Construye la cláusula WHERE basada en condiciones avanzadas.

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
        Sanitiza un identificador SQL para prevenir inyección SQL.

        Args:
            identifier (str): El identificador a sanitizar.

        Returns:
            str: El identificador sanitizado.
        """
        return '"{}"'.format(identifier.replace('"', '""'))

    def sanitize_value(self, value):
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
        
    def create_vector_extension(self) -> None:
        """
        Habilita la extensión 'vector' en la base de datos actual.

        Este método ejecuta 'CREATE EXTENSION vector;' para permitir el uso
        de tipos y funciones de vectores proporcionados por la extensión pgvector.

        Raises:
            psycopg.Error: Si ocurre un error al habilitar la extensión.
        """
        query = "CREATE EXTENSION IF NOT EXISTS vector;"
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    conn.commit()
            log.info("Extensión 'vector' habilitada exitosamente en la base de datos.")
        except psycopg.Error as e:
            log.error(f"Error al habilitar la extensión 'vector': {e}")
            raise

    def search_vectors(self,
                    vector: list,
                    table_name: str = 'vectors',
                    limit: int = 5,
                    vector_column: str = 'embedding',
                    agent_id: str = None,
                    agent_column: str = 'agent_id',
                    vector_status: int = None,
                    vector_status_column: str = 'vector_status') -> pd.DataFrame:
        """
        Realiza una búsqueda de vectores en la base de datos utilizando similitud coseno.

        Args:
            vector (np.ndarray): El vector de consulta.
            table_name (str, opcional): Nombre de la tabla donde se encuentran los vectores. Por defecto es 'vectors'.
            limit (int, opcional): Número máximo de resultados a retornar. Por defecto es 5.
            vector_column (str, opcional): Nombre de la columna que almacena los vectores. Por defecto es 'embedding'.
            agent_id (str, opcional): ID del agente cuyos vectores serán buscados.
            agent_column (str, opcional): Nombre de la columna que almacena el ID del agente. Por defecto es 'agent_id'.
            vector_status (int, opcional): Estado del vector para filtrar los resultados.
            vector_status_column (str, opcional): Nombre de la columna que almacena el estado del vector. Por defecto es 'vector_status'.

        Returns:
            pd.DataFrame: DataFrame con los registros más similares.

        Raises:
            psycopg.Error: Si ocurre un error durante la consulta.
        """
        vector = np.array(vector)
        
        # Construir la cláusula WHERE dinámica
        where_conditions = []
        params = []

        if agent_id is not None:
            where_conditions.append(f"{self.sanitize_identifier(agent_column)} = %s")
            params.append(agent_id)

        if vector_status is not None:
            where_conditions.append(f"{self.sanitize_identifier(vector_status_column)} = %s")
            params.append(vector_status)

        # Unir las condiciones con 'AND' si hay más de una
        where_clause = ''
        if where_conditions:
            where_clause = 'WHERE ' + ' AND '.join(where_conditions)

        # Construir la consulta SQL
        query = f"""
        SELECT *, 1 - ({self.sanitize_identifier(vector_column)} <=> %s) AS cosine_similarity
        FROM {self.sanitize_identifier(table_name)}
        {where_clause}
        ORDER BY {self.sanitize_identifier(vector_column)} <=> %s
        LIMIT %s;
        """
        # Agregar el vector y el límite a los parámetros
        params = [vector] + params + [vector, limit]

        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                    cur.execute(query, params)
                    records = cur.fetchall()
            return pd.DataFrame(records)
        except psycopg.Error as e:
            log.error(f"Error during vector search: {e}")
            raise

    def search_records(self, table_name: str, search_term: str, search_column: str = 'name', 
                       additional_conditions: dict = None, **kwargs) -> pd.DataFrame:
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

        return self.fetch_records(table_name, conditions=conditions, **kwargs)
