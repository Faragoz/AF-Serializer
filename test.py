"""
Example demonstrating the new simplified AF-Serializer API.

The key features are:
1. lvflatten(obj) - Serialize any @lvclass instance to bytes
2. lvunflatten(data) - Automatically identify and populate the correct class
"""

from af_serializer import (
    lvclass, lvflatten, lvunflatten,
    LVU16, LVI32, LVString, LVBoolean, LVDouble, LVArray, LVU8
)


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
# Example: Simple deserialization from HEX data
# ============================================================================
print("=== Example: Simple deserialization from HEX data ===")

@lvclass(version=(1, 0, 0, 6))
class Test():
    pass

@lvclass(version=(1, 0, 0, 4))
class Child(Test):
    boolean: LVBoolean
    number: LVI32
    double: LVDouble
    text: LVString
    number_array: LVArray(LVU8)
    string_array: LVArray(LVString)

data = bytes.fromhex("0000 0002 0F0D 4368 696C 642E 6C76 636C 6173 7300 0001 0000 0000 0004 0001 0000 0000 0006 0000 0000 0000 0042 0100 0002 6640 091E B851 EB85 1F00 0000 0C48 656C 6C6F 2050 7974 686F 6E00 0000 0336 374A 0000 0003 0000 0005 4861 62ED 6100 0000 0375 F161 0000 0006 7665 7A2E 2E2E ")
print(f"Serialized bytes: {data.hex()}")

child = Child()
child.boolean = True
child.number = 614
child.double = 3.14
child.text = "Hello Python"
child.number_array = [54,55,74]
child.string_array = ["Había","uña","vez..."]

# Deserialize with lvunflatten() - NO parameters needed!
restored = lvunflatten(data)
print(f"Restored type: {type(restored).__name__}")
#print(f"{restored.__annotations__}")
print(f"Boolean: {restored.boolean}")
print(f"Number: {restored.number}")
print(f"Double: {restored.double}")
print(f"Text: {restored.text}")
print(f"Number Array: {restored.number_array}")
print(f"String Array: {restored.string_array}")

# Verify
assert isinstance(restored, Child)
assert restored.boolean == child.boolean
assert restored.number == child.number
assert abs(restored.double - child.double) < 1e-10
assert restored.text == child.text
assert all(a == b for a, b in zip(restored.number_array, child.number_array))
print("✓ Deserialization successful!")

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