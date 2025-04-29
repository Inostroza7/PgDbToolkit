# PgDbToolkit 📊

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![PostgreSQL](https://img.shields.io/badge/postgresql-14%2B-blue)
![Psycopg](https://img.shields.io/badge/psycopg-3.1%2B-brightgreen)
![Build](https://img.shields.io/badge/build-passing-brightgreen)

`PgDbToolkit` es una biblioteca Python robusta y completa para interactuar con bases de datos PostgreSQL, ofreciendo tanto operaciones sincrónicas como asíncronas con una API elegante y consistente. Diseñada para desarrolladores que buscan simplicidad sin sacrificar potencia, esta biblioteca facilita todo desde operaciones CRUD básicas hasta consultas vectoriales avanzadas y migraciones de esquemas.

## Tabla de Contenidos

- [PgDbToolkit 📊](#pgdbtoolkit-)
  - [Tabla de Contenidos](#tabla-de-contenidos)
  - [Características Principales ✨](#características-principales-)
  - [Instalación 🚀](#instalación-)
  - [Configuración 🛠️](#configuración-️)
    - [Usando variables de entorno](#usando-variables-de-entorno)
    - [Configuración directa](#configuración-directa)
  - [Ejemplos de Uso 💻](#ejemplos-de-uso-)
    - [API Sincrónica](#api-sincrónica)
    - [API Asincrónica](#api-asincrónica)
    - [Uso de Pools de Conexiones](#uso-de-pools-de-conexiones)
    - [Soporte para Vectores y Búsqueda por Similitud](#soporte-para-vectores-y-búsqueda-por-similitud)
    - [Sistema de Migraciones](#sistema-de-migraciones)
    - [Validación de Datos](#validación-de-datos)
  - [Características Avanzadas 🔥](#características-avanzadas-)
    - [Operaciones por Lotes](#operaciones-por-lotes)
    - [Transacciones Atómicas](#transacciones-atómicas)
    - [Logging Personalizado](#logging-personalizado)
    - [Soft Delete](#soft-delete)
    - [Exportación de Datos](#exportación-de-datos)
    - [Gestión de Usuarios](#gestión-de-usuarios)
  - [API Completa 📚](#api-completa-)
    - [Gestión de Bases de Datos](#gestión-de-bases-de-datos)
    - [Gestión de Tablas](#gestión-de-tablas)
    - [Gestión de Registros](#gestión-de-registros)
    - [Operaciones Vectoriales](#operaciones-vectoriales)
    - [Utilidades](#utilidades)
  - [Manejo de Errores 🛡️](#manejo-de-errores-️)
  - [Roadmap 🛣️](#roadmap-️)
  - [Contribuciones 👥](#contribuciones-)
  - [Licencia 📄](#licencia-)

## Características Principales ✨

- **API Dual**: Implementaciones sincrónica (`PgDbToolkit`) y asincrónica (`AsyncPgDbToolkit`) con interfaces idénticas
- **Manejo Inteligente de Consultas**: Construcción automática de consultas SQL complejas con condiciones avanzadas
- **Soporte para pgvector**: Integración directa con la extensión vectorial de PostgreSQL para búsquedas de similitud
- **Gestión de Pools de Conexiones**: Manejo eficiente de múltiples conexiones simultáneas
- **Sistema de Migraciones**: Versionado y aplicación controlada de cambios de esquema
- **Validación Robusta**: Funciones integradas para validar datos antes de su inserción
- **Manejo Especializado de Errores**: Jerarquía de excepciones específicas para diagnóstico preciso
- **Operaciones por Lotes**: Procesamiento eficiente de grandes volúmenes de datos con `batch_operation` y `bulk_insert_with_copy`
- **Exportación de Datos**: Funcionalidad integrada para exportar resultados de consultas a CSV
- **Transacciones Atómicas**: Soporte completo para transacciones y operaciones atómicas
- **Logging Configurable**: Sistema centralizado de logs con niveles personalizables
- **Soft Delete**: Implementación de borrado lógico para mantener historial de registros
- **Gestión de Usuarios**: Herramientas para la creación y gestión de usuarios de PostgreSQL

## Instalación 🚀

```bash
pip install pgdbtoolkit
```

Para habilitar todas las características, incluya los extras:

```bash
pip install "pgdbtoolkit[all]"
```

O instale solo lo que necesite:

```bash
pip install "pgdbtoolkit[async,pool,vector]"
```

## Configuración 🛠️

### Usando variables de entorno

Cree un archivo `.env` en la raíz de su proyecto:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=secreto
DB_DATABASE=mi_base_de_datos
DB_SSLMODE=prefer
DB_CONNECT_TIMEOUT=10

# Configuración para pools de conexión
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=10
DB_POOL_MAX_IDLE=300
DB_POOL_MAX_LIFETIME=3600
DB_POOL_TIMEOUT=30.0
```

### Configuración directa

```python
from pgdbtoolkit import PgDbToolkit, AsyncPgDbToolkit

# Configuración personalizada
db_config = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": "secreto",
    "dbname": "mi_base_de_datos"
}

# Versión sincrónica
db = PgDbToolkit(db_config=db_config)

# Versión asincrónica
db_async = AsyncPgDbToolkit(db_config=db_config)
```

## Ejemplos de Uso 💻

### API Sincrónica

```python
from pgdbtoolkit import PgDbToolkit

# Inicializar toolkit (usará variables de entorno por defecto)
db = PgDbToolkit()

# Crear una tabla
db.create_table("usuarios", {
    "id": "SERIAL PRIMARY KEY",
    "nombre": "VARCHAR(100) NOT NULL",
    "email": "VARCHAR(255) UNIQUE",
    "edad": "INTEGER",
    "activo": "BOOLEAN DEFAULT TRUE",
    "fecha_registro": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
})

# Insertar múltiples registros
usuarios = [
    {"nombre": "Juan Pérez", "email": "juan@ejemplo.com", "edad": 30},
    {"nombre": "Ana García", "email": "ana@ejemplo.com", "edad": 25},
    {"nombre": "Carlos López", "email": "carlos@ejemplo.com", "edad": 35}
]
ids = db.insert_records("usuarios", usuarios)
print(f"IDs insertados: {ids}")

# Consulta avanzada con condiciones
resultados = db.fetch_records(
    "usuarios",
    columns=["id", "nombre", "email"],
    conditions={
        ("edad", ">"): 25,
        "activo": True
    },
    order_by=[("nombre", "ASC")],
    limit=10
)
print(resultados)

# Actualizar registros
db.update_records(
    "usuarios",
    {"activo": False},
    {"id": 1}
)

# Eliminar registros con condiciones complejas
db.delete_records(
    "usuarios", 
    {
        "activo": False,
        ("fecha_registro", "<"): "2023-01-01"
    }
)

# Ejecutar query personalizado
df = db.execute_query(
    "SELECT u.nombre, u.email, c.total FROM usuarios u JOIN compras c ON u.id = c.usuario_id WHERE c.total > %s",
    (100,)
)
```

### API Asincrónica

```python
import asyncio
from pgdbtoolkit import AsyncPgDbToolkit

async def main():
    # Inicializar toolkit asincrónico
    db = AsyncPgDbToolkit()
    
    # Crear una tabla
    await db.create_table("productos", {
        "id": "SERIAL PRIMARY KEY",
        "nombre": "VARCHAR(100) NOT NULL",
        "precio": "DECIMAL(10,2)",
        "stock": "INTEGER DEFAULT 0",
        "fecha_creacion": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    })
    
    # Insertar registros en lote
    productos = [{"nombre": f"Producto {i}", "precio": i * 10, "stock": i} for i in range(1000)]
    await db.batch_operation("insert", "productos", productos, batch_size=100)
    
    # Consultar registros con condiciones complejas
    resultados = await db.fetch_records(
        "productos",
        conditions={("precio", "BETWEEN"): [50, 150]},
        order_by=[("precio", "DESC")]
    )
    print(resultados)
    
    # Exportar resultados a CSV
    await db.export_query_to_csv(
        "SELECT * FROM productos WHERE stock < %s",
        (10,),
        filepath="productos_bajos_stock.csv"
    )
    
    # Ejecutar múltiples operaciones en una transacción
    await db.execute_transaction([
        ("UPDATE productos SET stock = stock - 1 WHERE id = %s", (42,)),
        ("INSERT INTO ventas (producto_id, cantidad) VALUES (%s, %s)", (42, 1))
    ])

if __name__ == "__main__":
    asyncio.run(main())
```

### Uso de Pools de Conexiones

```python
from pgdbtoolkit import PgConnectionPool, PgAsyncConnectionPool
import asyncio

# Pool sincrónico
with PgConnectionPool(min_size=2, max_size=10) as pool:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM usuarios")
            print(cur.fetchall())
    
    # Obtener estadísticas del pool
    stats = pool.stats()
    print(f"Conexiones activas: {stats.get('active', 0)}")

# Pool asincrónico
async def usando_pool_async():
    async with PgAsyncConnectionPool(min_size=2, max_size=10) as pool:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM usuarios")
                print(await cur.fetchall())
        
        # Redimensionar el pool dinámicamente
        await pool.resize(min_size=5, max_size=20)
        
        # Obtener estadísticas
        stats = await pool.stats()
        print(f"Conexiones activas: {stats.get('active', 0)}")

asyncio.run(usando_pool_async())
```

### Soporte para Vectores y Búsqueda por Similitud

```python
import json
import numpy as np

# Habilitar extensión vector
db.create_vector_extension()

# Crear tabla con campo vector
db.create_table("embeddings", {
    "id": "SERIAL PRIMARY KEY",
    "text": "TEXT NOT NULL",
    "embedding": "vector(1536)"
})

# Insertar un embedding
embedding = np.random.rand(1536).tolist()  # Vector de dimensión 1536
db.insert_records("embeddings", {
    "text": "Ejemplo de texto para embedding",
    "embedding": embedding
})

# Búsqueda por similaridad utilizando el operador <=> (distancia coseno)
query_embedding = np.random.rand(1536).tolist()
results = db.execute_query(
    "SELECT id, text, 1 - (embedding <=> %s::vector) as similarity FROM embeddings ORDER BY similarity DESC LIMIT 5",
    (json.dumps(query_embedding),)
)
print(results)

# Búsqueda utilizando el índice KNN (si está creado)
results = db.execute_query(
    "SELECT id, text, 1 - (embedding <=> %s::vector) as similarity FROM embeddings ORDER BY embedding <=> %s::vector LIMIT 5",
    (json.dumps(query_embedding), json.dumps(query_embedding))
)
print(results)

# Búsqueda con condiciones adicionales
results = db.execute_query(
    """
    SELECT id, text, 1 - (embedding <=> %s::vector) as similarity 
    FROM embeddings 
    WHERE text ILIKE %s
    ORDER BY similarity DESC LIMIT 5
    """,
    (json.dumps(query_embedding), "%ejemplo%")
)
print(results)
```

### Sistema de Migraciones

```python
from pgdbtoolkit import PgDbToolkit, MigrationManager

db = PgDbToolkit()
migrations = MigrationManager(db, migrations_dir="./migrations")

# Crear una nueva migración
migrations.create_migration(
    name="crear_tabla_usuarios",
    up_sql="""
    CREATE TABLE usuarios (
        id SERIAL PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    down_sql="""
    DROP TABLE IF EXISTS usuarios;
    """
)

# Aplicar migraciones pendientes (versión sincrónica)
applied = migrations.apply_migrations_sync()
print(f"Se aplicaron {len(applied)} migraciones")

# Revertir la última migración (versión sincrónica)
reverted = migrations.rollback_migrations_sync(steps=1)
print(f"Se revirtieron {len(reverted)} migraciones")

# Versión asincrónica
async def run_migrations():
    # Aplicar migraciones
    applied = await migrations.apply_migrations_async()
    print(f"Se aplicaron {len(applied)} migraciones")
    
    # Revertir migraciones
    reverted = await migrations.rollback_migrations_async(steps=1)
    print(f"Se revirtieron {len(reverted)} migraciones")

# Generar migración a partir de diferencias de esquema
target_schema = {
    "usuarios": {
        "id": "SERIAL PRIMARY KEY",
        "nombre": "VARCHAR(100) NOT NULL",
        "email": "VARCHAR(255) UNIQUE",
        "fecha_registro": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "direccion": "TEXT"  # Nueva columna
    }
}
migrations.generate_migration_from_schema_diff(target_schema, prefix="add_direccion")
```

### Validación de Datos

```python
from pgdbtoolkit import validate_email, validate_schema, validate_length, validate_numeric

# Validar un email
try:
    validate_email("usuario@ejemplo.com", "email")
except Exception as e:
    print(e)

# Validar estructura completa de datos
schema = {
    "nombre": {"type": str, "required": True, "validators": [lambda x, **kw: validate_length(x, 3, 100)]},
    "email": {"type": str, "required": True, "validators": [validate_email]},
    "edad": {"type": int, "validators": [lambda x, **kw: validate_numeric(x, 18, 120)]}
}

errors = validate_schema({"nombre": "Ana", "email": "ana@ejemplo.com", "edad": 25}, schema)
if errors:
    print("Errores de validación:", errors)
else:
    print("Datos válidos")

# Validar registro antes de insertar
from pgdbtoolkit import validate_record

table_schema = {
    "nombre": {"type": str, "required": True, "validators": [lambda x, **kw: validate_length(x, 3, 100)]},
    "email": {"type": str, "required": True, "validators": [validate_email]},
    "edad": {"type": int, "validators": [lambda x, **kw: validate_numeric(x, 18, 120)]}
}

try:
    validate_record({"nombre": "Ana", "email": "ana@ejemplo.com", "edad": 25}, table_schema)
    print("Registro válido")
except Exception as e:
    print(f"Error de validación: {e}")
```

## Características Avanzadas 🔥

### Operaciones por Lotes

```python
# Insertar miles de registros de manera eficiente
registros = [{"campo1": f"valor{i}", "campo2": i} for i in range(10000)]

# Método 1: Usando batch_operation
db.batch_operation("insert", "mi_tabla", registros, batch_size=500)

# Método 2: Usando bulk_insert_with_copy (más rápido para grandes volúmenes)
num_insertados = db.bulk_insert_with_copy("mi_tabla", registros)
print(f"Se insertaron {num_insertados} registros")

# Versión asincrónica
async def insertar_lotes():
    num_insertados = await db.bulk_insert_with_copy("mi_tabla", registros)
    print(f"Se insertaron {num_insertados} registros de forma asíncrona")
```

### Transacciones Atómicas

```python
# Asegurar que múltiples operaciones se ejecuten como una unidad
# Versión sincrónica
db.execute_transaction([
    ("INSERT INTO cuentas (id, balance) VALUES (%s, %s)", (1, 1000)),
    ("INSERT INTO cuentas (id, balance) VALUES (%s, %s)", (2, 500)),
    ("INSERT INTO transferencias (origen, destino, monto) VALUES (%s, %s, %s)", (1, 2, 200)),
    ("UPDATE cuentas SET balance = balance - %s WHERE id = %s", (200, 1)),
    ("UPDATE cuentas SET balance = balance + %s WHERE id = %s", (200, 2))
])

# Con referencias a resultados anteriores
# La función lambda puede acceder a los resultados de las consultas anteriores
resultados = db.execute_transaction([
    ("INSERT INTO productos (nombre, precio) VALUES (%s, %s) RETURNING id", ("Nuevo Producto", 99.99)),
    ("INSERT INTO inventario (producto_id, cantidad) VALUES (%s, %s)", 
     lambda results: (results[0].iloc[0, 0], 100))  # Usa el ID del producto insertado
])

# Versión asincrónica
async def realizar_transferencia():
    await db.execute_transaction([
        ("INSERT INTO transferencias (origen, destino, monto) VALUES (%s, %s, %s)", (1, 2, 200)),
        ("UPDATE cuentas SET balance = balance - %s WHERE id = %s", (200, 1)),
        ("UPDATE cuentas SET balance = balance + %s WHERE id = %s", (200, 2))
    ])
```

### Logging Personalizado

```python
from pgdbtoolkit import Log

# Configurar nivel de log global
Log.configure(level="DEBUG", log_file="db_operations.log")

# O para un módulo específico
logger = Log(__name__)
logger.info("Operación completada con éxito")
logger.error("Ocurrió un error importante")
logger.debug("Información detallada para depuración")

# Captura automática de errores en operaciones de base de datos
# Los logs incluyen información como consultas SQL, parámetros y stacktrace
try:
    db.execute_query("SELECT * FROM tabla_inexistente")
except Exception as e:
    # El error ya ha sido registrado automáticamente
    pass
```

### Soft Delete

```python
# Borrado lógico: marcar registros como eliminados pero mantenerlos en la base de datos
# Versión sincrónica
db.delete_records(
    "usuarios",
    {"id": 123},
    soft_delete=True,
    delete_column="deleted_at"  # Se usará CURRENT_TIMESTAMP
)

# Si la columna no existe, se creará automáticamente

# Excluir registros eliminados lógicamente en consultas
activos = db.fetch_records(
    "usuarios",
    conditions={"deleted_at": None}  # Solo registros no eliminados
)

# Versión asincrónica
async def soft_delete_usuario(id_usuario):
    await db.delete_records(
        "usuarios",
        {"id": id_usuario},
        soft_delete=True,
        delete_column="deleted_at"
    )
```

### Exportación de Datos

```python
# Exportar resultados de consulta a CSV
# Versión sincrónica
csv_path = db.export_query_to_csv(
    "SELECT * FROM ventas WHERE fecha BETWEEN %s AND %s",
    ("2023-01-01", "2023-12-31"),
    filepath="ventas_2023.csv"
)
print(f"Datos exportados a {csv_path}")

# Si no se especifica filepath, retorna un DataFrame
df = db.export_query_to_csv(
    "SELECT * FROM productos WHERE stock < %s",
    (10,)
)
print(f"Se encontraron {len(df)} productos con stock bajo")

# Versión asincrónica
async def exportar_datos():
    csv_path = await db.export_query_to_csv(
        "SELECT * FROM ventas WHERE fecha BETWEEN %s AND %s",
        ("2023-01-01", "2023-12-31"),
        filepath="ventas_2023_async.csv"
    )
    print(f"Datos exportados a {csv_path}")
```

### Gestión de Usuarios

```python
# Crear un nuevo usuario en PostgreSQL
db.create_user(
    username="app_user",
    password="secreto123",
    superuser=False,
    createdb=False,
    createrole=False,
    login=True,
    connection_limit=10
)

# Otorgar privilegios a un usuario
db.grant_database_privileges(
    username="app_user",
    database="mi_aplicacion",
    privileges=["CONNECT", "SELECT", "INSERT", "UPDATE"]
)

# Actualizar un usuario existente
db.update_user(
    "app_user", 
    {
        "password": "nuevo_secreto",
        "connection_limit": 20
    }
)

# Ver usuarios existentes
usuarios = db.get_users()
print(usuarios)

# Eliminar un usuario
db.delete_user("app_user", cascade=True)  # cascade=True elimina también objetos propiedad del usuario
```

## API Completa 📚

El toolkit proporciona una extensa API para cubrir todas sus necesidades de acceso a datos:

### Gestión de Bases de Datos

- `create_database(database_name)`: Crea una nueva base de datos.
- `delete_database(database_name)`: Elimina una base de datos existente.
- `get_databases()`: Obtiene una lista de todas las bases de datos.

### Gestión de Tablas

- `create_table(table_name, schema)`: Crea una nueva tabla con el esquema proporcionado.
- `delete_table(table_name)`: Elimina una tabla existente.
- `alter_table(table_name, ...)`: Modifica una tabla existente (añadir/eliminar columnas, restricciones, etc.).
- `get_tables()`: Obtiene una lista de todas las tablas en la base de datos actual.
- `get_table_info(table_name)`: Obtiene información detallada sobre una tabla.
- `truncate_table(table_name)`: Elimina todos los registros de una tabla sin eliminar la tabla.

### Gestión de Registros

- `insert_records(table_name, record)`: Inserta uno o más registros en una tabla.
- `fetch_records(table_name, columns, conditions, order_by, limit, offset)`: Consulta registros con condiciones avanzadas.
- `update_records(table_name, data, conditions)`: Actualiza registros que cumplen condiciones.
- `delete_records(table_name, conditions, soft_delete, delete_column)`: Elimina registros que cumplen condiciones, con opción de borrado lógico.
- `execute_query(query, params)`: Ejecuta una consulta SQL personalizada.
- `search_records(table_name, search_term, search_column, additional_conditions)`: Realiza búsquedas de texto en una tabla.
- `batch_operation(operation, table_name, records, batch_size)`: Realiza operaciones por lotes.
- `bulk_insert_with_copy(table_name, data, columns)`: Inserta grandes volúmenes de datos usando COPY.
- `export_query_to_csv(query, params, filepath)`: Exporta resultados de consulta a CSV.
- `execute_transaction(queries)`: Ejecuta múltiples operaciones en una sola transacción.
- `execute_multiple_queries(queries)`: Ejecuta múltiples consultas en una sola conexión.

### Operaciones Vectoriales

- `create_vector_extension()`: Habilita la extensión pgvector en la base de datos.
- `execute_query()`: Utilizado para realizar consultas vectoriales personalizadas.
- `insert_records()`: Para insertar datos incluyendo vectores.
- `update_records()`: Para actualizar registros con vectores.
- `search_records()`: Para buscar registros mediante texto (complementa búsquedas vectoriales).

### Utilidades

- `create_user(username, password, ...)`: Crea un usuario en PostgreSQL.
- `update_user(username, attributes)`: Actualiza atributos de un usuario.
- `delete_user(username, cascade)`: Elimina un usuario.
- `get_users()`: Obtiene lista de usuarios.
- `grant_database_privileges(username, database, privileges)`: Otorga privilegios a un usuario.

## Manejo de Errores 🛡️

La biblioteca proporciona excepciones específicas para diferentes tipos de errores:

```python
from pgdbtoolkit.exceptions import (
    DatabaseError, 
    ConnectionError, 
    QueryError, 
    ValidationError,
    RecordNotFoundError,
    MissingConfigError,
    ConfigurationError,
    PoolError,
    MigrationError
)

# Ejemplo de uso
try:
    db.execute_query("SELECT * FROM tabla_inexistente")
except QueryError as e:
    print(f"Error en consulta: {e}")
    # Manejar el error específicamente

try:
    db.insert_records("usuarios", {"email": "correo_invalido"})
except ValidationError as e:
    print(f"Error de validación: {e}")
    # Solicitar corrección al usuario

# Patrón de manejo de errores recomendado
try:
    # Operaciones de base de datos...
    db.execute_transaction([...])
except ConnectionError:
    # Manejar problemas de conexión
    print("No se pudo conectar a la base de datos")
except QueryError as e:
    # Manejar errores de consulta
    print(f"La consulta falló: {e}")
except ValidationError as e:
    # Manejar errores de validación
    print(f"Datos inválidos: {e}")
except DatabaseError as e:
    # Manejar cualquier otro error de base de datos
    print(f"Error de base de datos: {e}")
```

## Roadmap 🛣️

- [ ] Soporte para campos geométricos (PostGIS)
- [ ] Herramientas de análisis y rendimiento de consultas
- [ ] Interfaz web para gestión de migraciones
- [ ] Soporte para almacenamiento y búsqueda de documentos JSON/JSONB
- [ ] Generación automática de modelos ORM
- [ ] Mejoras en la integración con frameworks web populares
- [ ] Caching inteligente de resultados frecuentes
- [ ] Soporte para SQL Server y MySQL

## Contribuciones 👥

¡Las contribuciones son bienvenidas! Para contribuir:

1. Realiza un fork del repositorio.
2. Crea una nueva rama (`git checkout -b feature/mi-nueva-funcionalidad`).
3. Realiza tus cambios y commitea (`git commit -am 'Añadir nueva funcionalidad'`).
4. Push a la rama (`git push origin feature/mi-nueva-funcionalidad`).
5. Crea un nuevo Pull Request.

Consulta `CONTRIBUTING.md` para más detalles sobre nuestro proceso de contribución y estándares de código.

## Licencia 📄

Este proyecto está licenciado bajo la Licencia Apache 2.0 - ver el archivo [LICENSE](LICENSE) para más detalles.

```
Copyright 2024 Gustavo Inostroza

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```