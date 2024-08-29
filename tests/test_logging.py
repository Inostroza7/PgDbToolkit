import logging
import pytest
from pgdbtoolkit import log

def test_logging_info(caplog):
    log.setLevel(logging.INFO)
    with caplog.at_level(logging.INFO):
        log.info('This is an info message')
        assert 'This is an info message' in caplog.text

def test_logging_error(caplog):
    with caplog.at_level(logging.ERROR):
        log.error('This is an error message')
        assert 'This is an error message' in caplog.text

def test_logging_to_file(tmpdir):
    logfile = tmpdir.join("test.log")
    log_file_handler = logging.FileHandler(logfile)
    log.logger.addHandler(log_file_handler)
    
    log.error('This is an error written to file')
    
    with open(logfile, 'r') as f:
        content = f.read()
    
    assert 'This is an error written to file' in content

    log.logger.removeHandler(log_file_handler)