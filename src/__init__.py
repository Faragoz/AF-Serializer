"""
Construct-based LabVIEW Serialization Implementation.

This module provides an implementation of AF-Serializer using
the Construct library for declarative binary format definitions.

Key Features:
    - Declarative type definitions using Construct (Struct, PrefixedArray)
    - Type hints for all functions
    - Big-endian byte order (network byte order)
    - Validated against real LabVIEW HEX examples
    - Automatic class registry for deserialization

Declarative Approach:
    - LVCluster uses Struct internally for field definitions
    - LVArray1D uses PrefixedArray for simple 1D arrays
    - LVObject uses declarative VersionStruct and ClusterDataStruct
    - All types can be composed using Construct's declarative syntax

Public API:
    - lvflatten: Serialize Python data to LabVIEW format
    - lvunflatten: Deserialize LabVIEW data to Python (automatic class detection)
    
Basic Types:
    - LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64
    - LVDouble, LVSingle
    - LVBoolean
    - LVString

Compound Types:
    - LVArray: N-dimensional arrays (auto-detects dimensions)
    - LVArray1D: Simple 1D arrays using declarative PrefixedArray
    - LVCluster: Heterogeneous collections using declarative Struct

Object Types:
    - LVObject: LabVIEW objects with inheritance support
    - @lvclass decorator: Mark Python classes as LabVIEW Objects

Usage:
    >>> from src import lvclass, lvflatten, lvunflatten
    >>> 
    >>> @lvclass(library="MyLib", class_name="MyClass")
    >>> class MyClass:
    >>>     message: str
    >>>     code: int
    >>> 
    >>> obj = MyClass()
    >>> obj.message = "Hello"
    >>> obj.code = 42
    >>> 
    >>> data = lvflatten(obj)   # Serialize to bytes
    >>> restored = lvunflatten(data)  # Automatically returns MyClass instance
    >>> 
    >>> assert isinstance(restored, MyClass)
    >>> assert restored.message == "Hello"
    >>> assert restored.code == 42

Declarative Examples:
    >>> # Using declarative Struct directly
    >>> from construct import Struct, Int32ub
    >>> from src import LVString
    >>> 
    >>> MyStruct = Struct(
    ...     "name" / LVString,
    ...     "value" / Int32ub,
    ... )
    >>> 
    >>> # Using declarative PrefixedArray for 1D arrays
    >>> from src import LVArray1D, LVI32
    >>> arr = LVArray1D(LVI32)
    >>> data = arr.build([1, 2, 3])
"""

from .api import (
    lvflatten,
    lvunflatten,
    flatten_i32,
    unflatten_i32,
    flatten_double,
    unflatten_double,
    flatten_string,
    unflatten_string,
    flatten_boolean,
    unflatten_boolean,
)

from .basic_types import (
    # Construct definitions
    LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64,
    LVDouble, LVSingle,
    LVBoolean,
    LVString,
    # Type aliases
    LVI32Type, LVU32Type, LVI16Type, LVU16Type, LVI8Type, LVU8Type,
    LVI64Type, LVU64Type,
    LVDoubleType, LVSingleType,
    LVBooleanType,
    LVStringType,
)

from .compound_types import (
    # Compound type factories
    LVArray,
    LVArray1D,
    LVCluster,
    # Type aliases
    LVArrayType,
    LVClusterType,
)

from .objects import (
    # Object type factory
    LVObject,
    # Helper functions
    create_empty_lvobject,
    create_lvobject,
    # Type alias
    LVObjectType,
    # Declarative structs (for advanced usage)
    VersionStruct,
    ClusterDataStruct,
)

from .decorators import (
    # Decorators
    lvclass,
    lvfield,
    # Helper functions
    is_lvclass,
    get_lvclass_by_name,
    # Registry (for testing/debugging)
    _LVCLASS_REGISTRY,
)

__all__ = [
    # Main API
    "lvflatten",
    "lvunflatten",
    # Convenience functions
    "flatten_i32",
    "unflatten_i32",
    "flatten_double",
    "unflatten_double",
    "flatten_string",
    "unflatten_string",
    "flatten_boolean",
    "unflatten_boolean",
    # Basic type definitions
    "LVI32", "LVU32", "LVI16", "LVU16", "LVI8", "LVU8", "LVI64", "LVU64",
    "LVDouble", "LVSingle",
    "LVBoolean",
    "LVString",
    # Basic type aliases
    "LVI32Type", "LVU32Type", "LVI16Type", "LVU16Type", "LVI8Type", "LVU8Type",
    "LVI64Type", "LVU64Type",
    "LVDoubleType", "LVSingleType",
    "LVBooleanType",
    "LVStringType",
    # Compound types
    "LVArray",
    "LVArray1D",
    "LVCluster",
    "LVArrayType",
    "LVClusterType",
    # Object types
    "LVObject",
    "create_empty_lvobject",
    "create_lvobject",
    "LVObjectType",
    # Declarative structs (for advanced usage)
    "VersionStruct",
    "ClusterDataStruct",
    # Decorators and helpers
    "lvclass",
    "lvfield",
    "is_lvclass",
    "get_lvclass_by_name",
    "_LVCLASS_REGISTRY",
]

__version__ = "0.3.0"
