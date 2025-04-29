# migrations.py

"""
Gestión de migraciones para bases de datos PostgreSQL.
Este módulo proporciona clases para la gestión de migraciones de esquemas
de base de datos, permitiendo versionar y aplicar cambios de manera controlada.
"""

import os
import re
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
from pathlib import Path

from .exceptions import MigrationError

logger = logging.getLogger("pg_toolkit.migrations")

class Migration:
    """
    Clase base que representa una migración individual.
    """
    
    def __init__(
        self, 
        version: str, 
        name: str, 
        up_sql: str, 
        down_sql: str = None, 
        description: str = ""
    ):
        """
        Inicializa una migración.
        
        Args:
            version (str): Versión de la migración (típicamente timestamp).
            name (str): Nombre de la migración.
            up_sql (str): SQL para aplicar la migración.
            down_sql (str, opcional): SQL para revertir la migración.
            description (str, opcional): Descripción detallada de la migración.
        """
        self.version = version
        self.name = name
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.description = description or name
        self.applied_at = None
    
    def __str__(self):
        return f"Migration v{self.version}: {self.name}"
    
    def __repr__(self):
        return f"Migration(version='{self.version}', name='{self.name}')"


class MigrationManager:
    """
    Gestor de migraciones para bases de datos PostgreSQL.
    """
    
    def __init__(self, db_toolkit, migrations_dir: str = "migrations"):
        """
        Inicializa el gestor de migraciones.
        
        Args:
            db_toolkit: Instancia de PgDbToolkit o AsyncPgDbToolkit.
            migrations_dir (str): Directorio donde se almacenan las migraciones.
        """
        self.db_toolkit = db_toolkit
        self.migrations_dir = Path(migrations_dir)
        self.table_name = "migrations"
        self._ensure_migration_dir()
    
    def _ensure_migration_dir(self):
        """
        Asegura que el directorio de migraciones exista.
        """
        if not self.migrations_dir.exists():
            self.migrations_dir.mkdir(parents=True)
            logger.info(f"Directorio de migraciones creado: {self.migrations_dir}")
    
    async def _ensure_migrations_table_async(self):
        """
        Asegura que la tabla de migraciones exista (versión asíncrona).
        """
        schema = {
            "id": "SERIAL PRIMARY KEY",
            "version": "VARCHAR(50) NOT NULL UNIQUE",
            "name": "VARCHAR(255) NOT NULL",
            "description": "TEXT",
            "applied_at": "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
        }
        
        # Verificar si la tabla existe
        try:
            tables = await self.db_toolkit.get_tables()
            if self.table_name not in tables:
                await self.db_toolkit.create_table(self.table_name, schema)
                logger.info(f"Tabla de migraciones '{self.table_name}' creada")
        except Exception as e:
            logger.error(f"Error al verificar/crear tabla de migraciones: {e}")
            raise MigrationError(f"Error al preparar la tabla de migraciones: {e}")
    
    def _ensure_migrations_table_sync(self):
        """
        Asegura que la tabla de migraciones exista (versión sincrónica).
        """
        schema = {
            "id": "SERIAL PRIMARY KEY",
            "version": "VARCHAR(50) NOT NULL UNIQUE",
            "name": "VARCHAR(255) NOT NULL",
            "description": "TEXT",
            "applied_at": "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
        }
        
        # Verificar si la tabla existe
        try:
            tables = self.db_toolkit.get_tables()
            if self.table_name not in tables:
                self.db_toolkit.create_table(self.table_name, schema)
                logger.info(f"Tabla de migraciones '{self.table_name}' creada")
        except Exception as e:
            logger.error(f"Error al verificar/crear tabla de migraciones: {e}")
            raise MigrationError(f"Error al preparar la tabla de migraciones: {e}")
    
    def _load_migrations_from_dir(self) -> List[Migration]:
        """
        Carga las migraciones desde el directorio.
        
        Returns:
            List[Migration]: Lista de migraciones ordenadas por versión.
        """
        migrations = []
        
        # Buscar archivos de migración
        migration_files = []
        for extension in ['*.sql', '*.json']:
            migration_files.extend(list(self.migrations_dir.glob(extension)))
        
        for file_path in migration_files:
            try:
                if file_path.suffix == '.sql':
                    # Parsear migración SQL
                    migration = self._parse_sql_migration(file_path)
                elif file_path.suffix == '.json':
                    # Parsear migración JSON
                    migration = self._parse_json_migration(file_path)
                else:
                    continue
                
                if migration:
                    migrations.append(migration)
            except Exception as e:
                logger.warning(f"Error al cargar migración {file_path}: {e}")
        
        # Ordenar por versión
        migrations.sort(key=lambda m: m.version)
        return migrations
    
    def _parse_sql_migration(self, file_path: Path) -> Optional[Migration]:
        """
        Parsea un archivo SQL de migración.
        
        Args:
            file_path (Path): Ruta del archivo SQL.
            
        Returns:
            Optional[Migration]: Objeto Migration si se parseó correctamente, None en caso contrario.
        """
        # Extraer versión y nombre del nombre del archivo
        # Formato esperado: V[version]__[nombre].sql (ej: V20230101120000__create_users_table.sql)
        match = re.match(r'V(\d+)__(.+)\.sql$', file_path.name)
        if not match:
            logger.warning(f"Nombre de archivo de migración inválido: {file_path.name}")
            return None
        
        version, name = match.groups()
        name = name.replace('_', ' ').title()
        
        # Leer contenido
        content = file_path.read_text(encoding='utf-8')
        
        # Separar las secciones "up" y "down"
        up_sql = ""
        down_sql = ""
        
        # Buscar la sección "-- Up"
        up_match = re.search(r'-- Up\s+(.*?)(?:-- Down|$)', content, re.DOTALL)
        if up_match:
            up_sql = up_match.group(1).strip()
        
        # Buscar la sección "-- Down"
        down_match = re.search(r'-- Down\s+(.*?)$', content, re.DOTALL)
        if down_match:
            down_sql = down_match.group(1).strip()
        
        return Migration(version, name, up_sql, down_sql)
    
    def _parse_json_migration(self, file_path: Path) -> Optional[Migration]:
        """
        Parsea un archivo JSON de migración.
        
        Args:
            file_path (Path): Ruta del archivo JSON.
            
        Returns:
            Optional[Migration]: Objeto Migration si se parseó correctamente, None en caso contrario.
        """
        try:
            data = json.loads(file_path.read_text(encoding='utf-8'))
            
            # Verificar campos requeridos
            required_fields = ['version', 'name', 'up_sql']
            if not all(field in data for field in required_fields):
                logger.warning(f"Archivo JSON de migración incompleto: {file_path.name}")
                return None
            
            # Crear objeto Migration
            return Migration(
                version=data['version'],
                name=data['name'],
                up_sql=data['up_sql'],
                down_sql=data.get('down_sql'),
                description=data.get('description', '')
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Error al decodificar JSON de migración {file_path.name}: {e}")
            return None
    
    async def get_applied_migrations_async(self) -> List[Dict[str, Any]]:
        """
        Obtiene las migraciones aplicadas desde la base de datos (versión asíncrona).
        
        Returns:
            List[Dict[str, Any]]: Lista de migraciones aplicadas.
        """
        await self._ensure_migrations_table_async()
        
        try:
            result = await self.db_toolkit.fetch_records(
                self.table_name,
                order_by=[("applied_at", "ASC")]
            )
            return result.to_dict('records') if not result.empty else []
        except Exception as e:
            logger.error(f"Error al obtener migraciones aplicadas: {e}")
            raise MigrationError(f"Error al consultar migraciones aplicadas: {e}")
    
    def get_applied_migrations_sync(self) -> List[Dict[str, Any]]:
        """
        Obtiene las migraciones aplicadas desde la base de datos (versión sincrónica).
        
        Returns:
            List[Dict[str, Any]]: Lista de migraciones aplicadas.
        """
        self._ensure_migrations_table_sync()
        
        try:
            result = self.db_toolkit.fetch_records(
                self.table_name,
                order_by=[("applied_at", "ASC")]
            )
            return result.to_dict('records') if not result.empty else []
        except Exception as e:
            logger.error(f"Error al obtener migraciones aplicadas: {e}")
            raise MigrationError(f"Error al consultar migraciones aplicadas: {e}")
    
    async def apply_migrations_async(self, target_version: str = None) -> List[Migration]:
        """
        Aplica las migraciones pendientes (versión asíncrona).
        
        Args:
            target_version (str, opcional): Versión objetivo hasta la cual aplicar.
                Si no se especifica, se aplican todas las pendientes.
                
        Returns:
            List[Migration]: Lista de migraciones aplicadas.
        """
        # Obtener migraciones disponibles
        available_migrations = self._load_migrations_from_dir()
        
        # Obtener migraciones ya aplicadas
        applied_migrations = await self.get_applied_migrations_async()
        applied_versions = {m['version'] for m in applied_migrations}
        
        # Determinar migraciones pendientes
        pending_migrations = [m for m in available_migrations if m.version not in applied_versions]
        
        # Si hay una versión objetivo, filtrar migraciones
        if target_version:
            pending_migrations = [m for m in pending_migrations if m.version <= target_version]
        
        # Si no hay migraciones pendientes, terminar
        if not pending_migrations:
            logger.info("No hay migraciones pendientes para aplicar")
            return []
        
        # Aplicar migraciones pendientes
        applied = []
        for migration in pending_migrations:
            try:
                logger.info(f"Aplicando migración {migration}")
                
                # Ejecutar SQL de migración
                await self.db_toolkit.execute_query(migration.up_sql)
                
                # Registrar migración como aplicada
                await self.db_toolkit.insert_records(self.table_name, {
                    "version": migration.version,
                    "name": migration.name,
                    "description": migration.description
                })
                
                applied.append(migration)
                logger.info(f"Migración {migration.version} aplicada correctamente")
            except Exception as e:
                logger.error(f"Error al aplicar migración {migration.version}: {e}")
                raise MigrationError(f"Error al aplicar migración {migration.version}: {e}")
        
        return applied
    
    def apply_migrations_sync(self, target_version: str = None) -> List[Migration]:
        """
        Aplica las migraciones pendientes (versión sincrónica).
        
        Args:
            target_version (str, opcional): Versión objetivo hasta la cual aplicar.
                Si no se especifica, se aplican todas las pendientes.
                
        Returns:
            List[Migration]: Lista de migraciones aplicadas.
        """
        # Obtener migraciones disponibles
        available_migrations = self._load_migrations_from_dir()
        
        # Obtener migraciones ya aplicadas
        applied_migrations = self.get_applied_migrations_sync()
        applied_versions = {m['version'] for m in applied_migrations}
        
        # Determinar migraciones pendientes
        pending_migrations = [m for m in available_migrations if m.version not in applied_versions]
        
        # Si hay una versión objetivo, filtrar migraciones
        if target_version:
            pending_migrations = [m for m in pending_migrations if m.version <= target_version]
        
        # Si no hay migraciones pendientes, terminar
        if not pending_migrations:
            logger.info("No hay migraciones pendientes para aplicar")
            return []
        
        # Aplicar migraciones pendientes
        applied = []
        for migration in pending_migrations:
            try:
                logger.info(f"Aplicando migración {migration}")
                
                # Ejecutar SQL de migración
                self.db_toolkit.execute_query(migration.up_sql)
                
                # Registrar migración como aplicada
                self.db_toolkit.insert_records(self.table_name, {
                    "version": migration.version,
                    "name": migration.name,
                    "description": migration.description
                })
                
                applied.append(migration)
                logger.info(f"Migración {migration.version} aplicada correctamente")
            except Exception as e:
                logger.error(f"Error al aplicar migración {migration.version}: {e}")
                raise MigrationError(f"Error al aplicar migración {migration.version}: {e}")
        
        return applied
    
    async def rollback_migrations_async(self, steps: int = 1) -> List[Migration]:
        """
        Revierte las últimas migraciones aplicadas (versión asíncrona).
        
        Args:
            steps (int): Número de migraciones a revertir.
                
        Returns:
            List[Migration]: Lista de migraciones revertidas.
        """
        # Obtener migraciones disponibles
        available_migrations = self._load_migrations_from_dir()
        migration_map = {m.version: m for m in available_migrations}
        
        # Obtener migraciones aplicadas (ordenadas por aplicación)
        applied_migrations = await self.get_applied_migrations_async()
        
        # Si no hay migraciones aplicadas, terminar
        if not applied_migrations:
            logger.info("No hay migraciones para revertir")
            return []
        
        # Limitar el número de pasos
        steps = min(steps, len(applied_migrations))
        
        # Obtener las migraciones a revertir (las últimas aplicadas)
        to_rollback = applied_migrations[-steps:]
        to_rollback.reverse()  # Revertir en orden inverso
        
        # Revertir migraciones
        reverted = []
        for migration_record in to_rollback:
            version = migration_record['version']
            
            # Verificar si tenemos el SQL para revertir
            if version not in migration_map or not migration_map[version].down_sql:
                logger.warning(f"No se puede revertir migración {version}: SQL de reversión no disponible")
                continue
            
            try:
                migration = migration_map[version]
                logger.info(f"Revirtiendo migración {version}")
                
                # Ejecutar SQL de reversión
                await self.db_toolkit.execute_query(migration.down_sql)
                
                # Eliminar registro de migración
                await self.db_toolkit.delete_records(
                    self.table_name,
                    conditions={"version": version}
                )
                
                reverted.append(migration)
                logger.info(f"Migración {version} revertida correctamente")
            except Exception as e:
                logger.error(f"Error al revertir migración {version}: {e}")
                raise MigrationError(f"Error al revertir migración {version}: {e}")
        
        return reverted
    
    def rollback_migrations_sync(self, steps: int = 1) -> List[Migration]:
        """
        Revierte las últimas migraciones aplicadas (versión sincrónica).
        
        Args:
            steps (int): Número de migraciones a revertir.
                
        Returns:
            List[Migration]: Lista de migraciones revertidas.
        """
        # Obtener migraciones disponibles
        available_migrations = self._load_migrations_from_dir()
        migration_map = {m.version: m for m in available_migrations}
        
        # Obtener migraciones aplicadas (ordenadas por aplicación)
        applied_migrations = self.get_applied_migrations_sync()
        
        # Si no hay migraciones aplicadas, terminar
        if not applied_migrations:
            logger.info("No hay migraciones para revertir")
            return []
        
        # Limitar el número de pasos
        steps = min(steps, len(applied_migrations))
        
        # Obtener las migraciones a revertir (las últimas aplicadas)
        to_rollback = applied_migrations[-steps:]
        to_rollback.reverse()  # Revertir en orden inverso
        
        # Revertir migraciones
        reverted = []
        for migration_record in to_rollback:
            version = migration_record['version']
            
            # Verificar si tenemos el SQL para revertir
            if version not in migration_map or not migration_map[version].down_sql:
                logger.warning(f"No se puede revertir migración {version}: SQL de reversión no disponible")
                continue
            
            try:
                migration = migration_map[version]
                logger.info(f"Revirtiendo migración {version}")
                
                # Ejecutar SQL de reversión
                self.db_toolkit.execute_query(migration.down_sql)
                
                # Eliminar registro de migración
                self.db_toolkit.delete_records(
                    self.table_name,
                    conditions={"version": version}
                )
                
                reverted.append(migration)
                logger.info(f"Migración {version} revertida correctamente")
            except Exception as e:
                logger.error(f"Error al revertir migración {version}: {e}")
                raise MigrationError(f"Error al revertir migración {version}: {e}")
        
        return reverted
        
    def create_migration(self, name: str, up_sql: str, down_sql: str = None) -> Migration:
        """
        Crea un nuevo archivo de migración.
        
        Args:
            name (str): Nombre descriptivo de la migración.
            up_sql (str): SQL para aplicar la migración.
            down_sql (str, opcional): SQL para revertir la migración.
            
        Returns:
            Migration: Objeto Migration creado.
        """
        # Generar versión basada en timestamp
        version = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Sanitizar nombre para el archivo
        file_name = name.lower().replace(' ', '_')
        
        # Crear nombre de archivo
        file_path = self.migrations_dir / f"V{version}__{file_name}.sql"
        
        # Crear contenido
        content = f"-- Up\n{up_sql}\n\n"
        if down_sql:
            content += f"-- Down\n{down_sql}\n"
        
        # Escribir archivo
        file_path.write_text(content, encoding='utf-8')
        logger.info(f"Archivo de migración creado: {file_path}")
        
        # Crear y retornar objeto Migration
        return Migration(version, name, up_sql, down_sql)

    def generate_migration_from_schema_diff(self, target_schema: Dict[str, Dict[str, str]], prefix: str = "update") -> Optional[Migration]:
        """
        Genera una migración a partir de la diferencia entre el esquema actual y el objetivo.
        
        Args:
            target_schema (Dict[str, Dict[str, str]]): Esquema objetivo. 
                Formato: {"tabla1": {"columna1": "tipo1", ...}, ...}
            prefix (str, opcional): Prefijo para el nombre de la migración.
                
        Returns:
            Optional[Migration]: Migración generada o None si no hay diferencias.
        """
        up_statements = []
        down_statements = []
        
        try:
            # Obtener tablas actuales
            current_tables = self.db_toolkit.get_tables()
            
            # Procesar cada tabla en el esquema objetivo
            for table_name, columns in target_schema.items():
                if table_name not in current_tables:
                    # Crear tabla si no existe
                    up_statements.append(f"CREATE TABLE {table_name} (")
                    column_defs = []
                    for col_name, col_type in columns.items():
                        column_defs.append(f"    {col_name} {col_type}")
                    up_statements.append(",\n".join(column_defs))
                    up_statements.append(");")
                    
                    # SQL para revertir
                    down_statements.append(f"DROP TABLE IF EXISTS {table_name};")
                else:
                    # Obtener información de la tabla actual
                    table_info = self.db_toolkit.get_table_info(table_name)
                    current_columns = {row['column_name']: row['data_type'] for _, row in table_info.iterrows()}
                    
                    # Verificar si hay columnas que añadir o modificar
                    for col_name, col_type in columns.items():
                        if col_name not in current_columns:
                            # Añadir columna
                            up_statements.append(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type};")
                            down_statements.append(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {col_name};")
                        elif current_columns[col_name].lower() != col_type.lower():
                            # Modificar tipo de columna (si es posible)
                            up_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {col_type} USING {col_name}::{col_type};")
                            down_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {current_columns[col_name]};")
            
            # Si no hay cambios, retornar None
            if not up_statements:
                logger.info("No se detectaron diferencias en el esquema")
                return None
            
            # Crear migración
            name = f"{prefix}_schema_{datetime.now().strftime('%Y%m%d')}"
            up_sql = "\n".join(up_statements)
            down_sql = "\n".join(reversed(down_statements))
            
            return self.create_migration(name, up_sql, down_sql)
            
        except Exception as e:
            logger.error(f"Error al generar migración desde diferencia de esquema: {e}")
            raise MigrationError(f"Error al generar migración: {e}")