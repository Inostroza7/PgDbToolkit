# PgDbToolkit 📊

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![PostgreSQL](https://img.shields.io/badge/postgresql-✔️-blue)
![Build](https://img.shields.io/badge/build-passing-brightgreen)

`PgDbToolkit` es un paquete Python diseñado para gestionar operaciones en bases de datos PostgreSQL de manera eficiente, tanto de manera sincrónica como asíncrona. Este paquete es ideal para desarrolladores y equipos que buscan simplificar y optimizar la interacción con bases de datos PostgreSQL en sus proyectos.

## Características ✨

- **Soporte Sincrónico y Asíncrono:** Gestiona operaciones de base de datos tanto en modo sincrónico como asíncrono.
- **Manejo Eficiente de Conexiones:** Utiliza context managers para manejar las conexiones a la base de datos de manera eficiente.
- **Facilidad de Configuración:** Carga configuraciones desde un archivo `.env` o proporciona un diccionario personalizado directamente en el código.
- **Logging Personalizado:** Integra un sistema de logging configurable para monitorear y depurar operaciones de base de datos.
- **Operaciones CRUD:** Facilita la inserción, actualización, eliminación y consulta de registros.
- **Gestión de Bases de Datos:** Permite crear, eliminar y listar bases de datos.
- **Gestión de Tablas:** Facilita la creación, eliminación, modificación y consulta de tablas.
- **Construcción de Queries:** Ofrece un método auxiliar para construir queries SQL personalizados.

## Instalación 🚀

Puedes instalar `PgDbToolkit` desde PyPI utilizando pip:

```bash
pip install PgDbToolkit
```

## Uso Básico 💻

### 1. Configuración Inicial 🛠️

Puedes configurar la conexión a la base de datos de dos maneras:

#### Opción 1: Archivo `.env` 🌐

Crea un archivo `.env` en el directorio raíz de tu proyecto con la configuración de tu base de datos:

```env
DB_DATABASE=mydatabase
DB_USER=myuser
DB_PASSWORD=mypassword
DB_HOST=localhost
DB_PORT=5432
LOG_LEVEL=DEBUG
```

#### Opción 2: Configuración en el Código 🔧

También puedes pasar la configuración directamente en tu código como un diccionario:

```python
from pgdbtoolkit import PgDbToolkit

# Configuración personalizada
db_config = {
    'dbname': 'mydatabase',
    'user': 'myuser',
    'password': 'mypassword',
    'host': 'localhost',
    'port': '5432'
}

# Inicializa la herramienta con la configuración personalizada
db_tool = PgDbToolkit(db_config=db_config)
```

### 2. Ejemplo de Uso Sincrónico 🔄

```python
from pgdbtoolkit import PgDbToolkit

# Inicializa la herramienta con la configuración predeterminada o personalizada
db_tool = PgDbToolkit()

# Crea una nueva base de datos
db_tool.create_database('nueva_base_de_datos')

# Elimina una base de datos
db_tool.delete_database('nueva_base_de_datos')

# Crea una nueva tabla
db_tool.create_table('mi_tabla', {
    'id': 'SERIAL PRIMARY KEY',
    'nombre': 'VARCHAR(100)',
    'edad': 'INTEGER'
})

# Inserta un registro
db_tool.insert_record('mi_tabla', {'nombre': 'John Doe', 'edad': 30})

# Consulta registros
records = db_tool.fetch_records('mi_tabla', {'edad': 30})
print(records)

# Actualiza un registro
db_tool.update_record('mi_tabla', {'edad': 31}, {'nombre': 'John Doe'})

# Elimina un registro
db_tool.delete_record('mi_tabla', {'nombre': 'John Doe'})
```

### 3. Ejemplo de Uso Asíncrono ⚡

```python
import asyncio
from pgdbtoolkit import AsyncPgDbToolkit

async def main():
    # Inicializa la herramienta asíncrona con la configuración predeterminada o personalizada
    db_tool = AsyncPgDbToolkit()

    # Crea una nueva base de datos
    await db_tool.create_database('nueva_base_de_datos')

    # Elimina una base de datos
    await db_tool.delete_database('nueva_base_de_datos')

    # Crea una nueva tabla
    await db_tool.create_table('mi_tabla', {
        'id': 'SERIAL PRIMARY KEY',
        'nombre': 'VARCHAR(100)',
        'edad': 'INTEGER'
    })

    # Inserta un registro
    await db_tool.insert_record('mi_tabla', {'nombre': 'John Doe', 'edad': 30})

    # Consulta registros
    records = await db_tool.fetch_records('mi_tabla', {'edad': 30})
    print(records)

    # Actualiza un registro
    await db_tool.update_record('mi_tabla', {'edad': 31}, {'nombre': 'John Doe'})

    # Elimina un registro
    await db_tool.delete_record('mi_tabla', {'nombre': 'John Doe'})

# Ejecuta la función principal
asyncio.run(main())
```

### 4. Logging Personalizado 📜

El sistema de logging permite personalizar los niveles de log y decidir si se quiere guardar en un archivo o en la consola.

```python
from pgdbtoolkit import log

# Cambia el nivel de logging
log.setLevel("INFO")

# Loggea un mensaje
log.info("Este es un mensaje de información.")
```

## Contribuciones 👥

¡Las contribuciones son bienvenidas! Si deseas contribuir al proyecto, por favor sigue estos pasos:

1. Realiza un fork del repositorio.
2. Crea una nueva rama (`git checkout -b feature/mi-nueva-funcionalidad`).
3. Realiza tus cambios y commitea (`git commit -am 'Añadir nueva funcionalidad'`).
4. Push a la rama (`git push origin feature/mi-nueva-funcionalidad`).
5. Crea un nuevo Pull Request.

## Roadmap 🛤️

- [ ] Soporte para operaciones avanzadas de PostgreSQL.
- [ ] Mejoras en la documentación con ejemplos más complejos.
- [ ] Integración con herramientas de CI/CD.
- [ ] Añadir más tests unitarios y de integración.

## Licencia 📄

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

---

¡Gracias por usar `PgDbToolkit`! Si tienes alguna pregunta o sugerencia, no dudes en abrir un issue en el repositorio. 😊
