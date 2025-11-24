#!/usr/bin/env python3
"""
Examples demonstrating the Construct-based LabVIEW serialization implementation.

This script shows how to use the new construct_impl module for basic types.
"""

from src import (
    lvflatten, lvunflatten,
    LVI32, LVU32, LVI16, LVI64,
    LVDouble, LVSingle,
    LVBoolean, LVString,
)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def main():
    print("\n🚀 Construct-based LabVIEW Serialization Examples")
    
    # ========================================================================
    # Integer Types
    # ========================================================================
    print_section("Integer Types")
    
    # I32 (Signed 32-bit)
    value = 42
    data = lvflatten(value, LVI32)
    print(f"I32 ({value}): {data.hex()}")
    print(f"  Deserialized: {lvunflatten(data, LVI32)}")
    
    # U32 (Unsigned 32-bit)
    value = 4294967295  # Max U32
    data = lvflatten(value, LVU32)
    print(f"U32 ({value}): {data.hex()}")
    print(f"  Deserialized: {lvunflatten(data, LVU32)}")
    
    # I64 (Signed 64-bit)
    value = 9223372036854775807  # Max I64
    data = lvflatten(value, LVI64)
    print(f"I64 ({value}): {data.hex()}")
    print(f"  Deserialized: {lvunflatten(data, LVI64)}")
    
    # ========================================================================
    # Floating Point Types
    # ========================================================================
    print_section("Floating Point Types")
    
    # Double (64-bit IEEE 754)
    value = 3.14159265358979323846
    data = lvflatten(value, LVDouble)
    print(f"Double ({value}): {data.hex()}")
    print(f"  Deserialized: {lvunflatten(data, LVDouble)}")
    
    # Single (32-bit IEEE 754)
    value = 3.14
    data = lvflatten(value, LVSingle)
    print(f"Single ({value}): {data.hex()}")
    print(f"  Deserialized: {lvunflatten(data, LVSingle)}")
    
    # ========================================================================
    # Boolean Type
    # ========================================================================
    print_section("Boolean Type")
    
    for value in [True, False]:
        data = lvflatten(value, LVBoolean)
        print(f"Boolean ({value}): {data.hex()}")
        print(f"  Deserialized: {lvunflatten(data, LVBoolean)}")
    
    # ========================================================================
    # String Type
    # ========================================================================
    print_section("String Type (Pascal String with UTF-8)")
    
    strings = [
        "Hello",
        "Hello World",
        "Hello, LabVIEW!",
        "",  # Empty string
        "UTF-8: café, naïve",
        "Emoji: 👋 🌍",
    ]
    
    for value in strings:
        data = lvflatten(value, LVString)
        display_value = value if value else "(empty)"
        print(f'String "{display_value}": {data.hex()}')
        print(f'  Deserialized: "{lvunflatten(data, LVString)}"')
    
    # ========================================================================
    # Auto-Detection (without type hint)
    # ========================================================================
    print_section("Auto-Detection (without explicit type hint)")
    
    print("Auto-detect int as I32:")
    value = 42
    data = lvflatten(value)  # No type hint
    print(f"  {value} -> {data.hex()}")
    
    print("\nAuto-detect float as Double:")
    value = 3.14
    data = lvflatten(value)  # No type hint
    print(f"  {value} -> {data.hex()}")
    
    print("\nAuto-detect str as String:")
    value = "Hello"
    data = lvflatten(value)  # No type hint
    print(f"  '{value}' -> {data.hex()}")
    
    print("\nAuto-detect bool as Boolean:")
    value = True
    data = lvflatten(value)  # No type hint
    print(f"  {value} -> {data.hex()}")
    
    # ========================================================================
    # Round-Trip Examples
    # ========================================================================
    print_section("Round-Trip Tests (serialize → deserialize → compare)")
    
    test_cases = [
        (42, LVI32, "I32"),
        (3.14159265358979323846, LVDouble, "Double"),
        ("Hello, LabVIEW!", LVString, "String"),
        (True, LVBoolean, "Boolean"),
    ]
    
    for original, type_hint, type_name in test_cases:
        serialized = lvflatten(original, type_hint)
        deserialized = lvunflatten(serialized, type_hint)
        match = "✅" if original == deserialized else "❌"
        print(f"{match} {type_name}: {original} == {deserialized}")
    
    # ========================================================================
    # Validation Examples
    # ========================================================================
    print_section("Validation Examples")
    
    print("✅ Valid Boolean (0x01 = True):")
    data = bytes.fromhex("01")
    result = lvunflatten(data, LVBoolean)
    print(f"  {data.hex()} -> {result}")
    
    print("\n❌ Invalid Boolean (0x02) - will raise ValidationError:")
    try:
        data = bytes.fromhex("02")
        result = lvunflatten(data, LVBoolean)
        print(f"  {data.hex()} -> {result}")
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 60)
    print("  All examples completed successfully! ✨")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
