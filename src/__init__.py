"""
AF-Serializer - LabVIEW data serialization library for Python

This library provides automatic serialization and deserialization of Python data
structures to LabVIEW-compatible binary format.
"""

# Core types
from .types import (
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

# Type descriptors
from .descriptors import TypeDescriptor, TypeDescriptorID

# Serialization context
from .serialization import SerializationContext, ISerializable

# High-level API
from .auto_flatten import lvflatten, lvunflatten, _auto_infer_type
from .lv_serializer import LVSerializer

# Decorators
from .decorators import lvclass

__version__ = '1.0.0'

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
