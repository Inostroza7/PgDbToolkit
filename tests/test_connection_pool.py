# tests/test_connection_pool.py

"""
Tests para los pools de conexiones sincrónicas y asíncronas.
"""

import pytest
import asyncio
import pandas as pd
import concurrent.futures
from datetime import datetime

from pgdbtoolkit import PgConnectionPool, PgAsyncConnectionPool
from pgdbtoolkit.exceptions import PoolError


class TestConnectionPool:
    """
    Pruebas para el pool de conexiones sincrónicas.
    """

    def test_basic_pool_operations(self, connection_pool, pg_toolkit):
        """Verificar operaciones básicas del pool."""
        # Crear una tabla para probar el pool
        test_table = f"test_pool_{int(datetime.now().timestamp())}"
        pg_toolkit.create_table(test_table, {
            "id": "SERIAL PRIMARY KEY",
            "data": "TEXT"
        })
        
        try:
            # Obtener una conexión del pool
            with connection_pool.connection() as conn:
                # Verificar que la conexión funciona
                with conn.cursor() as cur:
                    cur.execute(f"INSERT INTO {test_table} (data) VALUES (%s) RETURNING id", ("test data",))
                    result = cur.fetchone()[0]
                    assert result == 1
            
            # Obtener las estadísticas del pool
            stats = connection_pool.stats()
            assert "pool_min" in stats
            assert "pool_max" in stats
            assert stats["pool_min"] == 1
            assert stats["pool_max"] == 3
            
            # Usar múltiples conexiones simultáneamente
            def worker(i):
                with connection_pool.connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(f"INSERT INTO {test_table} (data) VALUES (%s) RETURNING id", (f"worker {i}",))
                        return cur.fetchone()[0]
            
            # Usar un ThreadPoolExecutor para simular múltiples clientes
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(worker, i) for i in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # Verificar que se insertaron todos los registros
            with connection_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT COUNT(*) FROM {test_table}")
                    count = cur.fetchone()[0]
                    assert count == 11  # 1 inicial + 10 de los workers
        
        finally:
            # Limpiar
            pg_toolkit.delete_table(test_table)
    
    def test_pool_error_handling(self, pg_toolkit):
        """Verificar el manejo de errores del pool."""
        # Intentar crear un pool con configuración inválida
        invalid_config = {
            "host": "nonexistent-host",
            "port": 5432,
            "dbname": "nonexistent-db",
            "user": "invalid",
            "password": "invalid"
        }
        
        # La creación del pool no debe fallar, pero la conexión sí
        pool = PgConnectionPool(invalid_config, min_size=1, max_size=2)
        
        # Intentar obtener una conexión debe fallar
        with pytest.raises(Exception):
            with pool.connection() as conn:
                pass
        
        # Intentar esperar conexiones debe fallar
        with pytest.raises(Exception):
            pool.wait(timeout=1.0)
        
        # El pool debe poder cerrarse aún después de errores
        pool.close()
    
    def test_pool_resize(self, connection_pool):
        """Verificar que el pool puede cambiar de tamaño."""
        # Obtener estadísticas iniciales
        initial_stats = connection_pool.stats()
        assert initial_stats["pool_min"] == 1
        assert initial_stats["pool_max"] == 3
        
        # Cambiar el tamaño del pool
        connection_pool.resize(min_size=2, max_size=5)
        
        # Verificar que el tamaño cambió
        new_stats = connection_pool.stats()
        assert new_stats["pool_min"] == 2
        assert new_stats["pool_max"] == 5
    
    def test_pool_with_statements(self, connection_pool, pg_toolkit):
        """Verificar el uso del pool con bloques with anidados."""
        # Crear una tabla para probar el pool
        test_table = f"test_pool_statements_{int(datetime.now().timestamp())}"
        pg_toolkit.create_table(test_table, {
            "id": "SERIAL PRIMARY KEY",
            "name": "TEXT",
            "value": "INTEGER"
        })
        
        try:
            # Usar un bloque with para el pool (aunque ya está abierto por el fixture)
            with connection_pool:
                # Usar varios bloques with anidados para conexiones
                with connection_pool.connection() as conn1:
                    with conn1.cursor() as cur1:
                        cur1.execute(f"INSERT INTO {test_table} (name, value) VALUES (%s, %s)", ("test1", 100))
                    
                    # Anidar otra conexión
                    with connection_pool.connection() as conn2:
                        with conn2.cursor() as cur2:
                            cur2.execute(f"INSERT INTO {test_table} (name, value) VALUES (%s, %s)", ("test2", 200))
                            
                            # Verificar que ambas inserciones son visibles
                            cur2.execute(f"SELECT COUNT(*) FROM {test_table}")
                            count = cur2.fetchone()[0]
                            assert count == 2
                
                    # Verificar que las conexiones se liberaron correctamente
                    stats = connection_pool.stats()
                    assert stats["pool_available"] >= 1  # Al menos una conexión disponible
        
        finally:
            # Limpiar
            pg_toolkit.delete_table(test_table)


class TestAsyncConnectionPool:
    """
    Pruebas para el pool de conexiones asíncronas.
    """

    @pytest.mark.asyncio
    async def test_basic_async_pool_operations(self, async_connection_pool, async_pg_toolkit):
        """Verificar operaciones básicas del pool asíncrono."""
        # Crear una tabla para probar el pool
        test_table = f"test_async_pool_{int(datetime.now().timestamp())}"
        
        # Añadir logs para diagnóstico
        print(f"Nombre de la tabla de prueba: {test_table}")
        print(f"Configuración de async_pg_toolkit: {async_pg_toolkit.db_config}")
        print(f"Configuración de async_connection_pool: {async_connection_pool.conn_params}")
        
        await async_pg_toolkit.create_table(test_table, {
            "id": "SERIAL PRIMARY KEY",
            "data": "TEXT"
        })
        
        try:
            # Consultar la lista de tablas para verificar
            tables = await async_pg_toolkit.get_tables()
            print(f"Tablas en la base de datos: {tables}")
            
            # Esperar un momento para asegurarse de que la tabla esté visible
            await asyncio.sleep(0.5)
            
            # Obtener una conexión del pool
            async with async_connection_pool.connection() as conn:
                # Verificar que la tabla existe antes de intentar operaciones
                async with conn.cursor() as cur:
                    await cur.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)", (test_table,))
                    exists = (await cur.fetchone())[0]
                    assert exists, f"La tabla {test_table} no existe según la consulta de information_schema"
                    
                    await cur.execute(f"INSERT INTO {test_table} (data) VALUES (%s) RETURNING id", ("test data",))
                    result = (await cur.fetchone())[0]
                    assert result == 1
            
                # Verificar las estadísticas del pool
                stats = await async_connection_pool.stats()
                assert "pool_min" in stats
                assert "pool_max" in stats
                assert stats["pool_min"] == 1
                assert stats["pool_max"] == 3
            
                # Usar múltiples conexiones simultáneamente
                async def worker(i):
                    async with async_connection_pool.connection() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(f"INSERT INTO {test_table} (data) VALUES (%s) RETURNING id", (f"worker {i}",))
                            return (await cur.fetchone())[0]
            
                # Crear varias tareas concurrentes
                tasks = [asyncio.create_task(worker(i)) for i in range(10)]
                results = await asyncio.gather(*tasks)
            
                # Verificar que se insertaron todos los registros
                async with async_connection_pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(f"SELECT COUNT(*) FROM {test_table}")
                        count = (await cur.fetchone())[0]
                        assert count == 11  # 1 inicial + 10 de los workers
        
        finally:
            # Limpiar
            await async_pg_toolkit.delete_table(test_table)
    
    @pytest.mark.asyncio
    async def test_async_pool_error_handling(self, async_pg_toolkit):
        """Verificar el manejo de errores del pool asíncrono."""
        # Intentar crear un pool con configuración inválida
        invalid_config = {
            "host": "nonexistent-host",
            "port": 5432,
            "dbname": "nonexistent-db",
            "user": "invalid",
            "password": "invalid"
        }
        
        # Crear el pool sin abrirlo
        pool = PgAsyncConnectionPool(invalid_config, min_size=1, max_size=2)
        
        # Abrir el pool debe fallar
        with pytest.raises(Exception):
            await pool.open()
        
        # Obtener una conexión debe fallar
        with pytest.raises(Exception):
            async with pool.connection() as conn:
                pass
        
        # El pool debe poder cerrarse aún después de errores
        await pool.close()
    
    @pytest.mark.asyncio
    async def test_async_pool_with_statements(self, async_connection_pool, async_pg_toolkit):
        """Verificar el uso del pool asíncrono con bloques with anidados."""
        # Crear una tabla para probar el pool
        test_table = f"test_async_pool_statements_{int(datetime.now().timestamp())}"
        await async_pg_toolkit.create_table(test_table, {
            "id": "SERIAL PRIMARY KEY",
            "name": "TEXT",
            "value": "INTEGER"
        })
        
        try:
            # Usar un bloque with para el pool (aunque ya está abierto por el fixture)
            async with async_connection_pool:
                # Usar varios bloques with anidados para conexiones
                async with async_connection_pool.connection() as conn1:
                    async with conn1.cursor() as cur1:
                        await cur1.execute(f"INSERT INTO {test_table} (name, value) VALUES (%s, %s)", ("test1", 100))
                    
                    # Anidar otra conexión
                    async with async_connection_pool.connection() as conn2:
                        async with conn2.cursor() as cur2:
                            await cur2.execute(f"INSERT INTO {test_table} (name, value) VALUES (%s, %s)", ("test2", 200))
                            
                            # Verificar que ambas inserciones son visibles
                            await cur2.execute(f"SELECT COUNT(*) FROM {test_table}")
                            count = (await cur2.fetchone())[0]
                            assert count == 2
                
                    # Verificar que las conexiones se liberaron correctamente
                    stats = await async_connection_pool.stats()
                    assert stats["pool_available"] >= 1  # Al menos una conexión disponible
        
        finally:
            # Limpiar
            await async_pg_toolkit.delete_table(test_table)
    
    @pytest.mark.asyncio
    async def test_async_connection_stress(self, async_connection_pool, async_pg_toolkit):
        """Prueba de estrés para conexiones asíncronas."""
        # Crear una tabla para la prueba de estrés
        stress_table = f"test_async_stress_{int(datetime.now().timestamp())}"
        await async_pg_toolkit.create_table(stress_table, {
            "id": "SERIAL PRIMARY KEY",
            "worker_id": "INTEGER",
            "iteration": "INTEGER",
            "timestamp": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        })
        
        try:
            # Simular muchas operaciones concurrentes
            async def stress_worker(worker_id, iterations):
                for i in range(iterations):
                    try:
                        async with async_connection_pool.connection() as conn:
                            async with conn.cursor() as cur:
                                await cur.execute(
                                    f"INSERT INTO {stress_table} (worker_id, iteration) VALUES (%s, %s)",
                                    (worker_id, i)
                                )
                                await asyncio.sleep(0.01)  # Pequeña pausa para simular trabajo
                    except Exception as e:
                        print(f"Error en worker {worker_id}, iteración {i}: {e}")
                        raise
            
            # Ejecutar varios workers concurrentes
            worker_count = 10
            iterations = 5
            tasks = [asyncio.create_task(stress_worker(i, iterations)) for i in range(worker_count)]
            await asyncio.gather(*tasks)
            
            # Verificar resultados
            async with async_connection_pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(f"SELECT COUNT(*) FROM {stress_table}")
                    count = (await cur.fetchone())[0]
                    assert count == worker_count * iterations
            
            # Verificar estadísticas del pool
            stats = await async_connection_pool.stats()
            print(f"Pool stats after stress test: {stats}")
            assert "connections_num" in stats
            assert stats["connections_num"] > 0
        
        finally:
            # Limpiar
            await async_pg_toolkit.delete_table(stress_table)