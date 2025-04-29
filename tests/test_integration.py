import pytest
import asyncio
import os
from dotenv import load_dotenv
from pgdbtoolkit import PgDbToolkit, AsyncPgDbToolkit

# Cargar configuración de .env.test
load_dotenv(".env.test", override=True)

# Obtener configuración de admin
ADMIN_DB_CONFIG = {
    'host': os.getenv('TEST_DB_HOST', 'localhost'),
    'port': os.getenv('TEST_DB_PORT', '5432'),
    'user': os.getenv('TEST_DB_USER', 'postgres'),
    'password': os.getenv('TEST_DB_PASSWORD', 'postgres'),
    'dbname': os.getenv('TEST_DB_DATABASE', 'postgres')
}

# Configuración para las pruebas con test_user
TEST_USER_CONFIG = {
    'dbname': os.getenv('TEST_DB_DATABASE', 'postgres'),
    'user': 'test_user',
    'password': 'test_pass',
    'host': os.getenv('TEST_DB_HOST', 'localhost'),
    'port': os.getenv('TEST_DB_PORT', '5432'),
}

@pytest.fixture(scope="session")
def admin_toolkit():
    """Crea una instancia de PgDbToolkit con credenciales de admin para setup."""
    return PgDbToolkit(db_config=ADMIN_DB_CONFIG.copy())

@pytest.fixture(scope="session")
def setup_test_environment(admin_toolkit):
    """Prepara el entorno de prueba, creando el usuario test_user si no existe."""
    # Crear test_user si no existe y otorgarle privilegios
    admin_toolkit.execute_query("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'test_user') THEN
                CREATE ROLE test_user WITH LOGIN PASSWORD 'test_pass';
                GRANT CREATE ON DATABASE %s TO test_user;
                GRANT ALL PRIVILEGES ON DATABASE %s TO test_user;
                ALTER ROLE test_user CREATEDB;
            END IF;
        EXCEPTION WHEN insufficient_privilege THEN
            RAISE NOTICE 'Privilegios insuficientes para crear/modificar el usuario';
        END
        $$;
    """ % (ADMIN_DB_CONFIG['dbname'], ADMIN_DB_CONFIG['dbname']))
    
    # Crear tabla de prueba si no existe
    admin_toolkit.execute_query("""
        CREATE TABLE IF NOT EXISTS test_table (
            id SERIAL PRIMARY KEY,
            col1 VARCHAR(100),
            col2 VARCHAR(100)
        )
    """)
    
    # Dar permisos a test_user en la tabla
    admin_toolkit.execute_query("""
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO test_user;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO test_user;
    """)
    
    # Limpiar cualquier dato existente
    admin_toolkit.execute_query("TRUNCATE test_table RESTART IDENTITY")
    
    yield
    
    # Limpiar después de las pruebas
    admin_toolkit.execute_query("TRUNCATE test_table RESTART IDENTITY")

@pytest.fixture
def sync_db_tool(setup_test_environment):
    """Proporciona una instancia de PgDbToolkit con el usuario test_user."""
    return PgDbToolkit(db_config=TEST_USER_CONFIG)

@pytest.fixture
def async_db_tool(setup_test_environment):
    """Proporciona una instancia de AsyncPgDbToolkit con el usuario test_user."""
    return AsyncPgDbToolkit(db_config=TEST_USER_CONFIG)

def test_sync_crud_operations(sync_db_tool):
    """Prueba operaciones CRUD sincrónicas."""
    # Inserción
    sync_db_tool.insert_records('test_table', {'col1': 'value1', 'col2': 'value2'})
    
    # Consulta
    result = sync_db_tool.fetch_records('test_table', conditions={'col1': 'value1'})
    assert len(result) == 1
    assert result.iloc[0]['col2'] == 'value2'
    
    # Actualización
    sync_db_tool.update_records('test_table', {'col2': 'new_value'}, {'col1': 'value1'})
    result = sync_db_tool.fetch_records('test_table', conditions={'col1': 'value1'})
    assert result.iloc[0]['col2'] == 'new_value'
    
    # Eliminación
    sync_db_tool.delete_records('test_table', {'col1': 'value1'})
    result = sync_db_tool.fetch_records('test_table', conditions={'col1': 'value1'})
    assert len(result) == 0

@pytest.mark.asyncio
async def test_async_crud_operations(async_db_tool):
    """Prueba operaciones CRUD asincrónicas."""
    # Inserción
    await async_db_tool.insert_records('test_table', {'col1': 'value1', 'col2': 'value2'})
    
    # Consulta
    result = await async_db_tool.fetch_records('test_table', conditions={'col1': 'value1'})
    assert len(result) == 1
    assert result.iloc[0]['col2'] == 'value2'
    
    # Actualización
    await async_db_tool.update_records('test_table', {'col2': 'new_value'}, {'col1': 'value1'})
    result = await async_db_tool.fetch_records('test_table', conditions={'col1': 'value1'})
    assert result.iloc[0]['col2'] == 'new_value'
    
    # Eliminación
    await async_db_tool.delete_records('test_table', {'col1': 'value1'})
    result = await async_db_tool.fetch_records('test_table', conditions={'col1': 'value1'})
    assert len(result) == 0