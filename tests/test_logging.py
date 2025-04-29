import logging
import pytest
from pgdbtoolkit.log import Log

# Crear una instancia de Log para los tests
logger = Log("test_logger")

def test_logging_info(caplog):
    # Usar el método de clase para establecer el nivel
    Log.set_level(logging.INFO)
    with caplog.at_level(logging.INFO):
        logger.info('This is an info message')
        assert 'This is an info message' in caplog.text

def test_logging_error(caplog):
    with caplog.at_level(logging.ERROR):
        logger.error('This is an error message')
        assert 'This is an error message' in caplog.text

def test_logging_to_file(tmpdir):
    logfile = tmpdir.join("test.log")
    # Configurar el log para que escriba a un archivo
    Log.configure(log_file=str(logfile))
    
    logger.error('This is an error written to file')
    
    with open(logfile, 'r') as f:
        content = f.read()
    
    assert 'This is an error written to file' in content