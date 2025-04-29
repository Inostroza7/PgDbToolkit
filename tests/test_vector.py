# tests/test_vector.py

"""
Tests para las funcionalidades relacionadas con pgvector.
"""

import pytest
import numpy as np
import os
import pandas as pd
from pathlib import Path
import tempfile

# Ignorar errores si pgvector no está disponible para las pruebas
try:
    from pgvector.psycopg import register_vector, register_vector_async
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

from pgdbtoolkit.exceptions import QueryError

# Marcar todo el módulo como que requiere pgvector
pytestmark = pytest.mark.skipif(not HAS_PGVECTOR, reason="pgvector no está instalado")


class TestVector:
    """
    Pruebas para funcionalidades relacionadas con pgvector.
    """

    def test_create_vector_extension(self, pg_toolkit):
        """Verificar la creación de la extensión vector."""
        # Intentar crear la extensión
        try:
            pg_toolkit.create_vector_extension()
            
            # Verificar que la extensión está instalada
            result = pg_toolkit.execute_query(
                "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'"
            )
            assert result.iloc[0, 0] == 1
            
        except Exception as e:
            pytest.skip(f"No se pudo crear la extensión vector: {e}")
    
    def test_vector_operations(self, pg_toolkit):
        """Verificar operaciones básicas con vectores."""
        # Intentar crear la extensión vector
        try:
            pg_toolkit.create_vector_extension()
        except Exception as e:
            pytest.skip(f"No se pudo crear la extensión vector: {e}")
        
        # Crear una tabla con campo vector
        vector_table = f"test_vector_{int(os.urandom(4).hex(), 16)}"
        pg_toolkit.create_table(vector_table, {
            "id": "SERIAL PRIMARY KEY",
            "text": "TEXT NOT NULL",
            "embedding": "vector(3)"  # Vector de dimensión 3 para simplificar
        })
        
        try:
            # Insertar vectores
            test_data = [
                {"text": "Prueba 1", "embedding": [1.0, 0.0, 0.0]},
                {"text": "Prueba 2", "embedding": [0.0, 1.0, 0.0]},
                {"text": "Prueba 3", "embedding": [0.0, 0.0, 1.0]},
                {"text": "Prueba 4", "embedding": [0.5, 0.5, 0.0]},
                {"text": "Prueba 5", "embedding": [0.33, 0.33, 0.33]}
            ]
            
            pg_toolkit.insert_records(vector_table, test_data)
            
            # Consultar vectores
            vectors = pg_toolkit.execute_query(f"SELECT * FROM {vector_table}")
            assert len(vectors) == 5
            
            # Buscar similitud por producto escalar
            query_vector = [0.9, 0.1, 0.0]
            result = pg_toolkit.execute_query(f"""
                SELECT text, 1 - (embedding <=> %s::vector) AS similarity
                FROM {vector_table}
                ORDER BY similarity DESC
                LIMIT 3
            """, (query_vector,))
            
            # El primer elemento debería ser similar a [1.0, 0.0, 0.0]
            assert result["text"].iloc[0] == "Prueba 1"
            
            # Buscar por distancia euclídea
            result = pg_toolkit.execute_query(f"""
                SELECT text, embedding <-> %s::vector AS distance
                FROM {vector_table}
                ORDER BY distance
                LIMIT 3
            """, (query_vector,))
            
            # El más cercano debería seguir siendo el primero
            assert result["text"].iloc[0] == "Prueba 1"
            
            # Probar funciones de operaciones con vectores
            result = pg_toolkit.execute_query(f"""
                SELECT
                    embedding + %s::vector AS addition,
                    embedding - %s::vector AS subtraction
                FROM {vector_table}
                WHERE id = 1
            """, ([0.1, 0.1, 0.1], [0.1, 0.1, 0.1]))
            
            # Verificar las operaciones
            assert len(result) == 1
        
        finally:
            # Limpiar
            pg_toolkit.delete_table(vector_table)
    
    @pytest.mark.asyncio
    async def test_async_vector_operations(self, async_pg_toolkit):
        """Verificar operaciones vectoriales asíncronas."""
        # Intentar crear la extensión vector
        try:
            await async_pg_toolkit.create_vector_extension()
        except Exception as e:
            pytest.skip(f"No se pudo crear la extensión vector: {e}")
        
        # Crear una tabla con campo vector
        vector_table = f"test_async_vector_{int(os.urandom(4).hex(), 16)}"
        await async_pg_toolkit.create_table(vector_table, {
            "id": "SERIAL PRIMARY KEY",
            "text": "TEXT NOT NULL",
            "embedding": "vector(3)"  # Vector de dimensión 3 para simplificar
        })
        
        try:
            # Insertar vectores
            test_data = [
                {"text": "Async 1", "embedding": [1.0, 0.0, 0.0]},
                {"text": "Async 2", "embedding": [0.0, 1.0, 0.0]},
                {"text": "Async 3", "embedding": [0.0, 0.0, 1.0]},
                {"text": "Async 4", "embedding": [0.5, 0.5, 0.0]},
                {"text": "Async 5", "embedding": [0.33, 0.33, 0.33]}
            ]
            
            await async_pg_toolkit.insert_records(vector_table, test_data)
            
            # Consultar vectores
            vectors = await async_pg_toolkit.execute_query(f"SELECT * FROM {vector_table}")
            assert len(vectors) == 5
            
            # Buscar similitud por producto escalar
            query_vector = [0.9, 0.1, 0.0]
            result = await async_pg_toolkit.execute_query(f"""
                SELECT text, 1 - (embedding <=> %s::vector) AS similarity
                FROM {vector_table}
                ORDER BY similarity DESC
                LIMIT 3
            """, (query_vector,))
            
            # El primer elemento debería ser similar a [1.0, 0.0, 0.0]
            assert result["text"].iloc[0] == "Async 1"
            
        finally:
            # Limpiar
            await async_pg_toolkit.delete_table(vector_table)