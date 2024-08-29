import pytest
import asyncio
from pgdbtoolkit import PgDbTools, AsyncPgDbTools

@pytest.fixture
def sync_db_tool():
    config = {
        'dbname': 'test_db',
        'user': 'test_user',
        'password': 'test_pass',
        'host': 'localhost',
        'port': '5432',
    }
    return PgDbTools(db_config=config)

@pytest.fixture
def async_db_tool():
    config = {
        'dbname': 'test_db',
        'user': 'test_user',
        'password': 'test_pass',
        'host': 'localhost',
        'port': '5432',
    }
    return AsyncPgDbTools(db_config=config)

def test_sync_crud_operations(sync_db_tool):
    # Inserción
    sync_db_tool.insert_record('test_table', {'col1': 'value1', 'col2': 'value2'})
    
    # Consulta
    result = sync_db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert len(result) == 1
    assert result.iloc[0]['col2'] == 'value2'
    
    # Actualización
    sync_db_tool.update_record('test_table', {'col2': 'new_value'}, {'col1': 'value1'})
    result = sync_db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert result.iloc[0]['col2'] == 'new_value'
    
    # Eliminación
    sync_db_tool.delete_record('test_table', {'col1': 'value1'})
    result = sync_db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert len(result) == 0

@pytest.mark.asyncio
async def test_async_crud_operations(async_db_tool):
    # Inserción
    await async_db_tool.insert_record('test_table', {'col1': 'value1', 'col2': 'value2'})
    
    # Consulta
    result = await async_db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert len(result) == 1
    assert result.iloc[0]['col2'] == 'value2'
    
    # Actualización
    await async_db_tool.update_record('test_table', {'col2': 'new_value'}, {'col1': 'value1'})
    result = await async_db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert result.iloc[0]['col2'] == 'new_value'
    
    # Eliminación
    await async_db_tool.delete_record('test_table', {'col1': 'value1'})
    result = await async_db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert len(result) == 0