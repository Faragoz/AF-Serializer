"""
Decorators for LabVIEW Object Support.

This module provides decorators to easily convert Python classes to LabVIEW Objects,
making it simpler to work with the af_serializer serialization system.
"""

from typing import Optional, Any, List, Type, get_type_hints
from functools import wraps
import inspect
import warnings

from .basic_types import (
    LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64,
    LVString, LVBoolean, LVDouble, LVSingle
)
from .compound_types import LVCluster


# ============================================================================
# Class Registry
# ============================================================================

_LVCLASS_REGISTRY: dict[str, Type] = {}
"""Global registry mapping LabVIEW class names to Python classes."""


def get_lvclass_by_name(full_name: str) -> Optional[Type]:
    """
    Lookup @lvclass decorated class by LabVIEW name.
    
    Args:
        full_name: The full LabVIEW class name (e.g., "MyLib.lvlib:MyClass.lvclass")
    
    Returns:
        The Python class if found, None otherwise
    """
    return _LVCLASS_REGISTRY.get(full_name)


def lvclass(library: str = "", class_name: Optional[str] = None, 
            version: tuple = (1, 0, 0, 1)):
    """
    Decorator to mark a Python class as a LabVIEW Object.
    
    This decorator enables automatic serialization and deserialization of Python 
    class instances to/from LabVIEW Object format using registry lookup.
    
    The decorator automatically detects inheritance from other @lvclass decorated
    classes and determines the number of levels, versions, and cluster data.
    
    Args:
        library: LabVIEW library name (without .lvlib extension).
                Optional - defaults to empty string.
        class_name: LabVIEW class name (without .lvclass extension). 
                   If None, uses the Python class name.
        version: Version tuple (major, minor, patch, build).
                Optional - defaults to (1, 0, 0, 1).
    
    The decorator:
    - Registers the class in the global _LVCLASS_REGISTRY
    - Stores LabVIEW metadata on the class
    - Auto-detects inheritance levels from decorated base classes
    - Enables automatic serialization via lvflatten()
    - Enables automatic deserialization via lvunflatten()
    
    Examples:
        Simple class:
        >>> @lvclass(library="MyLib", class_name="MyClass")
        >>> class MyClass:
        >>>     message: str = ""
        >>>     count: int = 0
        
        With inheritance (3 levels detected automatically):
        >>> @lvclass(library="Actor Framework", class_name="Message")
        >>> class Message:
        >>>     pass
        >>>
        >>> @lvclass(library="Serializable Message", class_name="Serializable Msg", 
        ...          version=(1, 0, 0, 7))
        >>> class SerializableMsg(Message):
        >>>     pass
        >>>
        >>> @lvclass(library="Commander", class_name="echo general Msg")
        >>> class EchoMsg(SerializableMsg):
        >>>     message: str
        >>>     code: int
        
        Serialize and deserialize:
        >>> msg = EchoMsg()
        >>> msg.message = "Hello World"
        >>> msg.code = 0
        >>> from api import lvflatten, lvunflatten
        >>> data = lvflatten(msg)  # Auto-serializes with 3 levels
        >>> restored = lvunflatten(data)  # Automatically returns EchoMsg instance
    """
    def decorator(cls):
        # Build full LabVIEW name
        lv_library = library if library else ""
        lv_class = class_name if class_name else cls.__name__
        
        full_name = f"{lv_library}.lvlib:{lv_class}.lvclass" if lv_library else f"{lv_class}.lvclass"
        
        # Register in global registry
        _LVCLASS_REGISTRY[full_name] = cls
        
        # Store LabVIEW metadata on the class
        cls.__lv_library__ = lv_library
        cls.__lv_class_name__ = lv_class
        cls.__lv_version__ = version
        cls.__is_lv_class__ = True
        
        return cls
    
    return decorator


def lvfield(lv_type=None, order: Optional[int] = None):
    """
    Decorator to mark a field with specific LabVIEW type information.
    
    This is optional and provides more control over field serialization.
    
    Args:
        lv_type: The LabVIEW type to use (LVI32, LVString, etc.)
        order: Field order in serialization (if different from definition order)
    
    Examples:
        >>> @lvclass(library="MyLib")
        >>> class MyClass:
        >>>     @lvfield(lv_type=LVI32, order=0)
        >>>     count: int = 0
        >>>     
        >>>     @lvfield(lv_type=LVString, order=1)
        >>>     message: str = ""
    """
    def decorator(func_or_attr):
        if callable(func_or_attr):
            func_or_attr.__lv_type__ = lv_type
            func_or_attr.__lv_order__ = order
            return func_or_attr
        else:
            # For direct attributes
            return func_or_attr
    
    return decorator


# Helper function to check if an object is a LabVIEW class instance
def is_lvclass(obj: Any) -> bool:
    """
    Check if an object is an instance of a @lvclass decorated class.
    
    Args:
        obj: Object to check
    
    Returns:
        True if object is a LabVIEW class instance
    """
    return hasattr(obj.__class__, '__is_lv_class__') and obj.__class__.__is_lv_class__
