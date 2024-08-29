import pytest
from pgdbtoolkit import PgDbTools

@pytest.fixture(scope="module")
def db_tool(create_test_db):
    config = {
        'dbname': 'test_db',
        'user': 'test_user',
        'password': 'test_pass',
        'host': 'localhost',
        'port': '5432',
    }
    return PgDbTools(db_config=config)

def test_insert_record(db_tool):
    # Suponiendo que hay una tabla `test_table` en la base de datos
    db_tool.insert_record('test_table', {'col1': 'value1', 'col2': 'value2'})
    result = db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert len(result) == 1
    assert result.iloc[0]['col2'] == 'value2'

def test_fetch_records(db_tool):
    # Suponiendo que hay registros en la tabla `test_table`
    result = db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert len(result) > 0

def test_update_record(db_tool):
    db_tool.update_record('test_table', {'col2': 'new_value'}, {'col1': 'value1'})
    result = db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert result.iloc[0]['col2'] == 'new_value'

def test_delete_record(db_tool):
    db_tool.delete_record('test_table', {'col1': 'value1'})
    result = db_tool.fetch_records('test_table', {'col1': 'value1'})
    assert len(result) == 0