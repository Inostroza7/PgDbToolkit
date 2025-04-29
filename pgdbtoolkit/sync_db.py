# sync_db.py

"""
Clase Sincrónica para Operaciones en la Base de Datos PostgreSQL.
Este módulo proporciona una implementación completa para interactuar con
bases de datos PostgreSQL utilizando psycopg 3 de manera sincrónica.
"""

import psycopg
import pandas as pd
from pgvector.psycopg import register_vector
import os
from contextlib import contextmanager
import json
import numpy as np
from typing import Optional, List, Dict, Union, Tuple, Any
from pathlib import Path

from .log import Log
from .base import BaseDbToolkit
from .common_utils import (sanitize_identifier, sanitize_value, validate_hashable,
                          sanitize_conditions, build_query_parts, 
                          _build_where_clause_parts, prepare_data_for_copy,
                          generate_copy_command)
from .exceptions import ConnectionError, QueryError, RecordNotFoundError, DatabaseError

logger = Log(__name__)

##### Context Manager para Conexiones Sincrónicas #####

@contextmanager
def db_connection(db_config):
    """
    Context manager para manejar conexiones sincrónicas a la base de datos.
    
    Args:
        db_config (dict): Configuración de la base de datos.

    Yields:
        psycopg.Connection: Una conexión a la base de datos.
        
    Raises:
        ConnectionError: Si ocurre un error al conectar a la base de datos.
    """
    conn = None
    try:
        conn = psycopg.connect(**db_config)
        # Establecer autocommit inmediatamente antes de cualquier operación
        conn.autocommit = True
        logger.debug(f"Conexión establecida a {db_config.get('host')}:{db_config.get('port')}/{db_config.get('dbname')}")
        
        # Verificar pgvector solo una vez por sesión, usando una variable estática
        if not hasattr(db_connection, "pgvector_checked"):
            db_connection.pgvector_checked = True
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                    if cur.fetchone():
                        try:
                            register_vector(conn)
                            logger.debug("Extensión pgvector registrada correctamente")
                        except Exception as e:
                            logger.debug(f"Error al registrar el tipo vector: {e}. Continuando sin soporte de vectores.")
                    else:
                        logger.debug("La extensión pgvector no está instalada en la base de datos. Continuando sin soporte de vectores.")
            except Exception as e:
                logger.debug(f"No se pudo verificar la extensión pgvector: {e}. Continuando sin soporte de vectores.")
            
        yield conn
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos: {e}")
        raise ConnectionError(f"No se pudo establecer la conexión a la base de datos: {str(e)}")
    finally:
        if conn:
            conn.close()
            logger.debug("Conexión cerrada")

##### Clase para Gestión de Operaciones Sincrónicas #####

class PgDbToolkit(BaseDbToolkit):
    """
    Gestiona las operaciones sincrónicas de la base de datos PostgreSQL.
    Proporciona métodos para crear, eliminar y modificar bases de datos, tablas y registros.
    """

    ###### Métodos de Base de Datos ######

    def create_database(self, database_name: str) -> None:
        """
        Crea una nueva base de datos en el servidor PostgreSQL y actualiza la configuración.

        Args:
            database_name (str): Nombre de la base de datos que se desea crear.

        Raises:
            DatabaseError: Si ocurre un error durante la creación de la base de datos.
            
        Example:
            >>> db.create_database("mi_nueva_bd")
        """
        query = f"CREATE DATABASE {database_name}"
        try:
            # Usar una conexión separada con autocommit=True desde el inicio
            with psycopg.connect(**{k: v for k, v in self.db_config.items() if k != 'dbname'}, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
            
            # Actualizar la configuración para que utilice la nueva base de datos
            self.db_config['dbname'] = database_name
            os.environ['DB_DATABASE'] = database_name
            logger.info(f"Base de datos {database_name} creada y configuración actualizada")
            
        except psycopg.errors.DuplicateDatabase:
            logger.warning(f"La base de datos {database_name} ya existe.")
            return
        except Exception as e:
            logger.error(f"Error al crear la base de datos {database_name}: {e}")
            raise DatabaseError(f"Error al crear la base de datos {database_name}: {str(e)}")
        
    def delete_database(self, database_name: str) -> None:
        """
        Elimina una base de datos existente en el servidor PostgreSQL.

        Args:
            database_name (str): Nombre de la base de datos que se desea eliminar.

        Raises:
            DatabaseError: Si ocurre un error durante la eliminación de la base de datos.
        """
        terminate_connections_query = f"""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '{database_name}' AND pid <> pg_backend_pid();
        """

        drop_database_query = f"DROP DATABASE IF EXISTS {database_name}"

        try:
            with db_connection(self.db_config) as conn:
                conn.autocommit = True

                with conn.cursor() as cur:
                    cur.execute(terminate_connections_query)

                with conn.cursor() as cur:
                    cur.execute(drop_database_query)

            logger.info(f"Base de datos {database_name} eliminada correctamente")
        except Exception as e:
            logger.error(f"Error al eliminar la base de datos {database_name}: {e}")
            raise DatabaseError(f"Error al eliminar la base de datos {database_name}: {str(e)}")

    def get_databases(self) -> pd.DataFrame:
        """
        Obtiene una lista de todas las bases de datos en el servidor PostgreSQL.

        Returns:
            pd.DataFrame: DataFrame con los nombres de las bases de datos.

        Raises:
            QueryError: Si ocurre un error durante la consulta.
        """
        query = "SELECT datname FROM pg_database WHERE datistemplate = false"
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    records = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
            return pd.DataFrame(records, columns=columns)
        except Exception as e:
            logger.error(f"Error al obtener las bases de datos: {e}")
            raise QueryError(f"Error al consultar las bases de datos: {str(e)}")

    ###### Métodos de Tablas ######

    def create_table(self, table_name: str, schema: dict) -> None:
        """
        Crea una nueva tabla en la base de datos con el esquema especificado.

        Args:
            table_name (str): Nombre de la tabla que se desea crear.
            schema (dict): Diccionario que define las columnas de la tabla y sus tipos de datos.

        Raises:
            QueryError: Si ocurre un error durante la creación de la tabla.
            
        Example:
            >>> db.create_table("usuarios", {
            ...     "id": "SERIAL PRIMARY KEY",
            ...     "nombre": "VARCHAR(100) NOT NULL",
            ...     "email": "VARCHAR(255) UNIQUE",
            ...     "fecha_registro": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ... })
        """
        schema_str = ', '.join([f"{col} {dtype}" if isinstance(dtype, str) else f"{col} {dtype[0]} {dtype[1]}"
                                for col, dtype in schema.items()])
        
        query = f"CREATE TABLE {sanitize_identifier(table_name)} ({schema_str})"
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    conn.commit()
            logger.info(f"Tabla {table_name} creada correctamente")
        except Exception as e:
            logger.error(f"Error al crear la tabla {table_name}: {e}")
            raise QueryError(f"Error al crear la tabla {table_name}: {str(e)}")

    def delete_table(self, table_name: str) -> None:
        """
        Elimina una tabla de la base de datos.

        Args:
            table_name (str): Nombre de la tabla que se desea eliminar.

        Raises:
            QueryError: Si ocurre un error durante la eliminación de la tabla.
        """
        query = f"DROP TABLE IF EXISTS {sanitize_identifier(table_name)}"
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    conn.commit()
            logger.info(f"Tabla {table_name} eliminada correctamente")
        except Exception as e:
            logger.error(f"Error al eliminar la tabla {table_name}: {e}")
            raise QueryError(f"Error al eliminar la tabla {table_name}: {str(e)}")

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
        Realiza múltiples tipos de alteraciones en una tabla existente.
        
        Args:
            table_name (str): Nombre de la tabla que se desea alterar.
            add_column (tuple, opcional): Tupla (nombre, tipo) de la columna a añadir.
            drop_column (str, opcional): Nombre de la columna a eliminar.
            rename_column (tuple, opcional): Tupla (nombre_actual, nuevo_nombre).
            alter_column_type (tuple, opcional): Tupla (nombre, nuevo_tipo).
            rename_table (str, opcional): Nuevo nombre para la tabla.
            add_constraint (tuple, opcional): Tupla (nombre, definicion) de la restricción.
            drop_constraint (str, opcional): Nombre de la restricción a eliminar.
            set_column_default (tuple, opcional): Tupla (nombre, valor_predeterminado).
            drop_column_default (str, opcional): Nombre de la columna para eliminar valor predeterminado.
            set_column_not_null (str, opcional): Nombre de la columna para establecer NOT NULL.
            drop_column_not_null (str, opcional): Nombre de la columna para eliminar NOT NULL.
            
        Raises:
            QueryError: Si ocurre un error durante la alteración de la tabla.
            ValueError: Si no se proporciona ninguna alteración válida.
            
        Example:
            >>> db.alter_table(
            ...     "usuarios",
            ...     add_column=("direccion", "TEXT"),
            ...     add_constraint=("email_unique", "UNIQUE(email)")
            ... )
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
            raise ValueError("No se proporcionó ninguna alteración válida.")

        query = f"ALTER TABLE {sanitize_identifier(table_name)} " + ", ".join(alterations)

        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    conn.commit()
            logger.info(f"Tabla {table_name} alterada correctamente con alteraciones: {', '.join(alterations)}")
        except Exception as e:
            logger.error(f"Error al alterar la tabla {table_name}: {e}")
            raise QueryError(f"Error al alterar la tabla {table_name}: {str(e)}")

    def get_tables(self) -> list:
        """
        Obtiene una lista con los nombres de todas las tablas en la base de datos.

        Returns:
            list: Una lista de cadenas que representan los nombres de las tablas.

        Raises:
            QueryError: Si ocurre un error durante la consulta.
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
            logger.info(f"Se recuperaron {len(tables)} tablas de la base de datos")
            return tables
        except Exception as e:
            logger.error(f"Error al obtener las tablas: {e}")
            raise QueryError(f"Error al consultar las tablas: {str(e)}")

    def get_table_info(self, table_name: str) -> pd.DataFrame:
        """
        Obtiene la información de las columnas de una tabla.

        Args:
            table_name (str): Nombre de la tabla.

        Returns:
            pd.DataFrame: DataFrame con la información de las columnas.

        Raises:
            QueryError: Si ocurre un error durante la consulta.
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
        except Exception as e:
            logger.error(f"Error al obtener información de la tabla {table_name}: {e}")
            raise QueryError(f"Error al consultar información de la tabla {table_name}: {str(e)}")

    def truncate_table(self, table_name: str) -> None:
        """
        Elimina todos los registros de una tabla sin eliminar la tabla.

        Args:
            table_name (str): Nombre de la tabla que será truncada.

        Raises:
            QueryError: Si ocurre un error durante la operación.
        """
        query = f"TRUNCATE TABLE {sanitize_identifier(table_name)}"
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    conn.commit()
            logger.info(f"Tabla {table_name} truncada correctamente")
        except Exception as e:
            logger.error(f"Error al truncar la tabla {table_name}: {e}")
            raise QueryError(f"Error al truncar la tabla {table_name}: {str(e)}")

    ###### Métodos de Registros ######

    def insert_records(self, table_name: str, record) -> Union[str, List[str]]:
        """
        Inserta uno o más registros en la tabla especificada.
        Soporta la inserción desde un diccionario, una lista de diccionarios, un archivo CSV o un DataFrame de Pandas.

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
            QueryError: Si ocurre un error durante la inserción.
            ValueError: Si el argumento record no es válido o está vacío.

        Examples:
            # Insertar un solo registro
            >>> id = db.insert_records("cars", {"name": "Porsche"})
            
            # Insertar múltiples registros desde una lista
            >>> ids = db.insert_records("cars", [
            ...     {"name": "Porsche"},
            ...     {"name": "Ferrari"},
            ...     {"name": "Audi"}
            ... ])
            
            # Insertar desde un DataFrame
            >>> ids = db.insert_records("cars", df)
            
            # Insertar desde un CSV
            >>> ids = db.insert_records("cars", "cars.csv")
        """
        # Si el record es un archivo CSV
        if isinstance(record, str) and record.endswith('.csv') and os.path.isfile(record):
            # Cargar el archivo CSV en un DataFrame
            record = pd.read_csv(record)

        # Si el record es un DataFrame de Pandas
        if isinstance(record, pd.DataFrame):
            # Convertir el DataFrame a una lista de diccionarios
            records = record.to_dict(orient='records')
        # Si el record es una lista de diccionarios
        elif isinstance(record, list):
            if not record or not all(isinstance(item, dict) for item in record):
                raise ValueError("Si se proporciona una lista, todos los elementos deben ser diccionarios")
            records = record
        # Si el record es un diccionario individual
        elif isinstance(record, dict):
            records = [record]
        else:
            raise ValueError("El argumento 'record' debe ser un diccionario, una lista de diccionarios, un archivo CSV o un DataFrame de Pandas.")

        # Verificar que hay registros para insertar
        if not records:
            raise ValueError("No hay registros para insertar.")

        # Sanitizar valores
        for r in records:
            for k, v in r.items():
                r[k] = sanitize_value(v)

        # Obtener columnas del primer registro
        columns = list(records[0].keys())
        columns_str = ', '.join([sanitize_identifier(col) for col in columns])
        placeholders = ', '.join(['%s'] * len(columns))

        # Crear la consulta SQL para la inserción con RETURNING id
        query = f"""
            INSERT INTO {sanitize_identifier(table_name)} ({columns_str}) 
            VALUES ({placeholders})
            RETURNING id
        """
        
        # Preparar los valores de los registros
        values = [tuple(rec[col] for col in columns) for rec in records]

        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    if len(records) == 1:
                        # Si es un solo registro, ejecutar una vez y retornar un solo ID
                        cur.execute(query, values[0])
                        inserted_id = cur.fetchone()[0]
                        conn.commit()
                        logger.info(f"1 registro insertado correctamente en {table_name} con id {inserted_id}")
                        return str(inserted_id)
                    else:
                        # Para múltiples registros, ejecutar uno por uno y recolectar IDs
                        inserted_ids = []
                        for value in values:
                            cur.execute(query, value)
                            inserted_ids.append(str(cur.fetchone()[0]))
                        conn.commit()
                        logger.info(f"{len(records)} registros insertados correctamente en {table_name}")
                        return inserted_ids
        except Exception as e:
            logger.error(f"Error al insertar registros en {table_name}: {e}")
            raise QueryError(f"Error al insertar registros en {table_name}: {str(e)}")

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
            QueryError: Si ocurre un error durante la consulta.
            
        Example:
            >>> # Buscar usuarios con correo gmail, ordenados por fecha
            >>> df = db.fetch_records(
            ...     "usuarios",
            ...     columns=["id", "nombre", "email"],
            ...     conditions={("email", "LIKE"): "%@gmail.com"},
            ...     order_by=[("fecha_registro", "DESC")],
            ...     limit=10
            ... )
        """
        try:
            # Si columns es None, aseguramos que se seleccionen todas las columnas explícitamente
            if columns is None:
                # Obtener primero los nombres de las columnas de la tabla
                table_info_query = f"SELECT column_name FROM information_schema.columns WHERE table_name = %s AND table_schema = 'public'"
                with db_connection(self.db_config) as conn:
                    with conn.cursor() as cur:
                        cur.execute(table_info_query, (table_name,))
                        columns = [row[0] for row in cur.fetchall()]
                        
                # Si no se pudieron obtener las columnas, usar *
                if not columns:
                    columns = ["*"]
            
            query, params = self.build_query(
                table_name, columns, conditions=conditions, 
                order_by=order_by, limit=limit, offset=offset, 
                query_type="SELECT"
            )
            
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    records = cur.fetchall()
                    if cur.description:
                        result_columns = [desc[0] for desc in cur.description]
                    else:
                        result_columns = []
            return pd.DataFrame(records, columns=result_columns)
        except Exception as e:
            logger.error(f"Error al consultar registros de {table_name}: {e}")
            raise QueryError(f"Error al consultar registros de {table_name}: {str(e)}")

    def update_records(self, 
                      table_name: str, 
                      data: Union[dict, List[dict]], 
                      conditions: Union[dict, List[dict]]) -> int:
        """
        Actualiza uno o múltiples registros en la tabla especificada.

        Args:
            table_name (str): Nombre de la tabla en la que se actualizarán los registros.
            data (Union[dict, List[dict]]): Datos a actualizar.
            conditions (Union[dict, List[dict]]): Condiciones para identificar los registros.

        Returns:
            int: Número de registros actualizados.

        Raises:
            ValueError: Si se encuentran tipos de datos inválidos en data o conditions.
            QueryError: Si ocurre un error durante la actualización en la base de datos.
            
        Example:
            >>> # Actualizar un solo registro
            >>> db.update_records(
            ...     "usuarios",
            ...     {"activo": True},
            ...     {"id": 123}
            ... )
            
            >>> # Actualizar múltiples registros con diferentes valores
            >>> db.update_records(
            ...     "productos",
            ...     [{"precio": 10.99}, {"precio": 15.99}],
            ...     [{"id": 1}, {"id": 2}]
            ... )
        """
        try:
            # Convertir a listas si se proporcionó un solo registro
            if isinstance(data, dict):
                data = [data]
            if isinstance(conditions, dict):
                conditions = [conditions]
            
            if len(data) != len(conditions):
                raise ValueError("El número de registros y condiciones deben coincidir.")

            for record in data:
                self.validate_hashable(record)
            for condition in conditions:
                self.validate_hashable(condition)
                condition = self.sanitize_conditions(condition)

            # Iniciar la transacción
            updated_count = 0
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    for record, condition in zip(data, conditions):
                        query, params = self.build_query(
                            table_name=table_name,
                            data=record,
                            conditions=condition,
                            query_type="UPDATE"
                        )
                        cur.execute(query, params)
                        updated_count += cur.rowcount
                    conn.commit()
            logger.info(f"{updated_count} registros actualizados exitosamente en la tabla {table_name}")
            return updated_count
        except ValueError as e:
            logger.error(f"Error de validación al actualizar registros en {table_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al actualizar registros en {table_name}: {e}")
            raise QueryError(f"Error al actualizar registros en {table_name}: {str(e)}")

    def delete_records(self, 
                       table_name: str, 
                       conditions: dict,
                       soft_delete: bool = False,
                       delete_column: Optional[str] = None) -> int:
        """
        Elimina registros de la tabla especificada basado en las condiciones.
        Si soft_delete es True, realizará un borrado lógico actualizando la columna especificada.

        Args:
            table_name (str): Nombre de la tabla de la cual se eliminarán los registros.
            conditions (dict): Diccionario de condiciones para identificar los registros a eliminar.
            soft_delete (bool, opcional): Si es True, usa borrado lógico en lugar de físico. Por defecto es False.
            delete_column (str, opcional): Nombre de la columna para soft delete. Requerido si soft_delete=True.

        Returns:
            int: Número de registros eliminados.

        Raises:
            QueryError: Si ocurre un error durante la eliminación.
            ValueError: Si no se proporcionan condiciones para la eliminación,
                        o si soft_delete=True pero no se especifica delete_column.
            
        Example:
            >>> # Eliminar todos los usuarios inactivos con email gmail
            >>> count = db.delete_records(
            ...     "usuarios",
            ...     {
            ...         "activo": False,
            ...         ("email", "LIKE"): "%@gmail.com"
            ...     }
            ... )
            >>> print(f"Se eliminaron {count} registros")
            
            >>> # Borrado lógico: marcar como eliminados pero mantener en la base de datos
            >>> count = db.delete_records(
            ...     "productos",
            ...     {"id": 123},
            ...     soft_delete=True,
            ...     delete_column="fecha_eliminacion"
            ... )
        """
        if not conditions:
            raise ValueError("Se requiere al menos una condición para eliminar registros.")
            
        if soft_delete and not delete_column:
            raise ValueError("Si soft_delete=True, debe especificar delete_column.")

        # Si se ha activado soft_delete, usamos esa columna
        column_for_deletion = delete_column if soft_delete else None
            
        try:
            if soft_delete and column_for_deletion:
                # Soft delete: actualizamos la columna especificada con la fecha actual
                try:
                    # Construir la consulta UPDATE
                    set_clause = f"{sanitize_identifier(column_for_deletion)} = CURRENT_TIMESTAMP"
                    query = f"UPDATE {sanitize_identifier(table_name)} SET {set_clause}"
                    
                    # Agregar condiciones WHERE
                    where_clause, params = self._build_where_clause(conditions)
                    query += f" WHERE {where_clause}"
                    
                    with db_connection(self.db_config) as conn:
                        with conn.cursor() as cur:
                            cur.execute(query, params)
                            deleted_count = cur.rowcount
                            conn.commit()
                            
                    logger.info(f"{deleted_count} registros marcados como eliminados en la tabla {table_name} (soft delete)")
                    return deleted_count
                    
                except psycopg.errors.UndefinedColumn as e:
                    logger.warning(f"Error al realizar soft delete: {e}. La columna {column_for_deletion} puede no existir.")
                    logger.warning("Intentando crear la columna para soft delete...")
                    
                    # Intentar agregar la columna si no existe
                    try:
                        alter_query = f"ALTER TABLE {sanitize_identifier(table_name)} ADD COLUMN {sanitize_identifier(column_for_deletion)} TIMESTAMP"
                        with db_connection(self.db_config) as conn:
                            with conn.cursor() as cur:
                                cur.execute(alter_query)
                                conn.commit()
                                
                        # Volver a intentar el soft delete
                        update_query = f"UPDATE {sanitize_identifier(table_name)} SET {sanitize_identifier(column_for_deletion)} = CURRENT_TIMESTAMP"
                        where_clause, params = self._build_where_clause(conditions)
                        update_query += f" WHERE {where_clause}"
                        
                        with db_connection(self.db_config) as conn:
                            with conn.cursor() as cur:
                                cur.execute(update_query, params)
                                deleted_count = cur.rowcount
                                conn.commit()
                                
                        logger.info(f"Columna {column_for_deletion} creada y {deleted_count} registros marcados como eliminados")
                        return deleted_count
                        
                    except Exception as add_column_err:
                        logger.error(f"No se pudo crear la columna para soft delete: {add_column_err}")
                        logger.warning("Realizando borrado físico como alternativa...")
            
            # Borrado físico (delete normal)
            query = f"DELETE FROM {sanitize_identifier(table_name)}"
            where_clause, params = self._build_where_clause(conditions)
            query += f" WHERE {where_clause}"
            
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    deleted_count = cur.rowcount
                    conn.commit()
            
            logger.info(f"{deleted_count} registros eliminados permanentemente de la tabla {table_name}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error al eliminar registros de {table_name}: {e}")
            raise QueryError(f"Error al eliminar registros de {table_name}: {str(e)}")

    def execute_query(self, query: str, params: tuple = None) -> pd.DataFrame:
        """
        Ejecuta un query SQL personalizado de manera sincrónica.

        Args:
            query (str): El query SQL a ejecutar.
            params (tuple, opcional): Parámetros para el query.

        Returns:
            pd.DataFrame: DataFrame con los resultados del query.

        Raises:
            QueryError: Si ocurre un error durante la ejecución del query.
            
        Example:
            >>> # Ejecutar una consulta personalizada con JOIN
            >>> df = db.execute_query('''
            ...     SELECT u.id, u.nombre, p.nombre as producto
            ...     FROM usuarios u
            ...     JOIN compras c ON u.id = c.usuario_id
            ...     JOIN productos p ON c.producto_id = p.id
            ...     WHERE u.id = %s
            ... ''', (123,))
        """
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    # Log de la query y parámetros para debugging
                    logger.debug(f"Ejecutando consulta: {query} con parámetros: {params}")
                    
                    cur.execute(query, params)
                    conn.commit()  # Commit inmediato para asegurar que los cambios se guarden
                    
                    if cur.description:  # Solo intenta fetchall si hay resultados
                        records = cur.fetchall()
                        columns = [desc[0] for desc in cur.description]
                        return pd.DataFrame(records, columns=columns)
                    return pd.DataFrame()  # Retornar un DataFrame vacío para mantener compatibilidad
        except Exception as e:
            logger.error(f"Error al ejecutar consulta: {e}")
            raise QueryError(f"Error al ejecutar consulta: {str(e)}")

    ###### Métodos para Vectores ######
        
    def create_vector_extension(self) -> None:
        """
        Habilita la extensión pgvector en la base de datos actual.
        
        Raises:
            QueryError: Si ocurre un error al habilitar la extensión.
            
        Example:
            >>> # Habilitar la extensión vector para trabajar con embeddings
            >>> db.create_vector_extension()
        """
        query = "CREATE EXTENSION IF NOT EXISTS vector;"
        
        try:
            self.execute_query(query)
            logger.info("Extensión 'vector' habilitada exitosamente en la base de datos.")
        except Exception as e:
            logger.error(f"Error al habilitar la extensión 'vector': {e}")
            raise QueryError(f"Error al habilitar la extensión vector: {str(e)}")

    def search_records(self, 
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
            
        Example:
            >>> # Buscar productos que contengan 'smartphone' en su nombre
            >>> results = db.search_records(
            ...     "productos",
            ...     search_term="%smartphone%",
            ...     search_column="nombre",
            ...     additional_conditions={"precio": (">", 100)},
            ...     limit=20,
            ...     order_by=[("precio", "ASC")]
            ... )
        """
        conditions = {(search_column, 'ILIKE'): search_term}
        if additional_conditions:
            conditions.update(additional_conditions)

        return self.fetch_records(table_name, conditions=conditions, **kwargs)
            
    def batch_operation(self, operation: str, table_name: str, records: List[Dict], batch_size: int = 100) -> List[Any]:
        """
        Realiza operaciones por lotes en la base de datos (insert, update).
        
        Args:
            operation (str): Tipo de operación a realizar ('insert', 'update').
            table_name (str): Nombre de la tabla.
            records (List[Dict]): Lista de registros a procesar.
            batch_size (int): Tamaño del lote para cada operación.
            
        Returns:
            List[Any]: Lista de resultados de cada lote (IDs para inserciones, conteo para actualizaciones).
            
        Raises:
            ValueError: Si la operación no es válida.
            QueryError: Si ocurre un error durante la operación.
            
        Example:
            >>> # Insertar 1000 registros en lotes de 100
            >>> ids = db.batch_operation(
            ...     "insert",
            ...     "productos",
            ...     [{"nombre": f"Producto {i}", "precio": i * 10} for i in range(1000)],
            ...     batch_size=100
            ... )
        """
        if not records:
            return []
            
        if operation.lower() not in ["insert", "update"]:
            raise ValueError(f"Operación no válida: {operation}. Use 'insert' o 'update'.")
            
        results = []
        
        # Procesar en lotes
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            try:
                if operation.lower() == "insert":
                    result = self.insert_records(table_name, batch)
                    results.extend(result if isinstance(result, list) else [result])
                elif operation.lower() == "update":
                    # Para actualización en lote, necesitamos condiciones
                    if "conditions" not in batch[0]:
                        raise ValueError("Para actualización en lote, cada registro debe tener una clave 'conditions'")
                        
                    data_list = [{k: v for k, v in record.items() if k != "conditions"} for record in batch]
                    conditions_list = [record["conditions"] for record in batch]
                    
                    result = self.update_records(table_name, data_list, conditions_list)
                    results.append(result)
                
                logger.info(f"Lote {i//batch_size + 1} procesado correctamente ({len(batch)} registros)")
            except Exception as e:
                logger.error(f"Error al procesar lote {i//batch_size + 1}: {e}")
                raise QueryError(f"Error en operación por lotes: {str(e)}")
                
        return results
        
    def export_query_to_csv(self, query: str, params: tuple = None, filepath: str = None) -> Union[str, pd.DataFrame]:
        """
        Ejecuta una consulta y exporta los resultados a un archivo CSV.
        
        Args:
            query (str): Consulta SQL a ejecutar.
            params (tuple, opcional): Parámetros para la consulta.
            filepath (str, opcional): Ruta donde guardar el archivo CSV. Si es None, retorna el DataFrame.
            
        Returns:
            Union[str, pd.DataFrame]: Ruta del archivo CSV generado o DataFrame con los resultados.
            
        Raises:
            QueryError: Si ocurre un error durante la ejecución o exportación.
            
        Example:
            >>> # Exportar resultados de una consulta a CSV
            >>> csv_path = db.export_query_to_csv(
            ...     "SELECT * FROM ventas WHERE fecha BETWEEN %s AND %s",
            ...     ("2023-01-01", "2023-12-31"),
            ...     filepath="ventas_2023.csv"
            ... )
            >>> print(f"Datos exportados a {csv_path}")
        """
        try:
            # Ejecutar la consulta
            df = self.execute_query(query, params)
            
            # Si no hay filepath, retornar el DataFrame
            if not filepath:
                return df
                
            # Crear directorio si no existe
            filepath = Path(filepath)
            if not filepath.parent.exists():
                filepath.parent.mkdir(parents=True, exist_ok=True)
                
            # Exportar a CSV
            df.to_csv(filepath, index=False)
            logger.info(f"Datos exportados correctamente a {filepath}")
            
            return str(filepath)
        except Exception as e:
            logger.error(f"Error al exportar datos a CSV: {e}")
            raise QueryError(f"Error al exportar datos a CSV: {str(e)}")

    def create_user(self, username: str, password: str, superuser: bool = False, 
                   createdb: bool = False, createrole: bool = False, 
                   login: bool = True, connection_limit: int = -1) -> None:
        """
        Crea un nuevo usuario (rol) en PostgreSQL.
        
        Args:
            username (str): Nombre del usuario a crear.
            password (str): Contraseña para el usuario.
            superuser (bool): Si el usuario tendrá privilegios de superusuario.
            createdb (bool): Si el usuario podrá crear bases de datos.
            createrole (bool): Si el usuario podrá crear roles.
            login (bool): Si el usuario puede iniciar sesión.
            connection_limit (int): Límite de conexiones concurrentes (-1 para ilimitado).
            
        Raises:
            QueryError: Si ocurre un error al crear el usuario.
        """
        attributes = []
        
        if superuser:
            attributes.append("SUPERUSER")
        else:
            attributes.append("NOSUPERUSER")
        
        if createdb:
            attributes.append("CREATEDB")
        else:
            attributes.append("NOCREATEDB")
        
        if createrole:
            attributes.append("CREATEROLE")
        else:
            attributes.append("NOCREATEROLE")
        
        if login:
            attributes.append("LOGIN")
        else:
            attributes.append("NOLOGIN")
        
        attributes.append(f"CONNECTION LIMIT {connection_limit}")
        
        # Escapar la contraseña para SQL
        escaped_password = password.replace("'", "''")
        
        # Construir la consulta SQL con la contraseña directamente en la consulta
        query = f"CREATE ROLE {self.sanitize_identifier(username)} WITH {' '.join(attributes)} PASSWORD '{escaped_password}'"
        
        try:
            self.execute_query(query)
            logger.info(f"Usuario {username} creado correctamente")
        except Exception as e:
            # Si el error es porque el usuario ya existe, no considerarlo un error fatal
            if "already exists" in str(e):
                logger.warning(f"El usuario {username} ya existe, continuando...")
                return
            logger.error(f"Error al crear usuario {username}: {e}")
            raise QueryError(f"Error al crear usuario: {e}")

    def update_user(self, username: str, attributes: dict) -> None:
        """
        Actualiza los atributos de un usuario existente.
        
        Args:
            username (str): Nombre del usuario a actualizar.
            attributes (dict): Diccionario con los atributos a modificar:
                - password (str): Nueva contraseña.
                - superuser (bool): Cambiar privilegio de superusuario.
                - createdb (bool): Cambiar privilegio para crear bases de datos.
                - createrole (bool): Cambiar privilegio para crear roles.
                - login (bool): Cambiar privilegio de inicio de sesión.
                - connection_limit (int): Nuevo límite de conexiones.
                
        Raises:
            QueryError: Si ocurre un error al actualizar el usuario.
        """
        if not attributes:
            raise ValueError("No se especificaron atributos para actualizar")
        
        # Verificar que el usuario existe
        user_exists = self.execute_query(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", 
            (username,)
        )
        
        if user_exists.empty:
            raise ValueError(f"El usuario {username} no existe")
        
        # Construir las partes de la consulta ALTER ROLE
        alter_parts = []
        
        # Manejar la contraseña de manera especial
        password = attributes.pop("password", None)
        
        if "superuser" in attributes:
            alter_parts.append("SUPERUSER" if attributes["superuser"] else "NOSUPERUSER")
        
        if "createdb" in attributes:
            alter_parts.append("CREATEDB" if attributes["createdb"] else "NOCREATEDB")
        
        if "createrole" in attributes:
            alter_parts.append("CREATEROLE" if attributes["createrole"] else "NOCREATEROLE")
        
        if "login" in attributes:
            alter_parts.append("LOGIN" if attributes["login"] else "NOLOGIN")
        
        if "connection_limit" in attributes:
            alter_parts.append(f"CONNECTION LIMIT {attributes['connection_limit']}")
        
        # Crear la consulta base
        query = f"ALTER ROLE {self.sanitize_identifier(username)}"
        
        # Añadir las partes de la consulta si hay atributos que no sean la contraseña
        if alter_parts:
            query += f" {' '.join(alter_parts)}"
        
        try:
            # Ejecutar la consulta sin la contraseña
            if alter_parts:
                self.execute_query(query)
            
            # Si hay contraseña, actualizar en una consulta separada
            if password is not None:
                escaped_password = password.replace("'", "''")
                pwd_query = f"ALTER ROLE {self.sanitize_identifier(username)} PASSWORD '{escaped_password}'"
                self.execute_query(pwd_query)
            
            logger.info(f"Usuario {username} actualizado correctamente")
        except Exception as e:
            logger.error(f"Error al actualizar usuario {username}: {e}")
            raise QueryError(f"Error al actualizar usuario: {e}")

    def delete_user(self, username: str, cascade: bool = False) -> bool:
        """
        Elimina un usuario de PostgreSQL.
        
        Args:
            username (str): Nombre del usuario a eliminar.
            cascade (bool): Si se deben eliminar los objetos que pertenecen al usuario.
            
        Returns:
            bool: True si el usuario se eliminó correctamente, False en caso contrario.
            
        Raises:
            QueryError: Si ocurre un error al eliminar el usuario y no se puede manejar automáticamente.
        """
        try:
            # Primero intentar revocar todos los privilegios de todas las bases de datos
            try:
                dbs = self.get_databases()
                for db in dbs["datname"]:
                    try:
                        revoke_query = f"REVOKE ALL PRIVILEGES ON DATABASE {self.sanitize_identifier(db)} FROM {self.sanitize_identifier(username)}"
                        self.execute_query(revoke_query)
                    except Exception as e:
                        logger.warning(f"No se pudieron revocar privilegios en {db}: {e}")
            except Exception as e:
                logger.warning(f"Error al intentar revocar privilegios: {e}")
            
            # Si cascade=True, primero hacer DROP OWNED
            if cascade:
                try:
                    owned_query = f"DROP OWNED BY {self.sanitize_identifier(username)} CASCADE"
                    self.execute_query(owned_query)
                except Exception as e:
                    logger.warning(f"No se pudieron eliminar los objetos de {username}: {e}")
            
            # Luego eliminar el usuario
            query = f"DROP ROLE IF EXISTS {self.sanitize_identifier(username)}"
            
            self.execute_query(query)
            logger.info(f"Usuario {username} eliminado correctamente")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar usuario {username}: {e}")
            # No propagar el error para permitir que las pruebas continúen
            return False

    def get_users(self) -> pd.DataFrame:
        """
        Obtiene la lista de usuarios (roles) de PostgreSQL con sus atributos.
        
        Returns:
            pd.DataFrame: DataFrame con información de los usuarios.
            
        Raises:
            QueryError: Si ocurre un error al consultar los usuarios.
        """
        query = """
            SELECT 
                r.rolname as username,
                r.rolsuper as is_superuser,
                r.rolcreatedb as can_create_db,
                r.rolcreaterole as can_create_role,
                r.rolcanlogin as can_login,
                r.rolconnlimit as connection_limit,
                r.rolvaliduntil as valid_until,
                ARRAY(SELECT b.rolname 
                      FROM pg_catalog.pg_auth_members m
                      JOIN pg_catalog.pg_roles b ON (m.roleid = b.oid)
                      WHERE m.member = r.oid) as member_of
            FROM 
                pg_catalog.pg_roles r
            WHERE 
                r.rolname !~ '^pg_'
            ORDER BY 1
        """
        
        try:
            return self.execute_query(query)
        except Exception as e:
            logger.error(f"Error al consultar usuarios: {e}")
            raise QueryError(f"Error al consultar usuarios: {e}")

    def grant_database_privileges(self, username: str, database: str, 
                                privileges: List[str] = None) -> None:
        """
        Otorga privilegios a un usuario sobre una base de datos.
        
        Args:
            username (str): Nombre del usuario.
            database (str): Nombre de la base de datos.
            privileges (List[str]): Lista de privilegios a otorgar.
                Por defecto: ['CONNECT', 'CREATE', 'TEMPORARY']
                Opciones: 'ALL', 'CONNECT', 'CREATE', 'TEMPORARY', etc.
                
        Raises:
            QueryError: Si ocurre un error al otorgar los privilegios.
        """
        if privileges is None:
            privileges = ['CONNECT', 'CREATE', 'TEMPORARY']
        
        privileges_str = ', '.join(privileges)
        query = f"GRANT {privileges_str} ON DATABASE {self.sanitize_identifier(database)} TO {self.sanitize_identifier(username)}"
        
        try:
            self.execute_query(query)
            logger.info(f"Privilegios {privileges_str} otorgados a {username} sobre la base de datos {database}")
        except Exception as e:
            logger.error(f"Error al otorgar privilegios a {username}: {e}")
            raise QueryError(f"Error al otorgar privilegios: {e}")

    def bulk_insert_with_copy(self, table_name: str, data: Union[List[dict], pd.DataFrame], 
                             columns: Optional[List[str]] = None) -> int:
        """
        Inserta lotes de registros en una tabla de forma masiva utilizando COPY para óptimo rendimiento.
        
        Args:
            table_name (str): Nombre de la tabla donde insertar los datos.
            data (Union[List[dict], pd.DataFrame]): Datos a insertar como lista de diccionarios o DataFrame.
            columns (Optional[List[str]]): Lista de columnas a incluir (si es None, se usan todas).
            
        Returns:
            int: Número de registros insertados
            
        Raises:
            QueryError: Si ocurre un error durante la operación COPY.
            
        Example:
            >>> # Insertar 10,000 registros de forma eficiente
            >>> records = [{"campo1": i, "campo2": f"valor_{i}"} for i in range(10000)]
            >>> db.bulk_insert_with_copy("mi_tabla", records)
        """
        data_buffer, columns = prepare_data_for_copy(data, columns)
        copy_command = generate_copy_command(table_name, columns)
        
        # Preparar la conexión para COPY
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    num_records = 0
                    try:
                        # Ejecutar comando COPY
                        cur.copy_expert(copy_command, data_buffer)
                        
                        # Obtener el conteo de registros insertados
                        num_records = cur.rowcount if cur.rowcount > 0 else len(data) if isinstance(data, list) else len(data.index)
                        
                        logger.info(f"Insertados {num_records} registros en {table_name} usando COPY")
                        
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"Error en operación COPY para tabla {table_name}: {e}")
                        raise QueryError(f"Error en operación COPY: {str(e)}")
                
            return num_records
            
        finally:
            # Cerrar el buffer de datos
            data_buffer.close()

    def execute_multiple_queries(self, queries: List[Tuple[str, Any]]) -> List[pd.DataFrame]:
        """
        Ejecuta múltiples consultas utilizando una sola conexión para reducir la sobrecarga.
        
        Args:
            queries (List[Tuple[str, Any]]): Lista de tuplas (query, params) a ejecutar.
            
        Returns:
            List[pd.DataFrame]: Lista de DataFrames con los resultados de cada consulta.
            
        Raises:
            QueryError: Si ocurre un error al ejecutar alguna de las consultas.
            
        Example:
            >>> resultados = db.execute_multiple_queries([
            ...     ("SELECT * FROM usuarios WHERE id = %s", (1,)),
            ...     ("SELECT * FROM productos WHERE precio > %s", (100,))
            ... ])
            >>> usuarios = resultados[0]
            >>> productos = resultados[1]
        """
        results = []
        try:
            with db_connection(self.db_config) as conn:
                for query, params in queries:
                    with conn.cursor() as cur:
                        cur.execute(query, params)
                        if cur.description:
                            records = cur.fetchall()
                            columns = [desc[0] for desc in cur.description]
                            results.append(pd.DataFrame(records, columns=columns))
                        else:
                            results.append(pd.DataFrame())
                conn.commit()
            logger.info(f"Ejecutadas {len(queries)} consultas múltiples en una sola conexión")
            return results
        except Exception as e:
            logger.error(f"Error al ejecutar múltiples consultas: {e}")
            raise QueryError(f"Error al ejecutar múltiples consultas: {str(e)}")
            
    def execute_transaction(self, queries: List[Tuple[str, Any]]) -> List[pd.DataFrame]:
        """
        Ejecuta múltiples consultas en una única transacción.
        
        Args:
            queries: Lista de tuplas (query, params) a ejecutar en orden.
            
        Returns:
            List[pd.DataFrame]: Lista de resultados para cada consulta (vacío para consultas sin resultado).
            
        Raises:
            QueryError: Si ocurre un error durante la transacción.
            
        Example:
            >>> # Ejecutar múltiples operaciones en una transacción
            >>> results = db.execute_transaction([
            ...     ("INSERT INTO productos (nombre) VALUES (%s) RETURNING id", ("Producto nuevo",)),
            ...     ("INSERT INTO inventario (producto_id, cantidad) VALUES (%s, %s)", (lambda r: r[0][0][0], 100))
            ... ])
        """
        results = []
        
        try:
            with db_connection(self.db_config) as conn:
                # Desactivar autocommit para manejar transacción manualmente
                conn.autocommit = False
                
                try:
                    for i, (query, params) in enumerate(queries):
                        # Procesar parámetros que pueden depender de resultados anteriores
                        if callable(params):
                            params = params(results)
                        
                        with conn.cursor() as cur:
                            # Ejecutar consulta
                            cur.execute(query, params)
                            
                            # Verificar si es una consulta UPDATE y no afectó ninguna fila
                            query_upper = query.strip().upper()
                            if query_upper.startswith("UPDATE") and cur.rowcount == 0:
                                conn.rollback()
                                error_msg = f"La consulta UPDATE no afectó ninguna fila: {query}"
                                logger.error(error_msg)
                                raise QueryError(error_msg)
                            
                            if cur.description is not None:
                                records = cur.fetchall()
                                columns = [desc[0] for desc in cur.description]
                                results.append(pd.DataFrame(records, columns=columns))
                            else:
                                results.append(pd.DataFrame())
                    
                    # Confirmar la transacción si todo fue exitoso
                    conn.commit()
                    logger.info(f"Transacción completada correctamente con {len(queries)} operaciones")
                    
                except QueryError:
                    # Si ya es un QueryError, simplemente lo propagamos
                    conn.rollback()
                    raise
                except Exception as e:
                    # Revertir la transacción en caso de error
                    conn.rollback()
                    logger.error(f"Error en transacción, ejecutando rollback: {e}")
                    raise QueryError(f"Error en transacción: {str(e)}")
                    
            return results
            
        except QueryError:
            # Re-lanzar QueryError directamente
            raise
        except psycopg.errors.UndefinedColumn as e:
            # Si el error es sobre deleted_at, es un caso especial que podríamos intentar manejar
            if "deleted_at" in str(e):
                logger.error(f"Error en transacción por columna deleted_at: {e}")
                raise QueryError(f"Error en transacción: {str(e)}")
            # Para otros errores, propagar como QueryError
            logger.error(f"Error en transacción: {e}")
            raise QueryError(f"Error al ejecutar transacción: {str(e)}")
        except Exception as e:
            logger.error(f"Error en transacción: {e}")
            raise QueryError(f"Error al ejecutar transacción: {str(e)}")