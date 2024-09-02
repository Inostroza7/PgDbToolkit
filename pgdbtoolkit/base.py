from .config import load_database_config

class BaseDbToolkit:
    """Clase base que proporciona configuraciones comunes para las clases de operaciones de base de datos."""

    def __init__(self, db_config=None, dbname=None):
        """Inicializa la clase base con la configuración de la base de datos.

        Args:
            db_config (dict, opcional): Diccionario con los parámetros de conexión.
            dbname (str, opcional): Nombre de la base de datos a utilizar.
        """
        self.db_config = load_database_config(db_config)
        if dbname:
            self.db_config['dbname'] = dbname

    def change_database(self, dbname: str):
        """Cambia el nombre de la base de datos en la configuración.

        Args:
            dbname (str): Nombre de la nueva base de datos a utilizar.
        """
        self.db_config['dbname'] = dbname