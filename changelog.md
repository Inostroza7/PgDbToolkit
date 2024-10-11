# Changelog

## [0.1.12] - 2024-10-03

### Added
- **Added `search_records` to `sync_db`:** Agrega la función search records que realiza una búsqueda de texto en una columna específica.

## [0.1.11] - 2024-10-03

### Added
- **Fix `sync_db`:** Fix conexión que permitia solamente manejo de vectores ahora se pueden hacer query sin registro de vectores

## [0.1.10] - 2024-10-03

### Added
- **Added `sync_db`:** Ahora permite agregar order_direction 'ASC' y 'DESC'

## [0.1.9] - 2024-10-03

### Added
- **Added `sync_db`:** Ahora permite agregar order_by y limit 

## [0.1.8] - 2024-10-02

### Added
- **Fix `sync_db`:** Fix update_vectors

## [0.1.7] - 2024-10-02

### Added
- **Fix `sync_db`:** Fix search_vectors

## [0.1.6] - 2024-09-26

### Added
- **x `sync_db`:** Ahora permite recibir Pandas Dataframe y CSV

## [0.1.5] - 2024-09-24

### Added
- **Fix `sync_db`:** Fix del sync_db

## [0.1.4] - 2024-09-24

### Added
- **Fix `sync_db`:** Fix del sync_db

## [0.1.3] - 2024-09-02

### Added
- **Fix `log`:** Fix de logs con la librería httpx.

## [0.1.2] - 2024-09-02

### Added
- **Nueva clase `AsyncPgDbToolkit`:** Implementada para gestionar operaciones asíncronas en la base de datos.
  - **`async def create_database`:** Crea una base de datos en el servidor PostgreSQL de manera asíncrona.
  - **`async def delete_database`:** Elimina una base de datos en el servidor PostgreSQL de manera asíncrona.
  - **`async def get_databases`:** Obtiene una lista de todas las bases de datos en el servidor PostgreSQL de manera asíncrona.
  - **`async def create_table`:** Crea una nueva tabla en la base de datos con un esquema especificado de manera asíncrona.
  - **`async def delete_table`:** Elimina una tabla de la base de datos de manera asíncrona.
  - **`async def alter_table`:** Realiza múltiples tipos de alteraciones en una tabla existente en la base de datos de manera asíncrona.
  - **`async def get_tables`:** Obtiene una lista con los nombres de todas las tablas en la base de datos de manera asíncrona.
  - **`async def get_table_info`:** Obtiene la información de las columnas de una tabla, incluyendo nombre, tipo de datos y restricciones de manera asíncrona.
  - **`async def truncate_table`:** Elimina todos los registros de una tabla sin eliminar la tabla de manera asíncrona.
  - **`async def insert_record`:** Inserta un registro en la tabla especificada de manera asíncrona.
  - **`async def fetch_records`:** Consulta registros de una tabla con condiciones opcionales de manera asíncrona.
  - **`async def update_record`:** Actualiza un registro en la tabla especificada basado en las condiciones de manera asíncrona.
  - **`async def delete_record`:** Elimina un registro de la tabla especificada basado en las condiciones de manera asíncrona.
  - **`async def execute_query`:** Ejecuta un query SQL personalizado de manera asíncrona.
  - **`def build_query`:** Método auxiliar para la construcción de queries SQL basado en el tipo de operación.

### Changed
- **`PgDbToolkit`**: Añadido manejo de finalización de conexiones antes de eliminar una base de datos.

### Removed
- **Eliminación de código redundante:** Limpieza de funciones duplicadas y mejoras en la eficiencia del código.

---

## [0.1.1] - 2024-08-31

### Added
- **Primera versión de `PgDbToolkit`:** Gestión de operaciones sincrónicas en bases de datos PostgreSQL.
  - **`def create_database`:** Crea una nueva base de datos en el servidor PostgreSQL.
  - **`def delete_database`:** Elimina una base de datos en el servidor PostgreSQL.
  - **`def get_databases`:** Obtiene una lista de todas las bases de datos en el servidor PostgreSQL.
  - **`def create_table`:** Crea una nueva tabla en la base de datos con un esquema especificado.
  - **`def delete_table`:** Elimina una tabla de la base de datos.
  - **`def alter_table`:** Realiza múltiples tipos de alteraciones en una tabla existente en la base de datos.
  - **`def get_tables`:** Obtiene una lista con los nombres de todas las tablas en la base de datos.
  - **`def get_table_info`:** Obtiene la información de las columnas de una tabla, incluyendo nombre, tipo de datos y restricciones.
  - **`def truncate_table`:** Elimina todos los registros de una tabla sin eliminar la tabla.
  - **`def insert_record`:** Inserta un registro en la tabla especificada.
  - **`def fetch_records`:** Consulta registros de una tabla con condiciones opcionales.
  - **`def update_record`:** Actualiza un registro en la tabla especificada basado en las condiciones.
  - **`def delete_record`:** Elimina un registro de la tabla especificada basado en las condiciones.
  - **`def execute_query`:** Ejecuta un query SQL personalizado.
  - **`def build_query`:** Método auxiliar para la construcción de queries SQL basado en el tipo de operación.
```

### ROADMAP

1. **Métodos para la gestión de usuarios:**
   - `create_user`: Para crear un nuevo usuario en PostgreSQL.
   - `delete_user`: Para eliminar un usuario existente.
   - `grant_privileges`: Para otorgar privilegios a un usuario en una base de datos o tabla.

2. **Métodos para la gestión de índices:**
   - `create_index`: Para crear un índice en una tabla.
   - `delete_index`: Para eliminar un índice.

3. **Métodos para la copia masiva:**
   - `copy_from`: Para copiar datos de un archivo a una tabla.
   - `copy_to`: Para exportar datos de una tabla a un archivo.

4. **Métodos de backup y restauración:**
   - `backup_database`: Para realizar un backup de la base de datos.
   - `restore_database`: Para restaurar una base de datos desde un backup.

5. **Métodos de migración de esquema:**
   - `migrate_schema`: Para aplicar cambios en el esquema a través de migraciones.

