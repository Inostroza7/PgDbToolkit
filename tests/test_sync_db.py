# tests/test_sync_db.py

"""
Tests para la versión sincrónica de PgDbToolkit.
"""

import pytest
import pandas as pd
import os
from datetime import date
import tempfile
import numpy as np
import time
import random

from pgdbtoolkit import PgDbToolkit
from pgdbtoolkit.exceptions import QueryError


class TestPgDbToolkit:
    """
    Pruebas para la clase PgDbToolkit.
    """

    def test_initialization(self, pg_toolkit):
        """Verificar que el toolkit se inicializa correctamente."""
        assert isinstance(pg_toolkit, PgDbToolkit)
        assert pg_toolkit.db_config is not None
        assert pg_toolkit.db_config["dbname"] is not None

    def test_create_table(self, pg_toolkit):
        """Probar la creación de una tabla."""
        table_name = "test_create_table"
        schema = {
            "id": "SERIAL PRIMARY KEY",
            "name": "VARCHAR(100) NOT NULL",
            "description": "TEXT",
            "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        }
        
        # Verificar que la tabla no existe
        tables_before = pg_toolkit.get_tables()
        assert table_name not in tables_before
        
        # Crear la tabla
        pg_toolkit.create_table(table_name, schema)
        
        # Verificar que la tabla existe
        tables_after = pg_toolkit.get_tables()
        assert table_name in tables_after
        
        # Verificar estructura de la tabla
        table_info = pg_toolkit.get_table_info(table_name)
        assert not table_info.empty
        assert len(table_info) == 4  # 4 columnas
        assert "id" in table_info["column_name"].values
        assert "name" in table_info["column_name"].values
        assert "description" in table_info["column_name"].values
        assert "created_at" in table_info["column_name"].values
        
        # Limpiar
        pg_toolkit.delete_table(table_name)

    def test_insert_and_fetch_records(self, pg_toolkit, test_table, test_data):
        """Probar la inserción y recuperación de registros."""
        # Insertar registros
        ids = pg_toolkit.insert_records(test_table, test_data)
        
        # Verificar que se devolvieron IDs
        assert isinstance(ids, list)
        assert len(ids) == len(test_data)
        
        # Recuperar todos los registros
        all_records = pg_toolkit.fetch_records(test_table)
        assert not all_records.empty
        assert len(all_records) == len(test_data)
        
        # Recuperar con filtro
        active_records = pg_toolkit.fetch_records(test_table, conditions={"active": True})
        assert len(active_records) == 4  # 4 registros activos
        
        # Recuperar con condición avanzada
        high_value_records = pg_toolkit.fetch_records(
            test_table, 
            conditions={("value", ">"): 200}
        )
        assert len(high_value_records) == 3  # 3 registros con valor > 200
        
        # Recuperar con múltiples condiciones
        filtered_records = pg_toolkit.fetch_records(
            test_table,
            conditions={
                ("value", ">"): 200,
                "active": True
            }
        )
        assert len(filtered_records) == 2  # 2 registros con valor > 200 y activos
        
        # Recuperar con ordenamiento
        ordered_records = pg_toolkit.fetch_records(
            test_table,
            order_by=[("value", "DESC")]
        )
        assert ordered_records["value"].iloc[0] == 500  # El primer registro tiene valor 500
        assert ordered_records["value"].iloc[-1] == 100  # El último registro tiene valor 100
        
        # Recuperar con límite
        limited_records = pg_toolkit.fetch_records(
            test_table,
            limit=2
        )
        assert len(limited_records) == 2
        
        # Recuperar con offset
        offset_records = pg_toolkit.fetch_records(
            test_table,
            order_by=[("value", "ASC")],
            offset=2
        )
        assert len(offset_records) == 3
        assert offset_records["value"].iloc[0] == 300  # El primer registro después del offset tiene valor 300

    def test_update_records(self, pg_toolkit, test_table, test_data):
        """Probar la actualización de registros."""
        # Insertar registros
        pg_toolkit.insert_records(test_table, test_data)
        
        # Actualizar un solo registro
        pg_toolkit.update_records(
            test_table,
            {"name": "Updated Name", "value": 999},
            {"name": "Test 1"}
        )
        
        # Verificar actualización
        updated_record = pg_toolkit.fetch_records(
            test_table,
            conditions={"name": "Updated Name"}
        )
        assert len(updated_record) == 1
        assert updated_record["value"].iloc[0] == 999
        
        # Actualizar múltiples registros
        update_count = pg_toolkit.update_records(
            test_table,
            {"active": False},
            {("value", ">"): 300}
        )
        assert update_count == 3  # Se actualizaron 3 registros
        
        # Verificar actualización múltiple
        inactive_records = pg_toolkit.fetch_records(
            test_table,
            conditions={"active": False}
        )
        assert len(inactive_records) == 3
        
        # Actualizar con múltiples condiciones
        pg_toolkit.update_records(
            test_table,
            {"name": "Multiple Conditions"},
            {
                ("value", ">"): 300,
                "active": False
            }
        )
        
        # Verificar actualización con múltiples condiciones
        multi_condition_records = pg_toolkit.fetch_records(
            test_table,
            conditions={"name": "Multiple Conditions"}
        )
        assert len(multi_condition_records) == 3

    def test_delete_records(self, pg_toolkit, test_table, test_data):
        """Probar la eliminación de registros."""
        # Insertar registros
        pg_toolkit.insert_records(test_table, test_data)
        
        # Verificar que hay 5 registros
        all_records = pg_toolkit.fetch_records(test_table)
        assert len(all_records) == 5
        
        # Eliminar un registro
        deleted_count = pg_toolkit.delete_records(
            test_table,
            {"name": "Test 1"}
        )
        assert deleted_count == 1
        
        # Verificar que queda un registro menos
        remaining_records = pg_toolkit.fetch_records(test_table)
        assert len(remaining_records) == 4
        assert "Test 1" not in remaining_records["name"].values
        
        # Eliminar con condición avanzada
        deleted_count = pg_toolkit.delete_records(
            test_table,
            {("value", ">"): 300}
        )
        assert deleted_count == 2
        
        # Verificar eliminación con condición avanzada
        final_records = pg_toolkit.fetch_records(test_table)
        assert len(final_records) == 2
        assert all(value <= 300 for value in final_records["value"])
        
        # Eliminar con múltiples condiciones
        deleted_count = pg_toolkit.delete_records(
            test_table,
            {
                ("value", "="): 200,
                "active": True
            }
        )
        assert deleted_count == 1
        
        # Verificar eliminación con múltiples condiciones
        last_record = pg_toolkit.fetch_records(test_table)
        assert len(last_record) == 1
        assert last_record["name"].iloc[0] == "Test 3"

    def test_execute_query(self, pg_toolkit, test_table, test_data):
        """Probar la ejecución de consultas personalizadas."""
        # Insertar registros
        pg_toolkit.insert_records(test_table, test_data)
        
        # Ejecutar consulta simple
        result = pg_toolkit.execute_query(f"SELECT * FROM {test_table}")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
        
        # Ejecutar consulta con parámetros
        result = pg_toolkit.execute_query(
            f"SELECT * FROM {test_table} WHERE value > %s",
            (300,)
        )
        assert len(result) == 2
        
        # Ejecutar consulta de agregación
        result = pg_toolkit.execute_query(
            f"SELECT SUM(value) as total FROM {test_table}"
        )
        assert result["total"].iloc[0] == 1500  # Suma de 100+200+300+400+500
        
        # Ejecutar consulta con JOIN (crear tabla relacionada primero)
        related_table = f"{test_table}_related"
        pg_toolkit.create_table(related_table, {
            "id": "SERIAL PRIMARY KEY",
            "test_id": f"INTEGER REFERENCES {test_table}(id)",
            "info": "TEXT"
        })
        
        # Insertar datos relacionados
        pg_toolkit.insert_records(related_table, [
            {"test_id": 1, "info": "Related to Test 1"},
            {"test_id": 2, "info": "Related to Test 2"}
        ])
        
        # Ejecutar JOIN
        join_result = pg_toolkit.execute_query(f"""
            SELECT t.name, r.info 
            FROM {test_table} t
            JOIN {related_table} r ON t.id = r.test_id
        """)
        
        assert len(join_result) == 2
        assert "Related to Test 1" in join_result["info"].values
        
        # Limpiar
        pg_toolkit.delete_table(related_table)

    def test_batch_operation(self, pg_toolkit, test_table):
        """Probar operaciones por lotes."""
        # Crear registros en lote
        batch_size = 50
        test_batch = [{"name": f"Batch Item {i}", "value": i} for i in range(200)]
        
        # Insertar en lotes
        ids = pg_toolkit.batch_operation("insert", test_table, test_batch, batch_size)
        
        # Verificar que se insertaron todos los registros
        assert len(ids) == 200
        
        # Verificar en la base de datos
        records = pg_toolkit.fetch_records(test_table)
        assert len(records) == 200
        
        # Actualizar en lotes
        update_batch = [
            {"value": i*10, "conditions": {"id": ids[i]}}
            for i in range(100)
        ]
        
        # Ejecutar actualización en lote
        update_results = pg_toolkit.batch_operation("update", test_table, update_batch, batch_size)
        
        # Verificar actualización
        updated_records = pg_toolkit.fetch_records(
            test_table,
            conditions={("id", "IN"): ids[:100]}
        )
        assert all(value % 10 == 0 for value in updated_records["value"])

    def test_export_query_to_csv(self, pg_toolkit, test_table, test_data):
        """Probar exportación de resultados a CSV."""
        # Insertar registros
        pg_toolkit.insert_records(test_table, test_data)
        
        # Exportar a CSV
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name
        
        csv_path = pg_toolkit.export_query_to_csv(
            f"SELECT * FROM {test_table}",
            filepath=tmp_path
        )
        
        # Verificar que el archivo existe
        assert os.path.exists(csv_path)
        
        # Leer el CSV y verificar contenido
        df = pd.read_csv(csv_path)
        assert len(df) == 5
        assert "name" in df.columns
        assert "value" in df.columns
        
        # Sin path, debería devolver el DataFrame
        df_result = pg_toolkit.export_query_to_csv(
            f"SELECT * FROM {test_table} WHERE active = TRUE"
        )
        assert isinstance(df_result, pd.DataFrame)
        assert len(df_result) == 4
        
        # Limpiar
        os.unlink(tmp_path)

    def test_execute_transaction(self, pg_toolkit, test_table):
        """Probar ejecución de transacciones atómicas."""
        # Crear una tabla para transacciones
        transaction_table = f"{test_table}_transaction"
        pg_toolkit.create_table(transaction_table, {
            "id": "SERIAL PRIMARY KEY",
            "account": "VARCHAR(100)",
            "balance": "DECIMAL(10,2)"
        })
        
        # Ejecutar transacción exitosa
        pg_toolkit.execute_transaction([
            (f"INSERT INTO {transaction_table} (account, balance) VALUES (%s, %s)", ("Account A", 1000)),
            (f"INSERT INTO {transaction_table} (account, balance) VALUES (%s, %s)", ("Account B", 500)),
            (f"UPDATE {transaction_table} SET balance = balance - 200 WHERE account = %s", ("Account A",)),
            (f"UPDATE {transaction_table} SET balance = balance + 200 WHERE account = %s", ("Account B",))
        ])
        
        # Verificar estado después de la transacción
        accounts = pg_toolkit.fetch_records(transaction_table)
        assert len(accounts) == 2
        account_a = accounts[accounts["account"] == "Account A"]
        account_b = accounts[accounts["account"] == "Account B"]
        assert float(account_a["balance"].iloc[0]) == 800
        assert float(account_b["balance"].iloc[0]) == 700
        
        # Intentar transacción que debe fallar (referencia a cuenta inexistente)
        with pytest.raises(QueryError):
            pg_toolkit.execute_transaction([
                (f"UPDATE {transaction_table} SET balance = balance - 100 WHERE account = %s", ("Account A",)),
                (f"UPDATE {transaction_table} SET balance = balance + 100 WHERE account = %s", ("Account C",))
            ])
        
        # Verificar que no se realizó ningún cambio (rollback automático)
        accounts_after_error = pg_toolkit.fetch_records(transaction_table)
        account_a_after = accounts_after_error[accounts_after_error["account"] == "Account A"]
        assert float(account_a_after["balance"].iloc[0]) == 800  # Sin cambios
        
        # Limpiar
        pg_toolkit.delete_table(transaction_table)


class TestPgDbToolkitUsers:
    """
    Pruebas para las funciones de gestión de usuarios en PgDbToolkit.
    """
    
    def test_get_users(self, pg_toolkit):
        """Verificar que podemos obtener la lista de usuarios del sistema."""
        # Obtener usuarios
        users = pg_toolkit.get_users()
        
        # Verificar que la estructura del DataFrame es correcta
        assert isinstance(users, pd.DataFrame)
        assert "username" in users.columns
        assert "is_superuser" in users.columns
        assert "can_create_db" in users.columns
        assert "can_login" in users.columns
        
        # Verificar que al menos existe el usuario postgres (que siempre debe existir)
        assert "postgres" in users["username"].values
        
        # Verificar que al menos existe el usuario que estamos usando para conectarnos
        current_user = pg_toolkit.db_config.get("user", "postgres")
        if current_user != "postgres":  # Si no es el usuario postgres
            assert current_user in users["username"].values
    
    def test_user_management(self, pg_toolkit):
        """Probar el ciclo completo de gestión de usuarios."""
        # Nombre de usuario único para la prueba usando timestamp y número aleatorio
        test_username = f"test_sync_user_{int(time.time())}_{random.randint(1000, 9999)}"
        
        try:
            # 1. Crear usuario
            pg_toolkit.create_user(
                username=test_username,
                password="test_password",
                createdb=True,
                login=True
            )
            
            # 2. Verificar que el usuario existe y tiene los atributos correctos
            users = pg_toolkit.get_users()
            assert test_username in users["username"].values
            
            user_row = users[users["username"] == test_username].iloc[0]
            assert user_row["can_create_db"] == True
            assert user_row["can_login"] == True
            assert user_row["is_superuser"] == False
            
            # 3. Actualizar usuario
            pg_toolkit.update_user(
                test_username,
                attributes={
                    "superuser": True,
                    "connection_limit": 5
                }
            )
            
            # 4. Verificar los cambios
            updated_users = pg_toolkit.get_users()
            updated_user = updated_users[updated_users["username"] == test_username].iloc[0]
            assert updated_user["is_superuser"] == True
            assert updated_user["connection_limit"] == 5
            
            # 5. Otorgar privilegios sobre la base de datos de prueba
            # Nota: Esto asume que tienes permiso para modificar privilegios
            try:
                pg_toolkit.grant_database_privileges(
                    test_username,
                    pg_toolkit.db_config["dbname"],
                    privileges=["CONNECT"]
                )
            except Exception as e:
                # Si esto falla, puede ser por falta de permisos, y no debería hacer fallar la prueba
                print(f"Nota: No se pudieron otorgar privilegios: {e}")
            
        finally:
            # 6. Limpiar - eliminar usuario con CASCADE para forzar la eliminación
            success = pg_toolkit.delete_user(test_username, cascade=True)
            
            if success:
                # Verificar que se eliminó correctamente
                final_users = pg_toolkit.get_users()
                assert test_username not in final_users["username"].values
            else:
                # Intentar una eliminación más agresiva como último recurso
                try:
                    pg_toolkit.execute_query(
                        f"DROP ROLE IF EXISTS {test_username} CASCADE"
                    )
                except Exception as e:
                    print(f"No se pudo eliminar usuario {test_username} incluso con método agresivo: {e}")