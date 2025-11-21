"""
Decorators for Construct-based LabVIEW Object Support.

This module provides decorators to easily convert Python classes to LabVIEW Objects,
making it simpler to work with the construct_impl serialization system.
"""

from typing import Optional, Any, List, get_type_hints
from functools import wraps
import inspect

from .objects import create_lvobject, LVObject
from .basic_types import (
    LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64,
    LVString, LVBoolean, LVDouble, LVSingle
)
from .compound_types import LVCluster


def lvclass(library: str = "", class_name: Optional[str] = None, 
            version: tuple = (1, 0, 0, 0)):
    """
    Decorator to mark a Python class as a LabVIEW Object.
    
    This decorator enables automatic serialization of Python class instances
    to LabVIEW Object format using the construct_impl system.
    
    The decorator automatically detects inheritance from other @lvclass decorated
    classes and determines the number of levels, versions, and cluster data.
    
    Args:
        library: LabVIEW library name (without .lvlib extension).
                Optional - defaults to empty string.
        class_name: LabVIEW class name (without .lvclass extension). 
                   If None, uses the Python class name.
        version: Version tuple (major, minor, patch, build).
                Optional - defaults to (1, 0, 0, 0).
    
    The decorator:
    - Stores LabVIEW metadata on the class
    - Auto-detects inheritance levels from decorated base classes
    - Collects versions from entire inheritance chain
    - Serializes based on Type Hints for cluster fields
    - Enables automatic serialization via lvflatten()
    
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
        
        Then serialize:
        >>> msg = EchoMsg()
        >>> msg.message = "Hello World"
        >>> msg.code = 0
        >>> from api import lvflatten
        >>> data = lvflatten(msg)  # Auto-serializes with 3 levels
    """
    def decorator(cls):
        # Store LabVIEW metadata on the class
        cls.__lv_library__ = library if library else ""
        cls.__lv_class_name__ = class_name if class_name else cls.__name__
        cls.__lv_version__ = version
        cls.__is_lv_class__ = True
        
        # Add a method to serialize the instance
        original_init = cls.__init__ if hasattr(cls, '__init__') else None
        
        def __init__(self, *args, **kwargs):
            if original_init:
                original_init(self, *args, **kwargs)
        
        cls.__init__ = __init__
        
        # Add a method to convert to LVObject dict
        def to_lvobject(self) -> dict:
            """
            Convert this Python instance to a LabVIEW Object dictionary.
            
            Automatically detects inheritance chain and builds complete LVObject.
            
            Returns:
                Dictionary suitable for LVObject serialization
            """
            import io
            
            # Walk up the inheritance chain to find all @lvclass decorated base classes
            inheritance_chain = []
            for base in inspect.getmro(self.__class__):
                if hasattr(base, '__is_lv_class__') and base.__is_lv_class__:
                    inheritance_chain.append(base)
            
            # Reverse to go from root to derived
            inheritance_chain.reverse()
            
            num_levels = len(inheritance_chain)
            
            # Collect versions for all levels
            versions = []
            for level_class in inheritance_chain:
                versions.append(level_class.__lv_version__)
            
            # Build cluster data for each level
            cluster_data_list = []
            for i, level_class in enumerate(inheritance_chain):
                # Get type hints for this specific level
                level_hints = level_class.__annotations__ if hasattr(level_class, '__annotations__') else {}
                
                if not level_hints:
                    # No fields at this level - empty cluster
                    cluster_data_list.append(b'')
                else:
                    # Serialize fields defined at this level
                    stream = io.BytesIO()
                    for attr_name, attr_type in level_hints.items():
                        if hasattr(self, attr_name):
                            value = getattr(self, attr_name)
                            
                            # Serialize based on type hint
                            # Check for Construct types FIRST (they have .build method)
                            if hasattr(attr_type, 'build'):
                                # It's a Construct type (LVI32, LVU16, LVString, etc.)
                                stream.write(attr_type.build(value))
                            # Then check for Python types
                            elif attr_type == str or isinstance(value, str):
                                stream.write(LVString.build(value))
                            elif attr_type == bool or isinstance(value, bool):
                                stream.write(LVBoolean.build(value))
                            elif attr_type == int or isinstance(value, int):
                                stream.write(LVI32.build(value))
                            elif attr_type == float or isinstance(value, float):
                                stream.write(LVDouble.build(value))
                    
                    cluster_data_list.append(stream.getvalue())
            
            # Use only the most derived class name
            most_derived = inheritance_chain[-1]
            full_class_name = f"{most_derived.__lv_library__}.lvlib:{most_derived.__lv_class_name__}.lvclass" if most_derived.__lv_library__ else f"{most_derived.__lv_class_name__}.lvclass"
            
            # Create LVObject using the new API
            return create_lvobject(
                class_name=full_class_name,
                num_levels=num_levels,
                versions=versions,
                cluster_data=cluster_data_list
            )
        
        cls.to_lvobject = to_lvobject
        
        # Add a method to serialize directly
        def to_bytes(self) -> bytes:
            """
            Serialize this instance to LabVIEW Object bytes.
            
            Returns:
                Serialized bytes in LabVIEW Object format
            """
            obj_construct = LVObject()
            return obj_construct.build(self.to_lvobject())
        
        cls.to_bytes = to_bytes
        
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
