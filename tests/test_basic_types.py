"""
Unit tests for LabVIEW basic types implementation using Construct.

These tests validate serialization and deserialization of basic LabVIEW types
against real HEX examples from LabVIEW documentation.
"""

import math
import pytest
from construct import ValidationError, ConstructError

from src import (
    lvflatten, lvunflatten,
    LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64,
    LVDouble, LVSingle, LVBoolean, LVString,
)


# ============================================================================
# I32 Tests (Signed 32-bit Integer)
# ============================================================================

def test_i32_serialization_with_positive_value():
    """Validate I32 serialization for positive value against real LabVIEW hex output."""
    value = 42
    expected_hex = "0000002a"
    
    result = lvflatten(value, LVI32)
    
    assert result.hex() == expected_hex


def test_i32_serialization_with_zero():
    """Validate I32 serialization for zero."""
    value = 0
    expected_hex = "00000000"
    
    result = lvflatten(value, LVI32)
    
    assert result.hex() == expected_hex


def test_i32_serialization_with_negative_value():
    """Validate I32 serialization for negative value."""
    value = -1
    expected_hex = "ffffffff"
    
    result = lvflatten(value, LVI32)
    
    assert result.hex() == expected_hex


def test_i32_serialization_with_max_value():
    """Validate I32 serialization for maximum value."""
    value = 2147483647  # 0x7FFFFFFF
    expected_hex = "7fffffff"
    
    result = lvflatten(value, LVI32)
    
    assert result.hex() == expected_hex


def test_i32_serialization_with_min_value():
    """Validate I32 serialization for minimum value."""
    value = -2147483648  # 0x80000000
    expected_hex = "80000000"
    
    result = lvflatten(value, LVI32)
    
    assert result.hex() == expected_hex


def test_i32_deserialization_roundtrip():
    """Test I32 serialize → deserialize → compare."""
    original = 12345
    
    serialized = lvflatten(original, LVI32)
    deserialized = lvunflatten(serialized, LVI32)
    
    assert deserialized == original


@pytest.mark.parametrize("value,expected_hex", [
    (1, "00000001"),
    (2, "00000002"),
    (3, "00000003"),
    (255, "000000ff"),
    (256, "00000100"),
    (65535, "0000ffff"),
    (65536, "00010000"),
])
def test_i32_serialization_parametrized(value, expected_hex):
    """Test I32 serialization with multiple values."""
    result = lvflatten(value, LVI32)
    assert result.hex() == expected_hex


# ============================================================================
# U32 Tests (Unsigned 32-bit Integer)
# ============================================================================

def test_u32_serialization_with_large_value():
    """Validate U32 serialization for large unsigned value."""
    value = 4294967295  # 0xFFFFFFFF (max U32)
    expected_hex = "ffffffff"
    
    result = lvflatten(value, LVU32)
    
    assert result.hex() == expected_hex


def test_u32_deserialization_roundtrip():
    """Test U32 serialize → deserialize → compare."""
    original = 3000000000
    
    serialized = lvflatten(original, LVU32)
    deserialized = lvunflatten(serialized, LVU32)
    
    assert deserialized == original


# ============================================================================
# I16 Tests (Signed 16-bit Integer)
# ============================================================================

def test_i16_serialization_with_positive_value():
    """Validate I16 serialization."""
    value = 1000
    expected_hex = "03e8"
    
    result = lvflatten(value, LVI16)
    
    assert result.hex() == expected_hex


def test_i16_deserialization_roundtrip():
    """Test I16 serialize → deserialize → compare."""
    original = -500
    
    serialized = lvflatten(original, LVI16)
    deserialized = lvunflatten(serialized, LVI16)
    
    assert deserialized == original


# ============================================================================
# I8 Tests (Signed 8-bit Integer)
# ============================================================================

def test_i8_serialization_with_positive_value():
    """Validate I8 serialization."""
    value = 127
    expected_hex = "7f"
    
    result = lvflatten(value, LVI8)
    
    assert result.hex() == expected_hex


def test_i8_serialization_with_negative_value():
    """Validate I8 serialization for negative value."""
    value = -128
    expected_hex = "80"
    
    result = lvflatten(value, LVI8)
    
    assert result.hex() == expected_hex


# ============================================================================
# I64 Tests (Signed 64-bit Integer)
# ============================================================================

def test_i64_serialization_with_large_value():
    """Validate I64 serialization."""
    value = 9223372036854775807  # Max I64
    expected_hex = "7fffffffffffffff"
    
    result = lvflatten(value, LVI64)
    
    assert result.hex() == expected_hex


def test_i64_deserialization_roundtrip():
    """Test I64 serialize → deserialize → compare."""
    original = 1234567890123456789
    
    serialized = lvflatten(original, LVI64)
    deserialized = lvunflatten(serialized, LVI64)
    
    assert deserialized == original


# ============================================================================
# Double Tests (64-bit IEEE 754)
# ============================================================================

def test_double_serialization_with_pi():
    """Validate Double serialization against real LabVIEW hex output."""
    value = 3.14159265358979323846
    # Expected: IEEE 754 double precision representation of pi
    expected_hex = "400921fb54442d18"
    
    result = lvflatten(value, LVDouble)
    
    assert result.hex() == expected_hex


def test_double_serialization_with_zero():
    """Validate Double serialization for zero."""
    value = 0.0
    expected_hex = "0000000000000000"
    
    result = lvflatten(value, LVDouble)
    
    assert result.hex() == expected_hex


def test_double_serialization_with_negative():
    """Validate Double serialization for negative value."""
    value = -1.5
    expected_hex = "bff8000000000000"
    
    result = lvflatten(value, LVDouble)
    
    assert result.hex() == expected_hex


def test_double_deserialization_roundtrip():
    """Test Double serialize → deserialize → compare."""
    original = 123.456
    
    serialized = lvflatten(original, LVDouble)
    deserialized = lvunflatten(serialized, LVDouble)
    
    assert abs(deserialized - original) < 1e-10


@pytest.mark.parametrize("value", [
    0.0,
    1.0,
    -1.0,
    3.14159265358979323846,
    1e10,
    1e-10,
    -999.999,
])
def test_double_roundtrip_parametrized(value):
    """Test Double roundtrip with multiple values."""
    serialized = lvflatten(value, LVDouble)
    deserialized = lvunflatten(serialized, LVDouble)
    
    assert abs(deserialized - value) < 1e-10


# ============================================================================
# Single Tests (32-bit IEEE 754)
# ============================================================================

def test_single_serialization():
    """Validate Single (Float32) serialization."""
    value = 3.14
    expected_hex = "4048f5c3"  # IEEE 754 single precision
    
    result = lvflatten(value, LVSingle)
    
    assert result.hex() == expected_hex


def test_single_deserialization_roundtrip():
    """Test Single serialize → deserialize → compare."""
    original = 42.5
    
    serialized = lvflatten(original, LVSingle)
    deserialized = lvunflatten(serialized, LVSingle)
    
    assert abs(deserialized - original) < 1e-5


# ============================================================================
# Boolean Tests
# ============================================================================

def test_boolean_serialization_true():
    """Validate Boolean serialization for True against real LabVIEW hex output."""
    value = True
    expected_hex = "01"
    
    result = lvflatten(value, LVBoolean)
    
    assert result.hex() == expected_hex


def test_boolean_serialization_false():
    """Validate Boolean serialization for False."""
    value = False
    expected_hex = "00"
    
    result = lvflatten(value, LVBoolean)
    
    assert result.hex() == expected_hex


def test_boolean_deserialization_true():
    """Test Boolean deserialization for True."""
    data = bytes.fromhex("01")
    
    result = lvunflatten(data, LVBoolean)
    
    assert result is True


def test_boolean_deserialization_false():
    """Test Boolean deserialization for False."""
    data = bytes.fromhex("00")
    
    result = lvunflatten(data, LVBoolean)
    
    assert result is False


def test_boolean_deserialization_invalid_value():
    """Test Boolean deserialization rejects invalid values."""
    data = bytes.fromhex("02")  # Invalid: must be 0x00 or 0x01
    
    with pytest.raises(ValidationError):
        lvunflatten(data, LVBoolean)


def test_boolean_roundtrip():
    """Test Boolean serialize → deserialize → compare."""
    for original in [True, False]:
        serialized = lvflatten(original, LVBoolean)
        deserialized = lvunflatten(serialized, LVBoolean)
        assert deserialized == original


# ============================================================================
# String Tests
# ============================================================================

def test_string_serialization_hello():
    """Validate String serialization against real LabVIEW hex output."""
    value = "Hello"
    expected_hex = "0000000548656c6c6f"
    # Breakdown: 00000005 (length=5) + 48656c6c6f ("Hello")
    
    result = lvflatten(value, LVString)
    
    assert result.hex() == expected_hex


def test_string_serialization_hello_world():
    """Validate String serialization for longer string."""
    value = "Hello World"
    expected_hex = "0000000b48656c6c6f20576f726c64"
    # Breakdown: 0000000b (length=11) + UTF-8 bytes
    
    result = lvflatten(value, LVString)
    
    assert result.hex() == expected_hex


def test_string_serialization_empty():
    """Validate String serialization for empty string."""
    value = ""
    expected_hex = "00000000"
    
    result = lvflatten(value, LVString)
    
    assert result.hex() == expected_hex


def test_string_serialization_with_special_chars():
    """Validate String serialization with special characters."""
    value = "Hello, LabVIEW!"
    expected_hex = "0000000f48656c6c6f2c204c616256494557 21"
    # Remove spaces in expected
    expected_hex = expected_hex.replace(" ", "")
    
    result = lvflatten(value, LVString)
    
    assert result.hex() == expected_hex


def test_string_deserialization():
    """Test String deserialization."""
    data = bytes.fromhex("0000000548656c6c6f")
    
    result = lvunflatten(data, LVString)
    
    assert result == "Hello"


def test_string_roundtrip():
    """Test String serialize → deserialize → compare."""
    original = "Hello, LabVIEW!"
    
    serialized = lvflatten(original, LVString)
    deserialized = lvunflatten(serialized, LVString)
    
    assert deserialized == original


@pytest.mark.parametrize("value", [
    "",
    "a",
    "Hello",
    "Hello World",
    "Hello, LabVIEW!",
    "UTF-8: café, naïve, 日本語",
    "Special chars: !@#$%^&*()",
])
def test_string_roundtrip_parametrized(value):
    """Test String roundtrip with multiple values."""
    serialized = lvflatten(value, LVString)
    deserialized = lvunflatten(serialized, LVString)
    
    assert deserialized == value


# ============================================================================
# Auto-detection Tests (lvflatten without type_hint)
# ============================================================================

def test_auto_detect_int():
    """Test auto-detection of int as I32."""
    value = 42
    
    result = lvflatten(value)
    
    assert result.hex() == "0000002a"


def test_auto_detect_float():
    """Test auto-detection of float as Double."""
    value = 3.14159265358979323846
    expected_hex = "400921fb54442d18"
    
    result = lvflatten(value)
    
    assert result.hex() == expected_hex


def test_auto_detect_str():
    """Test auto-detection of str as String."""
    value = "Hello"
    expected_hex = "0000000548656c6c6f"
    
    result = lvflatten(value)
    
    assert result.hex() == expected_hex


def test_auto_detect_bool():
    """Test auto-detection of bool as Boolean."""
    result_true = lvflatten(True)
    result_false = lvflatten(False)
    
    assert result_true.hex() == "01"
    assert result_false.hex() == "00"


def test_auto_detect_unsupported_type():
    """Test auto-detection raises TypeError for unsupported types."""
    value = object()
    
    with pytest.raises(TypeError, match="Unsupported data type"):
        lvflatten(value)


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_i32_overflow():
    """Test I32 with value exceeding 32-bit range."""
    value = 2**32  # Exceeds I32 range
    
    with pytest.raises(ConstructError):
        lvflatten(value, LVI32)


def test_string_with_utf8():
    """Test String serialization with UTF-8 characters."""
    value = "日本語"  # Japanese characters
    
    serialized = lvflatten(value, LVString)
    deserialized = lvunflatten(serialized, LVString)
    
    assert deserialized == value


def test_string_with_emoji():
    """Test String serialization with emoji."""
    value = "Hello 👋 World 🌍"
    
    serialized = lvflatten(value, LVString)
    deserialized = lvunflatten(serialized, LVString)
    
    assert deserialized == value


def test_double_special_values():
    """Test Double serialization with special values."""
    # Test positive infinity
    serialized = lvflatten(float('inf'), LVDouble)
    deserialized = lvunflatten(serialized, LVDouble)
    assert deserialized == float('inf')
    
    # Test negative infinity
    serialized = lvflatten(float('-inf'), LVDouble)
    deserialized = lvunflatten(serialized, LVDouble)
    assert deserialized == float('-inf')
    
    # Test NaN (NaN != NaN, so check using math.isnan)
    serialized = lvflatten(float('nan'), LVDouble)
    deserialized = lvunflatten(serialized, LVDouble)
    assert math.isnan(deserialized)


# ============================================================================
# Integration Tests
# ============================================================================

def test_multiple_types_serialization():
    """Test serialization of multiple types in sequence."""
    # This tests that each type works independently
    i32_data = lvflatten(42, LVI32)
    double_data = lvflatten(3.14, LVDouble)
    string_data = lvflatten("Hello", LVString)
    bool_data = lvflatten(True, LVBoolean)
    
    # Verify each serialization
    assert i32_data.hex() == "0000002a"
    assert double_data.hex()[:4] == "4009"  # First 2 bytes of pi
    assert string_data.hex() == "0000000548656c6c6f"
    assert bool_data.hex() == "01"


def test_convenience_functions():
    """Test convenience functions for common types."""
    from src import (
        flatten_i32, unflatten_i32,
        flatten_double, unflatten_double,
        flatten_string, unflatten_string,
        flatten_boolean, unflatten_boolean,
    )
    
    # I32
    assert flatten_i32(42).hex() == "0000002a"
    assert unflatten_i32(bytes.fromhex("0000002a")) == 42
    
    # Double
    serialized_double = flatten_double(3.14)
    assert abs(unflatten_double(serialized_double) - 3.14) < 1e-10
    
    # String
    assert flatten_string("Hello").hex() == "0000000548656c6c6f"
    assert unflatten_string(bytes.fromhex("0000000548656c6c6f")) == "Hello"
    
    # Boolean
    assert flatten_boolean(True).hex() == "01"
    assert unflatten_boolean(bytes.fromhex("01")) is True
