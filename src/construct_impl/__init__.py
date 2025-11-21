"""
Construct-based LabVIEW Serialization Implementation.

This module provides an alternative implementation of AF-Serializer using
the Construct library for declarative binary format definitions.

Key Features:
    - Declarative type definitions using Construct
    - Type hints for all functions
    - Big-endian byte order (network byte order)
    - Validated against real LabVIEW HEX examples

Public API:
    - lvflatten: Serialize Python data to LabVIEW format
    - lvunflatten: Deserialize LabVIEW data to Python
    
Basic Types:
    - LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64
    - LVDouble, LVSingle
    - LVBoolean
    - LVString

Usage:
    >>> from src.construct_impl import lvflatten, lvunflatten, LVI32
    >>> data = lvflatten(42)
    >>> print(data.hex())
    0000002a
    >>> value = lvunflatten(data, LVI32)
    >>> print(value)
    42
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
    # Type definitions
    "LVI32", "LVU32", "LVI16", "LVU16", "LVI8", "LVU8", "LVI64", "LVU64",
    "LVDouble", "LVSingle",
    "LVBoolean",
    "LVString",
    # Type aliases
    "LVI32Type", "LVU32Type", "LVI16Type", "LVU16Type", "LVI8Type", "LVU8Type",
    "LVI64Type", "LVU64Type",
    "LVDoubleType", "LVSingleType",
    "LVBooleanType",
    "LVStringType",
]

__version__ = "0.1.0"
