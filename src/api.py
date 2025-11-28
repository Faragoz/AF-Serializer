"""
Public API for Construct-based LabVIEW Serialization.

This module provides the main public API for serializing and deserializing
LabVIEW data using the Construct library implementation.

Functions:
    lvflatten: Serialize Python data to LabVIEW binary format
    lvunflatten: Deserialize LabVIEW binary data to Python
"""

from typing import Any, Optional, Type, Union
from construct import Construct

from .basic_types import (
    LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64,
    LVDouble, LVSingle, LVBoolean, LVString,
    LVI32Type, LVU32Type, LVI16Type, LVU16Type, LVI8Type, LVU8Type,
    LVI64Type, LVU64Type, LVDoubleType, LVSingleType, LVBooleanType, LVStringType,
)


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
        
        >>> lvflatten(3.14)  # Auto-detect as Double
        b'@\\t!\\xfbTH-\\x18'
        
        >>> lvflatten(True)  # Auto-detect as Boolean
        b'\\x01'
    """
    # Check if data is a @lvclass decorated object
    if hasattr(data.__class__, '__is_lv_class__') and data.__class__.__is_lv_class__:
        # Auto-serialize using the to_bytes method
        if hasattr(data, 'to_bytes'):
            return data.to_bytes()
        else:
            raise TypeError(
                f"Object of type {type(data).__name__} is marked as LabVIEW class "
                f"but doesn't have to_bytes() method"
            )
    
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


def lvunflatten(data: bytes, type_hint: Union[Construct, Type]) -> Any:
    """
    Deserialize LabVIEW binary data to Python.
    
    This function converts LabVIEW binary format to Python data types.
    Supports both Construct types and @lvclass decorated classes.
    
    Args:
        data: Binary data in LabVIEW format (big-endian).
        type_hint: Either a Construct type definition (e.g., LVI32, LVDouble, LVString)
                   or an @lvclass decorated class type.
    
    Returns:
        Deserialized Python value matching the type_hint.
        If type_hint is an @lvclass decorated class, returns a populated instance.
    
    Raises:
        ConstructError: If data doesn't match the expected format.
        ValidationError: If data contains invalid values (e.g., boolean not 0x00/0x01).
        ValueError: If class not found in registry when using class type_hint.
    
    Examples:
        >>> data = b'\\x00\\x00\\x00*'
        >>> lvunflatten(data, LVI32)
        42
        
        >>> data = b'\\x00\\x00\\x00\\x05Hello'
        >>> lvunflatten(data, LVString)
        'Hello'
        
        >>> # With @lvclass decorated class
        >>> msg = EchoMsg()
        >>> msg.message = "Hello World"
        >>> msg.code = 42
        >>> data = lvflatten(msg)
        >>> restored = lvunflatten(data, EchoMsg)
        >>> assert restored.message == "Hello World"
        >>> assert restored.code == 42
    """
    from .objects import LVObject as LVObjectFactory
    from .decorators import get_lvclass_by_name
    
    # Check if type_hint is a class with __is_lv_class__ attribute
    if isinstance(type_hint, type) and hasattr(type_hint, '__is_lv_class__') and type_hint.__is_lv_class__:
        # Parse bytes as LVObject
        obj_construct = LVObjectFactory()
        lvobj_dict = obj_construct.parse(data)
        
        # Extract class_name from result
        class_name = lvobj_dict.get("class_name")
        
        if class_name:
            # Lookup class in registry (prefer most derived class)
            target_class = get_lvclass_by_name(class_name)
            
            if target_class is None:
                # Try to find a class in the inheritance chain
                # If user passes a base class but data is for derived class,
                # we should use the derived class from the registry
                target_class = type_hint
            
            # Create instance using from_lvobject
            if hasattr(target_class, 'from_lvobject'):
                return target_class.from_lvobject(lvobj_dict)
            else:
                # Fallback to returning the dict if from_lvobject not available
                return lvobj_dict
        else:
            # Empty object or no class name - return empty instance
            return type_hint.__new__(type_hint)
    
    # Otherwise, use existing Construct parsing logic
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
