import pytest
import psycopg
from psycopg.rows import dict_row
from pgdbtools.sync_db import PgDbTools
from pgdbtools.async_db import AsyncPgDbTools

DATABASE_NAME = "test_db"
USER = "test_user"
PASSWORD = "test_pass"
HOST = "localhost"
PORT = "5432"


@pytest.fixture(scope="session")
def create_test_db():
    """Fixture para crear y eliminar la base de datos de prueba."""
    # Conectar al servidor PostgreSQL
    with psycopg.connect(f"dbname=postgres user=postgres password={PASSWORD} host={HOST} port={PORT}") as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Crear el rol si no existe
            cur.execute(f"SELECT 1 FROM pg_roles WHERE rolname = '{USER}';")
            if not cur.fetchone():
                cur.execute(f"CREATE ROLE {USER} WITH LOGIN PASSWORD '{PASSWORD}';")
                cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {DATABASE_NAME} TO {USER};")
                cur.execute(f"ALTER ROLE {USER} CREATEDB;")  # Permitir que el rol cree bases de datos

            # Verificar si la base de datos ya existe
            cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DATABASE_NAME}';")
            exists = cur.fetchone()
            if not exists:
                # Crear base de datos de prueba si no existe
                cur.execute(f"CREATE DATABASE {DATABASE_NAME};")
    
    # Asignar permisos en el esquema public
    with psycopg.connect(f"dbname={DATABASE_NAME} user=postgres password={PASSWORD} host={HOST} port={PORT}") as conn:
        with conn.cursor() as cur:
            cur.execute(f"GRANT ALL PRIVILEGES ON SCHEMA public TO {USER};")
            cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO {USER};")

    # Conectar a la base de datos de prueba para crear tablas
    with psycopg.connect(f"dbname={DATABASE_NAME} user={USER} password={PASSWORD} host={HOST} port={PORT}") as conn:
        with conn.cursor() as cur:
            # Crear tabla de prueba si no existe
            cur.execute("""
                CREATE TABLE IF NOT EXISTS test_table (
                    col1 VARCHAR,
                    col2 VARCHAR
                );
            """)

    yield

    # Después de los tests, eliminar la base de datos de prueba
    with psycopg.connect(f"dbname=postgres user=postgres password={PASSWORD} host={HOST} port={PORT}") as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            # Terminar conexiones activas
            cur.execute(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{DATABASE_NAME}'
                AND pid <> pg_backend_pid();
            """)
            # Eliminar la base de datos
            cur.execute(f"DROP DATABASE {DATABASE_NAME};")

@pytest.fixture(scope="function")
def db_tool(create_test_db):
    config = {
        'dbname': DATABASE_NAME,
        'user': USER,
        'password': PASSWORD,
        'host': HOST,
        'port': PORT,
    }
    return PgDbTools(db_config=config)

@pytest.fixture(scope="function")
def async_db_tool(create_test_db):
    config = {
        'dbname': DATABASE_NAME,
        'user': USER,
        'password': PASSWORD,
        'host': HOST,
        'port': PORT,
    }
    return AsyncPgDbTools(db_config=config)