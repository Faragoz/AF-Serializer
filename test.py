"""
Example demonstrating the new simplified AF-Serializer API.

The key features are:
1. lvflatten(obj) - Serialize any @lvclass instance to bytes
2. lvunflatten(data) - Automatically identify and populate the correct class
"""

from src import lvclass, lvflatten, lvunflatten, LVU16, LVI32, LVString


# Define LabVIEW class hierarchy using @lvclass decorator
@lvclass(library="Actor Framework", class_name="Message")
class Message:
    pass


@lvclass(library="Serializable Message", class_name="Serializable Msg",
         version=(1, 0, 0, 7))
class SerializableMsg(Message):
    pass


@lvclass(library="Commander", class_name="echo general Msg")
class EchoMsg(SerializableMsg):
    message: str      # → LVString
    code: LVU16       # → U16 (2 bytes)


# ============================================================================
# Example: Simple roundtrip serialization/deserialization
# ============================================================================
print("=== Example: Simple Roundtrip ===")

msg = EchoMsg()
msg.message = "Hello World!"
msg.code = 42

# Serialize with lvflatten()
data = lvflatten(msg)
print(f"Serialized bytes: {data.hex()}")

# Deserialize with lvunflatten() - NO parameters needed!
restored = lvunflatten(data)
print(f"Restored type: {type(restored).__name__}")
print(f"Message: {restored.message}")
print(f"Code: {restored.code}")

# Verify
assert isinstance(restored, EchoMsg)
assert restored.message == "Hello World!"
assert restored.code == 42
print("✓ Roundtrip successful!")

# ============================================================================
# Example: 3-level inheritance
# ============================================================================
print("\n=== Example: 3-Level Inheritance ===")

# The EchoMsg class inherits from SerializableMsg -> Message
# This creates 3 levels in the LabVIEW Object

msg2 = EchoMsg()
msg2.message = "Testing 3-level inheritance"
msg2.code = 123

data2 = lvflatten(msg2)
print(f"Serialized 3-level object: {data2[:8].hex()}...")  # Show first 8 bytes

# First 4 bytes are NumLevels
num_levels = int.from_bytes(data2[:4], 'big')
print(f"NumLevels in binary: {num_levels}")
assert num_levels == 3

restored2 = lvunflatten(data2)
assert isinstance(restored2, EchoMsg)
assert restored2.message == "Testing 3-level inheritance"
assert restored2.code == 123
print("✓ 3-level inheritance works correctly!")

# ============================================================================
# Example: Class with multiple field types
# ============================================================================
print("\n=== Example: Multiple Field Types ===")

@lvclass(library="MyLib", class_name="ComplexClass")
class ComplexClass:
    name: str
    count: LVI32
    value: LVU16

obj = ComplexClass()
obj.name = "Test Object"
obj.count = 100
obj.value = 65535

data3 = lvflatten(obj)
restored3 = lvunflatten(data3)

assert isinstance(restored3, ComplexClass)
assert restored3.name == "Test Object"
assert restored3.count == 100
assert restored3.value == 65535
print(f"Restored: name={restored3.name}, count={restored3.count}, value={restored3.value}")
print("✓ Multiple field types work correctly!")

print("\n=== All examples completed successfully! ===")