"""
Decorators for Construct-based LabVIEW Object Support.

This module provides decorators to easily convert Python classes to LabVIEW Objects,
making it simpler to work with the construct_impl serialization system.
"""

from typing import Optional, Any, List, get_type_hints
from functools import wraps
import inspect

from .objects import create_lvobject, LVObject
from .basic_types import LVI32, LVString, LVBoolean, LVDouble
from .compound_types import LVCluster


def lvclass(library: str = "", class_name: Optional[str] = None, 
            version: tuple = (1, 0, 0, 0), num_levels: int = 1):
    """
    Decorator to mark a Python class as a LabVIEW Object.
    
    This decorator enables automatic serialization of Python class instances
    to LabVIEW Object format using the construct_impl system.
    
    Args:
        library: LabVIEW library name (without .lvlib extension)
        class_name: LabVIEW class name (without .lvclass extension). 
                   If None, uses the Python class name.
        version: Version tuple (major, minor, patch, build)
        num_levels: Number of inheritance levels (1 for single level,
                   more if inheriting from LabVIEW parent classes)
    
    The decorator:
    - Stores LabVIEW metadata on the class
    - Enables automatic serialization via lvflatten()
    - Supports inheritance hierarchies
    
    Examples:
        Basic usage:
        >>> @lvclass(library="MyLib", class_name="MyClass")
        >>> class MyClass:
        >>>     message: str = ""
        >>>     count: int = 0
        
        With inheritance (3 levels: Message -> Serializable Msg -> echo general Msg):
        >>> @lvclass(library="Commander", class_name="echo general Msg", 
        ...          version=(1,0,0,7), num_levels=3)
        >>> class EchoGeneralMsg:
        >>>     message: str = ""
        >>>     status: int = 0
        
        Then serialize:
        >>> msg = EchoGeneralMsg()
        >>> msg.message = "Hello, LabVIEW!"
        >>> from src.construct_impl.api import lvflatten
        >>> data = lvflatten(msg)  # Automatically serializes to LVObject format
    """
    def decorator(cls):
        # Store LabVIEW metadata on the class
        cls.__lv_library__ = library if library else cls.__name__
        cls.__lv_class_name__ = class_name if class_name else cls.__name__
        cls.__lv_version__ = version
        cls.__lv_num_levels__ = num_levels
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
            
            Returns:
                Dictionary suitable for LVObject serialization
            """
            # Get all instance attributes
            cluster_data = []
            
            # Build cluster data from instance attributes
            # For now, we'll serialize to bytes using basic types
            import io
            stream = io.BytesIO()
            
            # Get type hints if available
            hints = get_type_hints(self.__class__) if hasattr(self.__class__, '__annotations__') else {}
            
            # Serialize each attribute
            for attr_name in dir(self):
                if attr_name.startswith('_') or attr_name.startswith('__lv'):
                    continue
                if callable(getattr(self, attr_name)):
                    continue
                    
                value = getattr(self, attr_name)
                attr_type = hints.get(attr_name)
                
                # Serialize based on type
                if isinstance(value, str):
                    stream.write(LVString.build(value))
                elif isinstance(value, bool):
                    stream.write(LVBoolean.build(value))
                elif isinstance(value, int):
                    stream.write(LVI32.build(value))
                elif isinstance(value, float):
                    stream.write(LVDouble.build(value))
            
            cluster_bytes = stream.getvalue()
            
            # Create appropriate number of cluster data entries
            # For derived class (level N), put data there. Parents get empty data.
            EMPTY_CLUSTER_SIZE = 8  # LabVIEW standard for empty cluster padding
            cluster_data_list = [b'\x00' * EMPTY_CLUSTER_SIZE] * (self.__lv_num_levels__ - 1) + [cluster_bytes]
            
            # Create versions list (all levels get same version for now)
            version_int = (self.__lv_version__[0] << 24 | 
                          self.__lv_version__[1] << 16 | 
                          self.__lv_version__[2] << 8 | 
                          self.__lv_version__[3])
            versions = [version_int] * self.__lv_num_levels__
            
            # Create LVObject using the new API
            return create_lvobject(
                class_name=f"{self.__lv_library__}.lvlib:{self.__lv_class_name__}.lvclass",
                num_levels=self.__lv_num_levels__,
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
