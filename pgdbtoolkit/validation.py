# validation.py

"""
Utilidades de validación para datos de base de datos.
Este módulo proporciona funciones para validar datos antes de su inserción en la base de datos.
"""

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable, Type
import json

from .exceptions import ValidationError

def validate_type(value: Any, expected_type: Type, field_name: str = None) -> None:
    """
    Valida que un valor sea del tipo esperado.
    
    Args:
        value: Valor a validar.
        expected_type: Tipo esperado.
        field_name: Nombre del campo (para mensajes de error).
        
    Raises:
        ValidationError: Si el valor no es del tipo esperado.
    """
    field_msg = f" para el campo '{field_name}'" if field_name else ""
    
    if not isinstance(value, expected_type):
        raise ValidationError(f"Se esperaba un valor de tipo {expected_type.__name__}{field_msg}, pero se recibió {type(value).__name__}")

def validate_not_empty(value: Any, field_name: str = None) -> None:
    """
    Valida que un valor no esté vacío (None, '', [], {}).
    
    Args:
        value: Valor a validar.
        field_name: Nombre del campo (para mensajes de error).
        
    Raises:
        ValidationError: Si el valor está vacío.
    """
    field_msg = f"El campo '{field_name}'" if field_name else "El valor"
    
    if value is None or value == "" or value == [] or value == {}:
        raise ValidationError(f"{field_msg} no puede estar vacío")

def validate_length(value: Union[str, List], min_length: int = None, max_length: int = None, field_name: str = None) -> None:
    """
    Valida que la longitud de un string o lista esté dentro de un rango.
    
    Args:
        value: Valor a validar.
        min_length: Longitud mínima permitida.
        max_length: Longitud máxima permitida.
        field_name: Nombre del campo (para mensajes de error).
        
    Raises:
        ValidationError: Si la longitud está fuera del rango permitido.
    """
    field_msg = f"'{field_name}'" if field_name else "El valor"
    
    if value is None:
        return
        
    length = len(value)
    
    if min_length is not None and length < min_length:
        raise ValidationError(f"{field_msg} debe tener al menos {min_length} caracteres")
        
    if max_length is not None and length > max_length:
        raise ValidationError(f"{field_msg} no debe tener más de {max_length} caracteres")

def validate_regex(value: str, pattern: str, field_name: str = None) -> None:
    """
    Valida que un string cumpla con un patrón de expresión regular.
    
    Args:
        value: Valor a validar.
        pattern: Patrón de expresión regular.
        field_name: Nombre del campo (para mensajes de error).
        
    Raises:
        ValidationError: Si el valor no cumple con el patrón.
    """
    field_msg = f"El campo '{field_name}'" if field_name else "El valor"
    
    if value is None:
        return
        
    if not re.match(pattern, value):
        raise ValidationError(f"{field_msg} no tiene un formato válido")

def validate_email(value: str, field_name: str = None) -> None:
    """
    Valida que un string tenga formato de correo electrónico.
    
    Args:
        value: Valor a validar.
        field_name: Nombre del campo (para mensajes de error).
        
    Raises:
        ValidationError: Si el valor no tiene formato de correo.
    """
    field_msg = f"El campo '{field_name}'" if field_name else "El correo electrónico"
    
    if value is None:
        return
        
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        raise ValidationError(f"{field_msg} no tiene un formato válido")

def validate_uuid(value: str, field_name: str = None) -> None:
    """
    Valida que un string tenga formato UUID.
    
    Args:
        value: Valor a validar.
        field_name: Nombre del campo (para mensajes de error).
        
    Raises:
        ValidationError: Si el valor no tiene formato UUID.
    """
    field_msg = f"El campo '{field_name}'" if field_name else "El UUID"
    
    if value is None:
        return
        
    try:
        uuid.UUID(str(value))
    except ValueError:
        raise ValidationError(f"{field_msg} no tiene un formato UUID válido")

def validate_date(value: str, format_str: str = "%Y-%m-%d", field_name: str = None) -> None:
    """
    Valida que un string tenga formato de fecha.
    
    Args:
        value: Valor a validar.
        format_str: Formato de fecha esperado.
        field_name: Nombre del campo (para mensajes de error).
        
    Raises:
        ValidationError: Si el valor no tiene formato de fecha.
    """
    field_msg = f"El campo '{field_name}'" if field_name else "La fecha"
    
    if value is None:
        return
        
    try:
        datetime.strptime(value, format_str)
    except ValueError:
        raise ValidationError(f"{field_msg} no tiene un formato válido (debe ser {format_str})")

def validate_numeric(value: Any, min_value: float = None, max_value: float = None, field_name: str = None) -> None:
    """
    Valida que un valor sea numérico y esté dentro de un rango.
    
    Args:
        value: Valor a validar.
        min_value: Valor mínimo permitido.
        max_value: Valor máximo permitido.
        field_name: Nombre del campo (para mensajes de error).
        
    Raises:
        ValidationError: Si el valor no es numérico o está fuera del rango.
    """
    field_msg = f"El campo '{field_name}'" if field_name else "El valor"
    
    if value is None:
        return
        
    try:
        num_value = float(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{field_msg} debe ser un número")
        
    if min_value is not None and num_value < min_value:
        raise ValidationError(f"{field_msg} debe ser mayor o igual a {min_value}")
        
    if max_value is not None and num_value > max_value:
        raise ValidationError(f"{field_msg} debe ser menor o igual a {max_value}")

def validate_in_options(value: Any, options: List[Any], field_name: str = None) -> None:
    """
    Valida que un valor esté dentro de un conjunto de opciones válidas.
    
    Args:
        value: Valor a validar.
        options: Lista de opciones válidas.
        field_name: Nombre del campo (para mensajes de error).
        
    Raises:
        ValidationError: Si el valor no está en las opciones.
    """
    field_msg = f"El campo '{field_name}'" if field_name else "El valor"
    
    if value is None:
        return
        
    if value not in options:
        options_str = ", ".join([str(opt) for opt in options])
        raise ValidationError(f"{field_msg} debe ser uno de los siguientes valores: {options_str}")

def validate_json(value: Any, field_name: str = None) -> None:
    """
    Valida que un valor sea JSON válido o se pueda serializar a JSON.
    
    Args:
        value: Valor a validar.
        field_name: Nombre del campo (para mensajes de error).
        
    Raises:
        ValidationError: Si el valor no es JSON válido.
    """
    field_msg = f"El campo '{field_name}'" if field_name else "El valor"
    
    if value is None:
        return
        
    try:
        if isinstance(value, str):
            json.loads(value)
        else:
            json.dumps(value)
    except (json.JSONDecodeError, TypeError):
        raise ValidationError(f"{field_msg} no es un JSON válido")

def validate_schema(data: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Valida que un diccionario cumpla con un esquema definido.
    
    Args:
        data: Diccionario a validar.
        schema: Esquema de validación. Formato:
            {
                "campo1": {
                    "type": tipo_esperado,
                    "required": True/False,
                    "validators": [lista_de_funciones_validadoras]
                },
                ...
            }
            
    Returns:
        Dict[str, List[str]]: Diccionario con errores por campo.
    """
    errors = {}
    
    # Verificar campos requeridos
    for field_name, field_schema in schema.items():
        if field_schema.get("required", False) and field_name not in data:
            errors[field_name] = ["Este campo es requerido"]
    
    # Validar campos presentes
    for field_name, value in data.items():
        if field_name not in schema:
            continue
            
        field_schema = schema[field_name]
        field_errors = []
        
        # Validar tipo
        if "type" in field_schema and value is not None:
            expected_type = field_schema["type"]
            try:
                validate_type(value, expected_type, field_name)
            except ValidationError as e:
                field_errors.append(str(e))
        
        # Ejecutar validadores adicionales
        for validator in field_schema.get("validators", []):
            try:
                validator(value, field_name=field_name)
            except ValidationError as e:
                field_errors.append(str(e))
        
        if field_errors:
            errors[field_name] = field_errors
    
    return errors

def validate_record(record: Dict[str, Any], table_schema: Dict[str, Dict[str, Any]]) -> None:
    """
    Valida un registro antes de su inserción en la base de datos.
    
    Args:
        record: Registro a validar.
        table_schema: Esquema de la tabla.
        
    Raises:
        ValidationError: Si el registro no cumple con el esquema.
    """
    errors = validate_schema(record, table_schema)
    
    if errors:
        error_messages = []
        for field, field_errors in errors.items():
            for error in field_errors:
                error_messages.append(f"{field}: {error}")
        
        raise ValidationError("Errores de validación: " + "; ".join(error_messages))