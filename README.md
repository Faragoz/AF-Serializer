# AF-Serializer

LabVIEW data serialization library for Python. Serialize Python data structures to LabVIEW-compatible binary format with 100% compatibility based on real HEX examples from LabVIEW.

## Features

- **Simple API** - Use `lvflatten()` to serialize and `lvunflatten()` to deserialize
- **Declarative approach** - Uses Construct library's Struct and PrefixedArray for clean, maintainable code
- **Automatic class detection** - Registry-based automatic class identification during deserialization
- **Auto-detection of Python types** - Automatically infers LabVIEW types from Python data
- **3-level inheritance support** - Full support for LabVIEW class hierarchies
- **Validated against real HEX examples** - All formats validated against LabVIEW documentation

## Installation

```bash
pip install construct  # Required dependency
```

## Quick Start

### Automatic Serialization & Deserialization (Recommended)

Use `lvflatten()` to serialize and `lvunflatten()` to automatically deserialize:

```python
from src import lvclass, lvflatten, lvunflatten, LVU16

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

# Create and populate an instance
msg = EchoMsg()
msg.message = "Hello World!"
msg.code = 42

# Serialize with lvflatten()
data = lvflatten(msg)
print(f"Serialized: {data.hex()}")

# Deserialize with lvunflatten() - NO parameters needed!
restored = lvunflatten(data)
print(f"Restored type: {type(restored).__name__}")  # EchoMsg
print(f"Message: {restored.message}")  # Hello World!
print(f"Code: {restored.code}")  # 42

# Verify
assert isinstance(restored, EchoMsg)
assert restored.message == "Hello World!"
assert restored.code == 42
```

### Basic Types

Use `lvflatten()` to automatically serialize Python data:

```python
from src import lvflatten, lvunflatten, LVI32, LVString

# Simple types - serialize
lvflatten(42)                    # Integer → I32
lvflatten(3.14)                  # Float → Double
lvflatten("Hello World")         # String
lvflatten(True)                  # Boolean

# With explicit type hint - deserialize
data = lvflatten(42)
value = lvunflatten(data, LVI32)  # Returns 42

data = lvflatten("Hello")
text = lvunflatten(data, LVString)  # Returns "Hello"
```

### Arrays

```python
from src import LVArray, LVArray1D, LVI32

# 1D Array (standard)
arr = LVArray(LVI32)
data = arr.build([1, 2, 3])
parsed = arr.parse(data)  # Returns [1, 2, 3]

# 1D Array (declarative PrefixedArray)
arr1d = LVArray1D(LVI32)
data = arr1d.build([1, 2, 3])
parsed = list(arr1d.parse(data))  # Returns [1, 2, 3]

# 2D Array
data = arr.build([[1, 2, 3], [4, 5, 6]])
parsed = arr.parse(data)  # Returns [[1, 2, 3], [4, 5, 6]]

# 3D Array
data_3d = [
    [[7, 0, 0, 0], [8, 0, 0, 0]],
    [[0, 0, 0, 0], [0, 0, 0, 0]]
]
data = arr.build(data_3d)
parsed = arr.parse(data)  # Returns original 3D array
```

### Clusters

```python
from src import LVCluster, LVString, LVI32
from construct import Struct, Int32ub, Int16ub

# Simple cluster using LVCluster (tuple-based)
cluster = LVCluster(LVString, LVI32)
data = cluster.build(("Hello, LabVIEW!", 42))
parsed = cluster.parse(data)  # Returns ("Hello, LabVIEW!", 42)

# Declarative style using Construct's Struct directly (dict-based)
DeclarativeCluster = Struct(
    "name" / LVString,
    "count" / Int32ub,
    "value" / Int16ub,
)
data = DeclarativeCluster.build({"name": "Hello", "count": 10, "value": 5})
parsed = DeclarativeCluster.parse(data)  # Returns Container with named fields
```

## Architecture

The library uses a registry-based system for automatic class detection:

```
src/
├── __init__.py           # Main exports
├── api.py                # lvflatten, lvunflatten
├── decorators.py         # @lvclass decorator and registry
├── objects.py            # LVObject serialization
├── basic_types.py        # LVI32, LVString, etc.
└── compound_types.py     # LVArray, LVCluster
```

## The @lvclass Decorator

The `@lvclass` decorator registers Python classes in a global registry, enabling automatic identification during deserialization:

```python
from src import lvclass, lvflatten, lvunflatten, LVI32

@lvclass(library="MyLib", class_name="MyClass", version=(1, 0, 0, 1))
class MyClass:
    value: LVI32
    name: str

obj = MyClass()
obj.value = 100
obj.name = "Test"

# Serialize
data = lvflatten(obj)

# Deserialize - automatically returns MyClass instance
restored = lvunflatten(data)
assert isinstance(restored, MyClass)
```

### Inheritance Support

The decorator automatically detects inheritance chains:

```python
@lvclass(library="Base", class_name="BaseClass")
class BaseClass:
    pass

@lvclass(library="Derived", class_name="DerivedClass")
class DerivedClass(BaseClass):
    value: LVI32

# This creates a 2-level LVObject
obj = DerivedClass()
obj.value = 42
data = lvflatten(obj)  # num_levels = 2
```

## Supported LabVIEW Types

- **Numeric**: I8, I16, I32, I64, U8, U16, U32, U64, Single, Double
- **Boolean**: 8-bit boolean
- **String**: Length-prefixed strings
- **Array**: 1D, 2D, 3D, and N-dimensional arrays
- **Cluster**: Ordered collections of heterogeneous types
- **Objects**: LabVIEW objects with full inheritance support

## Type Hints

When using the `@lvclass` decorator, use type hints to specify field types:

| Python Type Hint | LabVIEW Type | Size |
|-----------------|--------------|------|
| `str` | LVString | variable |
| `int` | LVI32 | 4 bytes |
| `float` | LVDouble | 8 bytes |
| `bool` | LVBoolean | 1 byte |
| `LVI32` | I32 | 4 bytes |
| `LVU16` | U16 | 2 bytes |
| `LVDouble` | Double | 8 bytes |
| `LVArray(LVI32)` | Array of I32 | variable |

## Testing

Run the test suite:

```bash
# All tests
pytest tests/ -v

# Specific test files
pytest tests/test_decorators.py -v
pytest tests/test_objects.py -v
```

## Example: Complete Roundtrip

```python
from src import lvclass, lvflatten, lvunflatten, LVU16, LVI32

# Define a 3-level class hierarchy
@lvclass(library="Level1", class_name="Base")
class Base:
    pass

@lvclass(library="Level2", class_name="Middle", version=(1, 0, 0, 7))
class Middle(Base):
    pass

@lvclass(library="Level3", class_name="Derived")
class Derived(Middle):
    message: str
    code: LVU16
    count: LVI32

# Create and populate
obj = Derived()
obj.message = "Hello World"
obj.code = 42
obj.count = 100

# Serialize
data = lvflatten(obj)

# Deserialize - automatic class detection!
restored = lvunflatten(data)

# Verify
assert isinstance(restored, Derived)
assert restored.message == "Hello World"
assert restored.code == 42
assert restored.count == 100
print("✓ Roundtrip successful!")
```

## API Reference

### Main Functions

#### `lvflatten(data, type_hint=None) -> bytes`

Serialize Python data to LabVIEW binary format.

```python
# @lvclass instance
data = lvflatten(my_object)

# Basic types with auto-detection
data = lvflatten(42)        # I32
data = lvflatten("Hello")   # String
data = lvflatten(3.14)      # Double

# With explicit type hint
data = lvflatten(42, LVI64)  # Force I64
```

#### `lvunflatten(data, type_hint=None) -> Any`

Deserialize LabVIEW binary data to Python.

```python
# LVObject with automatic class detection (no type_hint)
obj = lvunflatten(data)  # Returns @lvclass instance

# Basic types (requires type_hint)
value = lvunflatten(data, LVI32)
text = lvunflatten(data, LVString)
```

### Helper Functions

#### `get_lvclass_by_name(full_name) -> Optional[Type]`

Lookup a class in the registry by its LabVIEW name.

```python
from src import get_lvclass_by_name

cls = get_lvclass_by_name("MyLib.lvlib:MyClass.lvclass")
```

## License

See LICENSE file for details.
