"""
AF-Serializer - Compatibility wrapper for backward compatibility

This file maintains backward compatibility by re-exporting all classes
and functions from the new modular structure.

For new code, prefer importing directly from the submodules or from src:
    from src import lvflatten, LVNumeric, LVBoolean, etc.
"""

# Re-export everything from the new modular structure
from src.types import (
    LVType,
    LVNumeric,
    LVBoolean,
    LVString,
    LVArray,
    LVCluster,
    LVObject,
    LVObjectMetadata,
    LVVariant,
)

from src.descriptors import TypeDescriptor, TypeDescriptorID
from src.serialization import SerializationContext, ISerializable
from src.auto_flatten import lvflatten, lvunflatten, _auto_infer_type
from src.lv_serializer import LVSerializer
from src.decorators import lvclass

__all__ = [
    # Main API
    'lvflatten',
    'lvunflatten',
    'LVSerializer',
    
    # Types
    'LVType',
    'LVNumeric',
    'LVBoolean',
    'LVString',
    'LVArray',
    'LVCluster',
    'LVObject',
    'LVObjectMetadata',
    'LVVariant',
    
    # Descriptors
    'TypeDescriptor',
    'TypeDescriptorID',
    
    # Context
    'SerializationContext',
    'ISerializable',
    
    # Decorators
    'lvclass',
    
    # Internal (for advanced users)
    '_auto_infer_type',
]
