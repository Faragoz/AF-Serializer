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
    Int8sb, Int8ub,
    Int16sb, Int16ub,
    Int32sb, Int32ub,
    Int64sb, Int64ub,
    Float32b, Float64b,
    Byte,
    PascalString,
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

from construct import PascalString

LVString = PascalString(Int32ub, "utf-8")
"""
LabVIEW String: Pascal String with Int32ub length prefix + UTF-8 encoding.

Uses Construct's built-in PascalString for clean, declarative definition.

Format: [length (I32)] + [UTF-8 bytes]
Example: "Hello" -> 00000005 48656C6C6F
"""


# ============================================================================
# NOTE: Compound Types and Objects
# ============================================================================

# Compound types (Arrays, Clusters) are implemented in compound_types.py
# LVObject types are implemented in objects.py
# These modules use the basic types defined above.
