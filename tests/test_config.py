import os
import pytest
from pgdbtoolkit import load_database_config

def test_load_database_config_from_env():
    # Simular entorno
    os.environ['DB_DATABASE'] = 'test_db'
    os.environ['DB_USER'] = 'test_user'
    os.environ['DB_PASSWORD'] = 'test_pass'
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_PORT'] = '5432'

    config = load_database_config()

    assert config['dbname'] == 'test_db'
    assert config['user'] == 'test_user'
    assert config['password'] == 'test_pass'
    assert config['host'] == 'localhost'
    assert config['port'] == '5432'

def test_load_database_config_custom():
    custom_config = {
        'dbname': 'custom_db',
        'user': 'custom_user',
        'password': 'custom_pass',
        'host': 'custom_host',
        'port': '5433',
    }
    config = load_database_config(custom_config)

    assert config['dbname'] == 'custom_db'
    assert config['user'] == 'custom_user'
    assert config['password'] == 'custom_pass'
    assert config['host'] == 'custom_host'
    assert config['port'] == '5433'