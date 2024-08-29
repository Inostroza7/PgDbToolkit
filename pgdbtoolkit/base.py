from .config import load_database_config

class BaseDbToolkit:
    """Clase base que proporciona configuraciones comunes para las clases de operaciones de base de datos."""

    def __init__(self, db_config=None):
        """Inicializa la clase base con la configuración de la base de datos.

        Args:
            db_config (dict, opcional): Diccionario con los parámetros de conexión.
        """
        self.db_config = load_database_config(db_config)