"""
LabVIEW Basic Data Types using Construct Library.

This module implements LabVIEW basic data types using the Construct library,
providing declarative binary format definitions with type hints.

All types use big-endian byte order (network byte order) as required by LabVIEW.

Supported Types:
    - Integers: I32, U32, I16, U16, I8, U8, I64, U64
    - Floating Point: Double (Float64), Single (Float32)
    - Boolean: 8-bit boolean (0x00 or 0x01)
    - String: Pascal String with Int32ub length prefix + UTF-8 encoding
"""

from typing import TypeAlias, Annotated
from construct import (
    Struct,
    Int8sb, Int8ub,
    Int16sb, Int16ub,
    Int32sb, Int32ub,
    Int64sb, Int64ub,
    Float32b, Float64b,
    Byte,
    Bytes,
    this,
    Adapter,
    ValidationError,
)


# ============================================================================
# Type Aliases for Type Hints
# ============================================================================

LVI32Type: TypeAlias = Annotated[int, "LabVIEW I32 (signed 32-bit integer)"]
LVU32Type: TypeAlias = Annotated[int, "LabVIEW U32 (unsigned 32-bit integer)"]
LVI16Type: TypeAlias = Annotated[int, "LabVIEW I16 (signed 16-bit integer)"]
LVU16Type: TypeAlias = Annotated[int, "LabVIEW U16 (unsigned 16-bit integer)"]
LVI8Type: TypeAlias = Annotated[int, "LabVIEW I8 (signed 8-bit integer)"]
LVU8Type: TypeAlias = Annotated[int, "LabVIEW U8 (unsigned 8-bit integer)"]
LVI64Type: TypeAlias = Annotated[int, "LabVIEW I64 (signed 64-bit integer)"]
LVU64Type: TypeAlias = Annotated[int, "LabVIEW U64 (unsigned 64-bit integer)"]
LVDoubleType: TypeAlias = Annotated[float, "LabVIEW Double (64-bit IEEE 754)"]
LVSingleType: TypeAlias = Annotated[float, "LabVIEW Single (32-bit IEEE 754)"]
LVBooleanType: TypeAlias = Annotated[bool, "LabVIEW Boolean (8-bit, 0x00 or 0x01)"]
LVStringType: TypeAlias = Annotated[str, "LabVIEW String (Pascal String, UTF-8)"]


# ============================================================================
# Integer Types (Big-Endian)
# ============================================================================

LVI32 = Int32sb
"""LabVIEW I32: Signed 32-bit integer, big-endian."""

LVU32 = Int32ub
"""LabVIEW U32: Unsigned 32-bit integer, big-endian."""

LVI16 = Int16sb
"""LabVIEW I16: Signed 16-bit integer, big-endian."""

LVU16 = Int16ub
"""LabVIEW U16: Unsigned 16-bit integer, big-endian."""

LVI8 = Int8sb
"""LabVIEW I8: Signed 8-bit integer."""

LVU8 = Int8ub
"""LabVIEW U8: Unsigned 8-bit integer."""

LVI64 = Int64sb
"""LabVIEW I64: Signed 64-bit integer, big-endian."""

LVU64 = Int64ub
"""LabVIEW U64: Unsigned 64-bit integer, big-endian."""


# ============================================================================
# Floating Point Types (Big-Endian IEEE 754)
# ============================================================================

LVDouble = Float64b
"""LabVIEW Double: 64-bit floating point, big-endian IEEE 754."""

LVSingle = Float32b
"""LabVIEW Single: 32-bit floating point, big-endian IEEE 754."""


# ============================================================================
# Boolean Adapter with Validation
# ============================================================================

class BooleanAdapter(Adapter):
    """
    Adapter for LabVIEW Boolean type.
    
    LabVIEW represents booleans as a single byte:
    - 0x00 = False
    - 0x01 = True
    
    This adapter validates that only 0x00 or 0x01 values are used.
    """
    
    def _decode(self, obj: int, context, path) -> bool:
        """Convert byte value to Python bool."""
        if obj not in (0, 1):
            raise ValidationError(f"Invalid boolean value: {obj:#04x}. Must be 0x00 or 0x01.")
        return bool(obj)
    
    def _encode(self, obj: bool, context, path) -> int:
        """Convert Python bool to byte value."""
        return 1 if obj else 0


LVBoolean = BooleanAdapter(Byte)
"""LabVIEW Boolean: 8-bit boolean with validation (0x00 or 0x01)."""


# ============================================================================
# String Type (Pascal String with Int32ub Prefix)
# ============================================================================

class StringAdapter(Adapter):
    """
    Adapter for LabVIEW String type.
    
    LabVIEW strings are Pascal Strings with:
    - Int32ub (4 bytes, big-endian) length prefix
    - UTF-8 encoded string data
    
    Format: [length (I32)] + [UTF-8 bytes]
    Example: "Hello" -> 00000005 48656C6C6F
    """
    
    def _decode(self, obj: dict, context, path) -> str:
        """Convert bytes to Python string."""
        return obj["data"].decode("utf-8")
    
    def _encode(self, obj: str, context, path) -> dict:
        """Convert Python string to bytes with length prefix."""
        data = obj.encode("utf-8")
        return {"length": len(data), "data": data}


LVString = StringAdapter(
    Struct(
        "length" / Int32ub,
        "data" / Bytes(this.length),
    )
)
"""
LabVIEW String: Pascal String with Int32ub length prefix + UTF-8 encoding.

Format: [length (I32)] + [UTF-8 bytes]
Example: "Hello" -> 00000005 48656C6C6F
"""


# ============================================================================
# TODO: Phase 2 - Compound Types
# ============================================================================

# TODO: Implement LVArray1D
# Format: [num_elements (I32)] + [elements...]
# Example (3 elements: 1, 2, 3):
#   0000 0003 0000 0001 0000 0002 0000 0003

# TODO: Implement LVArray2D
# Format: [num_dims (I32)] [dim1_size] [dim2_size] + [elements...]
# Example (2×3 elements):
#   0000 0002 0000 0003 0000 0001 0000 0002 0000 0003 0000 0001 0000 0002 0000 0003

# TODO: Implement LVCluster
# Format: Direct concatenation of elements WITHOUT header
# IMPORTANT: NO header of element count, data concatenated directly
# Example (String "Hello, LabVIEW!" + Enum 0):
#   0000 0010 4865 6C6C 6F2C 204C 6162 5649 4557 2100 0000


# ============================================================================
# TODO: Phase 3 - LVObject Types
# ============================================================================

# TODO: Implement LVObject
# Format:
#   - NumLevels (I32): 0x00000000 for empty LabVIEW Object
#   - ClassName: Total length (I8) + Pascal Strings + End marker (0x00) + Padding
#   - VersionList: Version numbers for each contained object
#   - ClusterData: State data for each contained object
#
# Example (Empty LVObject):
#   0000 0000
#
# Example (Actor Object - empty):
#   0000 0001 2515 4163 746F 7220 4672 616D 6577 6F72 6B2E 6C76 6C69 620D
#   4163 746F 722E 6C76 636C 6173 7300 0000 0000 0000 0000 0000
