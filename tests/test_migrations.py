# tests/test_migrations.py

"""
Tests para el sistema de migraciones.
"""

import pytest
import os
import json
from pathlib import Path
from datetime import datetime
import time

from pgdbtoolkit import MigrationManager, Migration
from pgdbtoolkit.exceptions import MigrationError


class TestMigrations:
    """
    Pruebas para el sistema de migraciones.
    """

    def test_migration_creation(self, migration_manager, migrations_dir):
        """Verificar la creación de migraciones."""
        # Crear una migración
        migration = migration_manager.create_migration(
            name="create_test_table",
            up_sql="""
            CREATE TABLE test_migration_table (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            down_sql="""
            DROP TABLE IF EXISTS test_migration_table;
            """
        )
        
        # Verificar que el objeto Migration se creó correctamente
        assert isinstance(migration, Migration)
        assert "create_test_table" in migration.name
        
        # Verificar que se creó el archivo de migración
        migration_files = list(Path(migrations_dir).glob("*.sql"))
        assert len(migration_files) == 1
        
        # Verificar contenido del archivo
        content = migration_files[0].read_text()
        assert "-- Up" in content
        assert "CREATE TABLE test_migration_table" in content
        assert "-- Down" in content
        assert "DROP TABLE IF EXISTS test_migration_table" in content
    
    def test_apply_migrations_sync(self, migration_manager, pg_toolkit, migrations_dir):
        """Verificar la aplicación de migraciones en modo sincrónico."""
        # Crear migración para tabla users
        migration1 = migration_manager.create_migration(
            name="create_users_table",
            up_sql="""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                email VARCHAR(255) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            down_sql="""
            DROP TABLE IF EXISTS users;
            """
        )
        
        # Esperar al menos 2 segundos para asegurar timestamp diferente
        time.sleep(2)
        
        # Crear migración para tabla posts que depende de users
        migration2 = migration_manager.create_migration(
            name="create_posts_table",
            up_sql="""
            CREATE TABLE posts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                title VARCHAR(200) NOT NULL,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            down_sql="""
            DROP TABLE IF EXISTS posts;
            """
        )
        
        # Verificar que las migraciones tienen versiones diferentes
        assert migration1.version != migration2.version
        
        # Aplicar migraciones
        applied_migrations = migration_manager.apply_migrations_sync()
        
        # Verificar que se aplicaron ambas migraciones
        assert len(applied_migrations) == 2
        
        # Verificar que las tablas existen
        tables = pg_toolkit.get_tables()
        assert "users" in tables
        assert "posts" in tables
        
        # Verificar que las migraciones están registradas en la tabla migrations
        applied_records = migration_manager.get_applied_migrations_sync()
        assert len(applied_records) == 2
        assert "Create Users Table" in [record["name"] for record in applied_records]
        assert "Create Posts Table" in [record["name"] for record in applied_records]
        
        # Intentar aplicar migraciones de nuevo (no debería hacer nada)
        new_applied = migration_manager.apply_migrations_sync()
        assert len(new_applied) == 0
        
        # Crear una migración adicional
        time.sleep(2)
        
        migration3 = migration_manager.create_migration(
            name="add_comments_table",
            up_sql="""
            CREATE TABLE comments (
                id SERIAL PRIMARY KEY,
                post_id INTEGER REFERENCES posts(id),
                user_id INTEGER REFERENCES users(id),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            down_sql="""
            DROP TABLE IF EXISTS comments;
            """
        )
        
        # Verificar que tiene una versión diferente
        assert migration3.version != migration2.version
        
        # Aplicar solo la nueva migración
        latest_applied = migration_manager.apply_migrations_sync()
        assert len(latest_applied) == 1
        assert "Add Comments Table" in latest_applied[0].name
        
        # Verificar que la nueva tabla existe
        tables = pg_toolkit.get_tables()
        assert "comments" in tables
    
    def test_rollback_migrations_sync(self, migration_manager, pg_toolkit, migrations_dir):
        """Verificar el rollback de migraciones en modo sincrónico."""
        # Crear y aplicar migraciones
        migration_manager.create_migration(
            name="create_products_table",
            up_sql="""
            CREATE TABLE products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            down_sql="""
            DROP TABLE IF EXISTS products;
            """
        )
        
        # Esperar un momento para asegurar que la siguiente migración tenga un timestamp diferente
        time.sleep(2)
        
        migration_manager.create_migration(
            name="create_product_categories_table",
            up_sql="""
            CREATE TABLE product_categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            down_sql="""
            DROP TABLE IF EXISTS product_categories;
            """
        )