import os
from dotenv import load_dotenv

load_dotenv(override=True)

def load_database_config(custom_config=None):
    """Carga la configuración de la base de datos desde un diccionario o el archivo .env.
    
    Args:
        custom_config (dict, opcional): Diccionario con los parámetros de conexión.
        
    Returns:
        dict: Configuración de conexión a la base de datos.
    """
    if custom_config:
        return custom_config
    return {
        'dbname': os.getenv('DB_DATABASE'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT'),
    }