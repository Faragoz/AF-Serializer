"""
Auto-Flatten - Inferencia automática de tipos y serialización
"""
from typing import Any, Optional
import numpy as np

from .types import LVType, LVBoolean, LVNumeric, LVString, LVArray, LVCluster
from .serialization import SerializationContext


def _auto_infer_type(data: Any) -> LVType:
    """
    Infiere automáticamente el tipo LabVIEW desde datos Python.
    
    Reglas de inferencia:
    - bool → LVBoolean
    - int → LVNumeric(np.int32)
    - float → LVNumeric(np.float64)
    - str → LVString
    - list homogénea → LVArray
    - list heterogénea → LVCluster (sin nombres)
    - tuple → LVCluster (sin nombres)
    - dict → LVCluster (con nombres)
    - LVType → retornar tal cual
    """
    # Si ya es un LVType, retornar directamente
    if isinstance(data, LVType):
        return data
    
    # Boolean (antes de int, porque bool es subclase de int)
    if isinstance(data, bool):
        return LVBoolean(data)
    
    # Numéricos
    if isinstance(data, int):
        return LVNumeric(data, np.int32)
    
    if isinstance(data, float):
        return LVNumeric(data, np.float64)
    
    # String
    if isinstance(data, str):
        return LVString(data)
    
    # List: detectar si es homogénea o heterogénea
    if isinstance(data, list):
        if not data:
            raise ValueError("Cannot infer type from empty list")
        
        # Convertir elementos recursivamente
        elements = [_auto_infer_type(x) for x in data]
        
        # Verificar si todos son del mismo tipo
        first_type = type(elements[0])
        if all(isinstance(e, first_type) for e in elements):
            # Lista homogénea → Array
            return LVArray(elements, first_type)
        else:
            # Lista heterogénea → Cluster sin nombres
            names = tuple(f"elem_{i}" for i in range(len(elements)))
            return LVCluster((names, tuple(elements)), named=False)
    
    # Tuple: siempre cluster sin nombres
    if isinstance(data, tuple):
        if not data:
            raise ValueError("Cannot infer type from empty tuple")
        
        elements = [_auto_infer_type(x) for x in data]
        names = tuple(f"elem_{i}" for i in range(len(elements)))
        return LVCluster((names, tuple(elements)), named=False)
    
    # Dict: cluster con nombres
    if isinstance(data, dict):
        if not data:
            raise ValueError("Cannot infer type from empty dict")
        
        names = tuple(data.keys())
        values = tuple(_auto_infer_type(v) for v in data.values())
        return LVCluster((names, values), named=True)
    
    raise TypeError(f"Cannot auto-infer LabVIEW type from {type(data)}")


def lvflatten(data: Any, context: Optional[SerializationContext] = None) -> bytes:
    """
    Serializa automáticamente cualquier dato Python a formato LabVIEW.
    
    Args:
        data: Cualquier tipo Python (int, float, str, list, tuple, dict, nested)
        context: Contexto de serialización (opcional)
    
    Returns:
        bytes: Datos serializados en formato LabVIEW
    
    Examples:
        >>> lvflatten(1)                                      # I32
        >>> lvflatten([1, 2, 3])                             # Array I32
        >>> lvflatten(("Hello", 0))                          # Cluster
        >>> lvflatten({"x": 1, "y": 2})                      # Cluster con nombres
    """
    context = context or SerializationContext()
    lv_type = _auto_infer_type(data)
    return lv_type.serialize(context)


def lvunflatten(data: bytes, type_hint: Optional[type] = None, 
                context: Optional[SerializationContext] = None) -> Any:
    """
    Deserializa datos LabVIEW a tipos Python.
    
    Args:
        data: Bytes en formato LabVIEW
        type_hint: Tipo esperado (opcional)
        context: Contexto de deserialización (opcional)
    
    Returns:
        Datos Python deserializados
    
    Note:
        Implementación completa pendiente
    """
    # TODO: Implementar deserialización completa
    raise NotImplementedError("Deserialización completa pendiente")
