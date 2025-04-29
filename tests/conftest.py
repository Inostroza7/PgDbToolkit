# tests/conftest.py

"""
Configuración para pruebas pytest de la biblioteca PgDbToolkit.

Este archivo contiene fixtures que se utilizan en múltiples archivos de prueba.
"""

import os
import sys
import pytest
import pytest_asyncio
import psycopg
import asyncio
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
import re
import uuid

# Añadir el directorio raíz al path de Python para poder importar pgdbtoolkit
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar los módulos a probar
from pgdbtoolkit import (
    PgDbToolkit, 
    AsyncPgDbToolkit, 
    PgConnectionPool, 
    PgAsyncConnectionPool,
    MigrationManager,
    Log
)

# Cargar variables de entorno para las pruebas
load_dotenv(".env.test", override=True)

# Configuración para las pruebas
TEST_DB_CONFIG = {
    'host': os.getenv('TEST_DB_HOST', 'localhost'),
    'port': os.getenv('TEST_DB_PORT', '5432'),
    'user': os.getenv('TEST_DB_USER', 'postgres'),
    'password': os.getenv('TEST_DB_PASSWORD', 'postgres'),
    'dbname': os.getenv('TEST_DB_DATABASE', 'postgres')
}

# Configurar logger para pruebas
Log.configure(level="DEBUG")
logger = Log(__name__)

# Función para generar un nombre único para la base de datos
def generate_test_db_name():
    """Genera un nombre único para la base de datos de prueba."""
    timestamp = int(datetime.now().timestamp())
    unique_id = uuid.uuid4().hex[:8]
    return f"pgdbtoolkit_test_{timestamp}_{unique_id}"

# Variable compartida para el nombre de la base de datos de prueba
TEST_DB_NAME = None

# Fixture para el toolkit sincrónico
@pytest.fixture(scope="session")
def pg_toolkit():
    """Proporciona una instancia de PgDbToolkit para pruebas."""
    global TEST_DB_NAME
    TEST_DB_NAME = generate_test_db_name()
    
    logger.info(f"Configurando toolkit con configuración: {TEST_DB_CONFIG}")
    toolkit = PgDbToolkit(db_config=TEST_DB_CONFIG.copy())
    
    # Crear base de datos temporal para pruebas
    try:
        toolkit.create_database(TEST_DB_NAME)
        logger.info(f"Base de datos de prueba creada: {TEST_DB_NAME}")
    except Exception as e:
        if "already exists" in str(e):
            logger.warning(f"La base de datos {TEST_DB_NAME} ya existe, continuando con las pruebas")
        else:
            logger.error(f"Error al crear base de datos de prueba: {e}")
            pytest.fail(f"No se pudo crear la base de datos de prueba: {e}")
    
    # Cambiar a la base de datos de prueba
    toolkit.change_database(TEST_DB_NAME)
    
    yield toolkit
    
    # Limpiar después de las pruebas
    toolkit.change_database("postgres")  # Cambiar a otra base de datos para poder eliminar la de prueba
    try:
        toolkit.delete_database(TEST_DB_NAME)
        logger.info(f"Base de datos de prueba eliminada: {TEST_DB_NAME}")
    except Exception as e:
        logger.warning(f"No se pudo eliminar la base de datos de prueba: {e}")

# Fixture para el toolkit asincrónico
@pytest.fixture(scope="session")
def async_pg_toolkit():
    """Proporciona una instancia de AsyncPgDbToolkit para pruebas."""
    logger.info(f"Configurando toolkit asíncrono con configuración: {TEST_DB_CONFIG}")
    toolkit = AsyncPgDbToolkit(db_config=TEST_DB_CONFIG.copy())
    
    # Usar la misma base de datos que el toolkit sincrónico
    global TEST_DB_NAME
    if TEST_DB_NAME is None:
        # Si pg_toolkit no se ha ejecutado primero, generamos un nombre
        TEST_DB_NAME = generate_test_db_name()
        
        # Crear base de datos temporal para pruebas (usando el toolkit sincrónico)
        sync_toolkit = PgDbToolkit(db_config=TEST_DB_CONFIG.copy())
        try:
            sync_toolkit.create_database(TEST_DB_NAME)
            logger.info(f"Base de datos de prueba creada para pruebas asíncronas: {TEST_DB_NAME}")
        except Exception as e:
            if "already exists" in str(e):
                logger.warning(f"La base de datos {TEST_DB_NAME} ya existe, continuando con las pruebas")
            else:
                logger.error(f"Error al crear base de datos de prueba para pruebas asíncronas: {e}")
                pytest.fail(f"No se pudo crear la base de datos de prueba para pruebas asíncronas: {e}")
    
    # Cambiar a la base de datos de prueba
    toolkit.change_database(TEST_DB_NAME)
    
    yield toolkit
    
    # No es necesario limpiar aquí ya que ya se limpia en el fixture sincrónico

# Fixture para pool de conexiones
@pytest.fixture(scope="function")
def connection_pool():
    """Proporciona un pool de conexiones para pruebas."""
    test_config = TEST_DB_CONFIG.copy()
    test_config['dbname'] = TEST_DB_NAME
    pool = PgConnectionPool(test_config, min_size=1, max_size=3)
    yield pool
    pool.close()

# Fixture para pool de conexiones asíncronas
@pytest_asyncio.fixture
async def async_connection_pool(async_pg_toolkit):
    """Proporciona un pool de conexiones asíncronas para pruebas."""
    # Usar la misma configuración que async_pg_toolkit para garantizar consistencia
    pool = PgAsyncConnectionPool(
        async_pg_toolkit.db_config,  # Usar la misma configuración del toolkit
        min_size=1,
        max_size=3
    )
    await pool.open()
    yield pool
    await pool.close()

# Fixture para tabla de prueba
@pytest.fixture(scope="function")
def test_table(pg_toolkit):
    """Crea una tabla de prueba y la elimina después de la prueba."""
    table_name = f"test_table_{int(datetime.now().timestamp())}"
    
    pg_toolkit.create_table(table_name, {
        "id": "SERIAL PRIMARY KEY",
        "name": "VARCHAR(100) NOT NULL",
        "value": "INTEGER",
        "active": "BOOLEAN DEFAULT TRUE",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    })
    
    yield table_name
    
    pg_toolkit.delete_table(table_name)

# Fixture para tabla de prueba asincrónica
@pytest_asyncio.fixture
async def async_test_table(async_pg_toolkit):
    """Crea una tabla de prueba asincrónica y la elimina después de la prueba."""
    table_name = f"async_test_table_{int(datetime.now().timestamp())}"
    
    await async_pg_toolkit.create_table(table_name, {
        "id": "SERIAL PRIMARY KEY",
        "name": "VARCHAR(100) NOT NULL",
        "value": "INTEGER",
        "active": "BOOLEAN DEFAULT TRUE",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "deleted_at": "TIMESTAMP",
    })
    
    yield table_name
    
    await async_pg_toolkit.delete_table(table_name)

# Fixture para datos de prueba
@pytest.fixture(scope="function")
def test_data():
    """Proporciona datos de prueba para insertar en tablas."""
    return [
        {"name": "Test 1", "value": 100, "active": True},
        {"name": "Test 2", "value": 200, "active": True},
        {"name": "Test 3", "value": 300, "active": True},
        {"name": "Test 4", "value": 400, "active": True},
        {"name": "Test 5", "value": 500, "active": False}
    ]

# Fixture para directorio de migraciones
@pytest.fixture(scope="function")
def migrations_dir(tmp_path):
    """Crea un directorio temporal para migraciones."""
    migrations_path = tmp_path / "migrations"
    migrations_path.mkdir()
    return str(migrations_path)

# Fixture para manager de migraciones
@pytest.fixture(scope="function")
def migration_manager(pg_toolkit, migrations_dir):
    """Proporciona un manager de migraciones para pruebas."""
    return MigrationManager(pg_toolkit, migrations_dir=migrations_dir)

# Fixture para manager de migraciones asincrónico
@pytest.fixture(scope="function")
def async_migration_manager(async_pg_toolkit, migrations_dir):
    """Proporciona un manager de migraciones asincrónico para pruebas."""
    return MigrationManager(async_pg_toolkit, migrations_dir=migrations_dir)

# Leer la versión desde el archivo __version__.py sin importarlo
with open('pgdbtoolkit/__version__.py', 'r') as f:
    version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        __version__ = version_match.group(1)
    else:
        raise RuntimeError("No se encontró la versión en pgdbtoolkit/__version__.py")