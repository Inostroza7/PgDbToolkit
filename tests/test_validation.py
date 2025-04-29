# tests/test_validation.py

"""
Tests para las funciones de validación.
"""

import pytest
import json
from datetime import date, datetime
import uuid

from pgdbtoolkit.validation import (
    validate_type,
    validate_not_empty,
    validate_length,
    validate_regex,
    validate_email,
    validate_uuid,
    validate_date,
    validate_numeric,
    validate_in_options,
    validate_json,
    validate_schema,
    validate_record
)
from pgdbtoolkit.exceptions import ValidationError


class TestValidation:
    """
    Pruebas para las funciones de validación.
    """

    def test_validate_type(self):
        """Verificar la validación de tipos."""
        # Casos válidos
        validate_type("test", str)
        validate_type(123, int)
        validate_type(123.45, float)
        validate_type(True, bool)
        validate_type([1, 2, 3], list)
        validate_type({"a": 1}, dict)
        
        # Casos inválidos
        with pytest.raises(ValidationError):
            validate_type("test", int)
        
        with pytest.raises(ValidationError):
            validate_type(123, str)
        
        with pytest.raises(ValidationError):
            validate_type([1, 2, 3], dict)
        
        # Con nombre de campo
        with pytest.raises(ValidationError) as excinfo:
            validate_type("test", int, field_name="age")
        assert "age" in str(excinfo.value)
    
    def test_validate_not_empty(self):
        """Verificar la validación de valores no vacíos."""
        # Casos válidos
        validate_not_empty("test")
        validate_not_empty(123)
        validate_not_empty([1, 2, 3])
        validate_not_empty({"a": 1})
        validate_not_empty(False)  # False no se considera vacío
        
        # Casos inválidos
        with pytest.raises(ValidationError):
            validate_not_empty("")
        
        with pytest.raises(ValidationError):
            validate_not_empty([])
        
        with pytest.raises(ValidationError):
            validate_not_empty({})
        
        with pytest.raises(ValidationError):
            validate_not_empty(None)
        
        # Con nombre de campo
        with pytest.raises(ValidationError) as excinfo:
            validate_not_empty("", field_name="username")
        assert "username" in str(excinfo.value)
    
    def test_validate_length(self):
        """Verificar la validación de longitud."""
        # Casos válidos
        validate_length("test", min_length=1)
        validate_length("test", max_length=10)
        validate_length("test", min_length=1, max_length=10)
        validate_length([1, 2, 3, 4], min_length=2, max_length=5)
        
        # Casos inválidos
        with pytest.raises(ValidationError):
            validate_length("test", min_length=5)
        
        with pytest.raises(ValidationError):
            validate_length("test", max_length=3)
        
        with pytest.raises(ValidationError):
            validate_length([1, 2], min_length=3)
        
        # Caso nulo (no debería fallar)
        validate_length(None, min_length=5)
        
        # Con nombre de campo
        with pytest.raises(ValidationError) as excinfo:
            validate_length("pass", min_length=8, field_name="password")
        assert "password" in str(excinfo.value)
    
    def test_validate_regex(self):
        """Verificar la validación con expresiones regulares."""
        # Casos válidos
        validate_regex("ABC123", r"^[A-Z0-9]+$")
        validate_regex("2023-01-01", r"^\d{4}-\d{2}-\d{2}$")
        
        # Casos inválidos
        with pytest.raises(ValidationError):
            validate_regex("abc123", r"^[A-Z0-9]+$")
        
        with pytest.raises(ValidationError):
            validate_regex("01/01/2023", r"^\d{4}-\d{2}-\d{2}$")
        
        # Caso nulo (no debería fallar)
        validate_regex(None, r"^[A-Z0-9]+$")
        
        # Con nombre de campo
        with pytest.raises(ValidationError) as excinfo:
            validate_regex("abc123", r"^[A-Z0-9]+$", field_name="code")
        assert "code" in str(excinfo.value)
    
    def test_validate_email(self):
        """Verificar la validación de direcciones de correo electrónico."""
        # Casos válidos
        validate_email("user@example.com")
        validate_email("firstname.lastname@example.co.uk")
        validate_email("user+tag@example.org")
        
        # Casos inválidos
        with pytest.raises(ValidationError):
            validate_email("user@")
        
        with pytest.raises(ValidationError):
            validate_email("@example.com")
        
        with pytest.raises(ValidationError):
            validate_email("user@example")
        
        with pytest.raises(ValidationError):
            validate_email("user.example.com")
        
        # Caso nulo (no debería fallar)
        validate_email(None)
        
        # Con nombre de campo
        with pytest.raises(ValidationError) as excinfo:
            validate_email("invalid-email", field_name="contact_email")
        assert "contact_email" in str(excinfo.value)
    
    def test_validate_uuid(self):
        """Verificar la validación de UUIDs."""
        # Casos válidos
        validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        validate_uuid(str(uuid.uuid4()))
        
        # Casos inválidos
        with pytest.raises(ValidationError):
            validate_uuid("invalid-uuid")
        
        with pytest.raises(ValidationError):
            validate_uuid("550e8400-e29b-41d4-a716-44665544000Z")  # Caracter Z no válido en hexadecimal
        
        # Caso nulo (no debería fallar)
        validate_uuid(None)
        
        # Con nombre de campo
        with pytest.raises(ValidationError) as excinfo:
            validate_uuid("invalid-id", field_name="user_id")
        assert "user_id" in str(excinfo.value)
    
    def test_validate_date(self):
        """Verificar la validación de fechas."""
        # Casos válidos
        validate_date("2023-01-01")
        validate_date("01/01/2023", format_str="%d/%m/%Y")
        
        # Casos inválidos
        with pytest.raises(ValidationError):
            validate_date("2023/01/01")  # Formato incorrecto
        
        with pytest.raises(ValidationError):
            validate_date("01/01/2023")  # Formato incorrecto para el valor predeterminado
        
        with pytest.raises(ValidationError):
            validate_date("2023-13-01")  # Fecha inválida
        
        # Caso nulo (no debería fallar)
        validate_date(None)
        
        # Con nombre de campo
        with pytest.raises(ValidationError) as excinfo:
            validate_date("2023/01/01", field_name="birth_date")
        assert "birth_date" in str(excinfo.value)
    
    def test_validate_numeric(self):
        """Verificar la validación de valores numéricos."""
        # Casos válidos
        validate_numeric(123)
        validate_numeric("123")
        validate_numeric(123.45)
        validate_numeric("123.45")
        validate_numeric(123, min_value=0)
        validate_numeric(123, max_value=200)
        validate_numeric(123, min_value=0, max_value=200)
        
        # Casos inválidos
        with pytest.raises(ValidationError):
            validate_numeric("abc")  # No es un número
        
        with pytest.raises(ValidationError):
            validate_numeric(-10, min_value=0)  # Menor que el mínimo
        
        with pytest.raises(ValidationError):
            validate_numeric(300, max_value=200)  # Mayor que el máximo
        
        # Caso nulo (no debería fallar)
        validate_numeric(None)
        
        # Con nombre de campo
        with pytest.raises(ValidationError) as excinfo:
            validate_numeric(-10, min_value=0, field_name="age")
        assert "age" in str(excinfo.value)
    
    def test_validate_in_options(self):
        """Verificar la validación de valores dentro de un conjunto de opciones."""
        # Casos válidos
        validate_in_options("A", ["A", "B", "C"])
        validate_in_options(1, [1, 2, 3])
        
        # Casos inválidos
        with pytest.raises(ValidationError):
            validate_in_options("D", ["A", "B", "C"])
        
        with pytest.raises(ValidationError):
            validate_in_options(4, [1, 2, 3])
        
        # Caso nulo (no debería fallar)
        validate_in_options(None, ["A", "B", "C"])
        
        # Con nombre de campo
        with pytest.raises(ValidationError) as excinfo:
            validate_in_options("D", ["A", "B", "C"], field_name="status")
        assert "status" in str(excinfo.value)
    
    def test_validate_json(self):
        """Verificar la validación de JSON."""
        # Casos válidos
        validate_json('{"name": "John", "age": 30}')
        validate_json({"name": "John", "age": 30})
        validate_json([1, 2, 3])
        
        # Casos inválidos
        with pytest.raises(ValidationError):
            validate_json('{"name": "John", "age": }')  # JSON inválido
        
        with pytest.raises(ValidationError):
            validate_json(object())  # No se puede serializar a JSON
        
        # Caso nulo (no debería fallar)
        validate_json(None)
        
        # Con nombre de campo
        with pytest.raises(ValidationError) as excinfo:
            validate_json('{"invalid', field_name="data")
        assert "data" in str(excinfo.value)
    
    def test_validate_schema(self):
        """Verificar la validación de esquemas completos."""
        # Definir un esquema de validación
        schema = {
            "name": {
                "type": str,
                "required": True,
                "validators": [lambda x, **kw: validate_length(x, min_length=2, max_length=100)]
            },
            "email": {
                "type": str,
                "required": True,
                "validators": [validate_email]
            },
            "age": {
                "type": int,
                "validators": [lambda x, **kw: validate_numeric(x, min_value=18, max_value=120)]
            },
            "status": {
                "type": str,
                "validators": [lambda x, **kw: validate_in_options(x, ["active", "inactive", "pending"])]
            }
        }
        
        # Datos válidos
        valid_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "status": "active"
        }
        
        errors = validate_schema(valid_data, schema)
        assert not errors
        
        # Datos con errores
        invalid_data = {
            "name": "J",  # Muy corto
            "email": "invalid-email",
            "age": 15,  # Muy joven
            "status": "unknown"  # No está en las opciones
        }
        
        errors = validate_schema(invalid_data, schema)
        assert errors
        assert "name" in errors
        assert "email" in errors
        assert "age" in errors
        assert "status" in errors
        
        # Datos con campo requerido faltante
        missing_required = {
            "age": 30,
            "status": "active"
        }
        
        errors = validate_schema(missing_required, schema)
        assert errors
        assert "name" in errors
        assert "email" in errors
    
    def test_validate_record(self):
        """Verificar la validación de registros completos."""
        # Definir un esquema de tabla
        table_schema = {
            "name": {
                "type": str,
                "required": True,
                "validators": [lambda x, **kw: validate_length(x, min_length=2, max_length=100)]
            },
            "email": {
                "type": str,
                "required": True,
                "validators": [validate_email]
            },
            "age": {
                "type": int,
                "validators": [lambda x, **kw: validate_numeric(x, min_value=18, max_value=120)]
            }
        }
        
        # Registro válido
        valid_record = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        }
        
        # No debería levantar excepción
        validate_record(valid_record, table_schema)
        
        # Registro inválido
        invalid_record = {
            "name": "J",  # Muy corto
            "email": "invalid-email",
            "age": 15  # Muy joven
        }
        
        # Debería levantar excepción con mensajes de error
        with pytest.raises(ValidationError) as excinfo:
            validate_record(invalid_record, table_schema)
        
        error_message = str(excinfo.value)
        assert "name" in error_message
        assert "email" in error_message
        assert "age" in error_message