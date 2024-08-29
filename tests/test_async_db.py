import pytest
import asyncio
from pgdbtoolkit import AsyncPgDbTools

@pytest.fixture(scope="module")
def db_tool(create_test_db):
    config = {
        'dbname': 'test_db',
        'user': 'test_user',
        'password': 'test_pass',
        'host': 'localhost',
        'port': '5432',
    }
    return AsyncPgDbTools(db_config=config)

@pytest.mark.asyncio
async def test_insert_record(db_tool):
    await db_tool.insert_record('test_table', {'col1': 'value1', 'col2': 'value2'})
    result = await db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert len(result) == 1
    assert result.iloc[0]['col2'] == 'value2'

@pytest.mark.asyncio
async def test_fetch_records(db_tool):
    result = await db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert len(result) > 0

@pytest.mark.asyncio
async def test_update_record(db_tool):
    await db_tool.update_record('test_table', {'col2': 'new_value'}, {'col1': 'value1'})
    result = await db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert result.iloc[0]['col2'] == 'new_value'

@pytest.mark.asyncio
async def test_delete_record(db_tool):
    await db_tool.delete_record('test_table', {'col1': 'value1'})
    result = await db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert len(result) == 0