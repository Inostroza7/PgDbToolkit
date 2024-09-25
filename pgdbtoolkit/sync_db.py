##### Clase Sincrónica para Operaciones en la Base de Datos #####

import psycopg
import pandas as pd
from contextlib import contextmanager
import os
from .log import log
from .base import BaseDbToolkit
import json

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
        yield conn
    finally:
        conn.close()

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

    def insert_record(self, table_name: str, record: dict) -> None:
        """
        Inserta un registro en la tabla especificada de manera sincrónica.

        Args:
            table_name (str): Nombre de la tabla en la que se insertará el registro.
            record (dict): Diccionario con los datos del registro a insertar.

        Raises:
            psycopg.Error: Si ocurre un error durante la inserción.
        """
        sanitized_record = {k: self.sanitize_value(v) for k, v in record.items()}
        columns = ', '.join([self.sanitize_identifier(k) for k in sanitized_record.keys()])
        placeholders = ', '.join(['%s'] * len(sanitized_record))
        query = f"INSERT INTO {self.sanitize_identifier(table_name)} ({columns}) VALUES ({placeholders})"
        
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, tuple(sanitized_record.values()))
                    conn.commit()
            log.info(f"Record inserted successfully into {table_name}")
        except psycopg.Error as e:
            log.error(f"Error inserting record into {table_name}: {e}")
            raise

    def fetch_records(self, table_name: str, conditions: dict = None) -> pd.DataFrame:
        """
        Consulta registros de una tabla con condiciones opcionales.

        Args:
            table_name (str): Nombre de la tabla de la cual se consultarán los registros.
            conditions (dict, opcional): Diccionario de condiciones para filtrar los registros.

        Returns:
            pd.DataFrame: DataFrame con los registros consultados.

        Raises:
            psycopg.Error: Si ocurre un error durante la consulta.
        """
        query, params = self.build_query(table_name, conditions=conditions, query_type="SELECT")
        try:
            with db_connection(self.db_config) as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                    cur.execute(query, params)
                    records = cur.fetchall()
            return pd.DataFrame(records)
        except psycopg.Error as e:
            log.error(f"Error fetching records from {table_name}: {str(e)}")
            raise
        

    def update_record(self, table_name: str, record: dict, conditions: dict) -> None:
        """
        Actualiza un registro en la tabla especificada basado en las condiciones.

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
                    records = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
            return pd.DataFrame(records, columns=columns)
        except psycopg.Error as e:
            log.error(f"Error executing query: {e}")
            raise

    ##### Método Auxiliar para Construcción de Queries #####

    def build_query(self, table_name: str, data: dict = None, conditions: dict = None, query_type: str = "SELECT") -> tuple:
        """
        Construye un query SQL basado en el tipo de operación.

        Args:
            table_name (str): Nombre de la tabla.
            data (dict, opcional): Diccionario con los datos del registro para INSERT y UPDATE.
            conditions (dict, opcional): Diccionario de condiciones para filtrar los registros.
            query_type (str, opcional): Tipo de query a construir ('SELECT', 'INSERT', 'UPDATE', 'DELETE').

        Returns:
            tuple: (query_string, params)
        """
        table_name = self.sanitize_identifier(table_name)
        params = []

        if query_type == "SELECT":
            query = "SELECT * FROM {}".format(table_name)
            if conditions:
                condition_str = ' AND '.join(["{}= %s".format(self.sanitize_identifier(k)) for k in conditions.keys()])
                query += " WHERE {}".format(condition_str)
                params.extend(conditions.values())
        elif query_type == "INSERT":
            if not data:
                raise ValueError("INSERT queries require data.")
            columns = ', '.join([self.sanitize_identifier(col) for col in data.keys()])
            placeholders = ', '.join(['%s'] * len(data))
            query = "INSERT INTO {} ({}) VALUES ({})".format(table_name, columns, placeholders)
            params.extend(data.values())
        elif query_type == "UPDATE":
            if not data:
                raise ValueError("UPDATE queries require data.")
            set_str = ', '.join(["{}= %s".format(self.sanitize_identifier(k)) for k in data.keys()])
            query = "UPDATE {} SET {}".format(table_name, set_str)
            params.extend(data.values())
            if conditions:
                condition_str = ' AND '.join(["{}= %s".format(self.sanitize_identifier(k)) for k in conditions.keys()])
                query += " WHERE {}".format(condition_str)
                params.extend(conditions.values())
        elif query_type == "DELETE":
            if not conditions:
                raise ValueError("DELETE queries require at least one condition.")
            condition_str = ' AND '.join(["{}= %s".format(self.sanitize_identifier(k)) for k in conditions.keys()])
            query = "DELETE FROM {} WHERE {}".format(table_name, condition_str)
            params.extend(conditions.values())
        else:
            raise ValueError("Query type '{}' not recognized.".format(query_type))

        return query, params

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