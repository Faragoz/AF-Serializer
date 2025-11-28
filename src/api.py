"""
Public API for Construct-based LabVIEW Serialization.

This module provides the main public API for serializing and deserializing
LabVIEW data using the Construct library implementation.

Functions:
    lvflatten: Serialize Python data to LabVIEW binary format
    lvunflatten: Deserialize LabVIEW binary data to Python (automatic class detection)
"""

from typing import Any, Optional, Type, Union
from construct import Construct

from .basic_types import (
    LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64,
    LVDouble, LVSingle, LVBoolean, LVString,
    LVI32Type, LVU32Type, LVI16Type, LVU16Type, LVI8Type, LVU8Type,
    LVI64Type, LVU64Type, LVDoubleType, LVSingleType, LVBooleanType, LVStringType,
)
from .objects import LVObject


# Type mapping for auto-inference
_TYPE_MAP: dict[type, Construct] = {
    bool: LVBoolean,
    int: LVI32,
    float: LVDouble,
    str: LVString,
}


def lvflatten(data: Any, type_hint: Optional[Construct] = None) -> bytes:
    """
    Serialize Python data to LabVIEW binary format.
    
    This function converts Python data types to their LabVIEW binary
    representation using big-endian byte order.
    
    Supports @lvclass decorated objects for automatic LVObject serialization.
    
    Args:
        data: Data to serialize. Supported types:
            - int: Serialized as I32 by default
            - float: Serialized as Double by default
            - str: Serialized as String (Pascal String with Int32ub prefix)
            - bool: Serialized as Boolean (0x00 or 0x01)
            - @lvclass decorated object: Serialized as LVObject
        type_hint: Optional explicit Construct type definition.
            If provided, this overrides auto-detection.
            Examples: LVI32, LVDouble, LVString, LVBoolean
    
    Returns:
        bytes: Binary data in LabVIEW format (big-endian).
    
    Raises:
        TypeError: If data type is not supported and no type_hint is provided.
        ValidationError: If data doesn't match the expected format.
    
    Examples:
        >>> lvflatten(42)  # Auto-detect as I32
        b'\\x00\\x00\\x00*'
        
        >>> lvflatten(42, LVI64)  # Explicit I64
        b'\\x00\\x00\\x00\\x00\\x00\\x00\\x00*'
        
        >>> lvflatten("Hello")  # Auto-detect as String
        b'\\x00\\x00\\x00\\x05Hello'
        
        >>> @lvclass(library="MyLib", class_name="MyClass")
        >>> class MyClass:
        >>>     value: int = 0
        >>> obj = MyClass()
        >>> obj.value = 42
        >>> data = lvflatten(obj)  # Automatic LVObject serialization
    """
    # Check if data is a @lvclass decorated object
    if hasattr(data.__class__, '__is_lv_class__') and data.__class__.__is_lv_class__:
        # Auto-serialize using LVObject construct
        obj_construct = LVObject()
        return obj_construct.build(data)
    
    # Use provided type hint or auto-detect
    if type_hint is None:
        # Auto-detect type from Python data
        data_type = type(data)
        if data_type not in _TYPE_MAP:
            raise TypeError(
                f"Unsupported data type: {data_type.__name__}. "
                f"Supported types: {', '.join(t.__name__ for t in _TYPE_MAP.keys())}. "
                f"Provide an explicit type_hint for custom types or use @lvclass decorator."
            )
        type_hint = _TYPE_MAP[data_type]
    
    # Serialize using Construct
    return type_hint.build(data)


def lvunflatten(data: bytes, type_hint: Optional[Construct] = None) -> Any:
    """
    Deserialize LabVIEW binary data to Python.
    
    For LVObject data (detected by num_levels > 0), automatically uses registry
    lookup to return the correct @lvclass instance with populated attributes.
    
    For basic types, requires a type_hint to specify the expected format.
    
    Args:
        data: Binary data in LabVIEW format (big-endian).
        type_hint: Optional Construct type definition specifying the expected format.
            If None and data is LVObject, uses automatic class detection via registry.
            Examples: LVI32, LVDouble, LVString, LVBoolean
    
    Returns:
        For LVObject data:
            - Instance of @lvclass decorated class (if class found in registry)
            - dict with raw bytes (if class not found in registry)
        For basic types:
            - Deserialized Python value matching the type_hint
    
    Raises:
        ValueError: If type_hint is None and data is not LVObject format.
        ConstructError: If data doesn't match the expected format.
    
    Examples:
        # Automatic LVObject deserialization (no type_hint needed):
        >>> @lvclass(library="MyLib", class_name="EchoMsg")
        >>> class EchoMsg:
        >>>     message: str
        >>>     code: int
        >>> msg = EchoMsg()
        >>> msg.message = "Hello"
        >>> msg.code = 42
        >>> data = lvflatten(msg)
        >>> restored = lvunflatten(data)  # Automatically returns EchoMsg instance
        >>> assert isinstance(restored, EchoMsg)
        >>> assert restored.message == "Hello"
        >>> assert restored.code == 42
        
        # Basic type deserialization (requires type_hint):
        >>> data = b'\\x00\\x00\\x00*'
        >>> lvunflatten(data, LVI32)
        42
        
        >>> data = b'\\x00\\x00\\x00\\x05Hello'
        >>> lvunflatten(data, LVString)
        'Hello'
    """
    if type_hint is None:
        # Try to parse as LVObject (automatic detection)
        obj_construct = LVObject()
        return obj_construct.parse(data)
    
    return type_hint.parse(data)


# ============================================================================
# Convenience Functions for Specific Types
# ============================================================================

def flatten_i32(value: int) -> bytes:
    """Serialize a signed 32-bit integer to LabVIEW I32 format."""
    return LVI32.build(value)


def unflatten_i32(data: bytes) -> int:
    """Deserialize LabVIEW I32 format to signed 32-bit integer."""
    return LVI32.parse(data)


def flatten_double(value: float) -> bytes:
    """Serialize a float to LabVIEW Double format."""
    return LVDouble.build(value)


def unflatten_double(data: bytes) -> float:
    """Deserialize LabVIEW Double format to float."""
    return LVDouble.parse(data)


def flatten_string(value: str) -> bytes:
    """Serialize a string to LabVIEW String format."""
    return LVString.build(value)


def unflatten_string(data: bytes) -> str:
    """Deserialize LabVIEW String format to string."""
    return LVString.parse(data)


def flatten_boolean(value: bool) -> bytes:
    """Serialize a boolean to LabVIEW Boolean format."""
    return LVBoolean.build(value)


def unflatten_boolean(data: bytes) -> bool:
    """Deserialize LabVIEW Boolean format to boolean."""
    return LVBoolean.parse(data)


# ============================================================================
# NOTE: Advanced Serialization
# ============================================================================

# For arrays: Use LVArray1D or LVArray2D from compound_types module
# For clusters: Use LVCluster from compound_types module  
# For objects: Use @lvclass decorator or LVObject from objects module
#
# Examples:
#   from src import LVArray1D, LVI32
#   array_construct = LVArray1D(LVI32)
#   data = array_construct.build([1, 2, 3])
#
#   from src import LVCluster, LVString, LVI32
#   cluster = LVCluster(LVString, LVI32)
#   data = cluster.build(("Hello", 42))
#
#   from src import lvclass, lvflatten
#   @lvclass(library="MyLib", class_name="MyClass")
#   class MyClass:
#       value: int = 0
#   obj = MyClass()
#   data = lvflatten(obj)  # Automatic serialization
