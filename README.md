# AF-Serializer

LabVIEW data serialization library for Python. Serialize Python data structures to LabVIEW-compatible binary format with 100% compatibility based on real HEX examples from LabVIEW.

## Features

- **Auto-detection of Python types** - Automatically infers LabVIEW types from Python data
- **Simple API** - Use `lvflatten()` to serialize any Python object
- **Modular architecture** - Clean separation of concerns with specialized modules
- **Support for complex structures** - Handles nested lists, tuples, dictionaries, and custom objects
- **LabVIEW compatibility** - Produces binary format 100% compatible with LabVIEW flatten/unflatten
- **Validated against real HEX examples** - All formats validated against LabVIEW documentation

## Installation

```bash
pip install numpy  # Required dependency
```

## Quick Start

### Auto-Flatten (Recommended)

Use `lvflatten()` to automatically serialize Python data without manual type specification:

```python
from src import lvflatten

# Simple types
lvflatten(42)                    # Integer → I32
lvflatten(3.14)                  # Float → Double
lvflatten("Hello World")         # String
lvflatten(True)                  # Boolean

# Arrays (homogeneous lists)
lvflatten([1, 2, 3])            # Array 1D of I32
# Output: 00000003 00000001 00000002 00000003

# Clusters (tuples or heterogeneous data)
lvflatten(("Hello", 1, 0.15))   # Cluster without names

# Named Clusters (dictionaries)
lvflatten({"x": 10, "y": 20, "label": "Point A"})

# Complex nested structures
lvflatten({
    "header": ("v1.0", 123),
    "values": [10, 20, 30],
    "active": True
})
```

### Manual Type Specification

For more control, use the lower-level API:

```python
from src import LVSerializer, LVNumeric, LVString, LVCluster
import numpy as np

serializer = LVSerializer()

# Create LabVIEW types manually
num = LVNumeric(42, np.int32)
text = LVString("Hello LabVIEW")

# Create cluster with named fields
names = ("x", "y", "label")
values = (
    LVNumeric(10.5, np.float64),
    LVNumeric(20.3, np.float64),
    LVString("Point A")
)
cluster = LVCluster((names, values))

# Serialize
data = serializer.serialize(cluster)
print(f"Serialized: {data.hex()}")
```

### Using the @lvclass Decorator

Create LabVIEW objects from Python classes:

```python
from src import lvflatten, lvclass

@lvclass(library="Commander", class_name="echo general Msg")
class EchoMsg:
    message: str = ""
    status: int = 0

msg = EchoMsg()
msg.message = "Hello, LabVIEW!"
msg.status = 1

# Serialize automatically (future feature)
# serialized = lvflatten(msg)
```

## Architecture

The library is organized in a modular structure for maintainability:

```
src/
├── __init__.py           # Main exports
├── Serializer.py         # Backward compatibility wrapper
├── descriptors.py        # TypeDescriptor, TypeDescriptorID
├── serialization.py      # SerializationContext, ISerializable
├── auto_flatten.py       # lvflatten(), auto-detection
├── lv_serializer.py      # LVSerializer high-level API
├── decorators.py         # @lvclass decorator
└── types/
    ├── __init__.py       # Type exports
    ├── basic.py          # LVNumeric, LVBoolean, LVString
    ├── compound.py       # LVArray, LVCluster
    ├── objects.py        # LVObject, LVObjectMetadata
    └── variant.py        # LVVariant
```

## Type Inference Rules

The auto-detection system (`_auto_infer_type()`) uses these rules:

| Python Type | LabVIEW Type | Format | Example Output |
|-------------|--------------|--------|----------------|
| `bool` | `LVBoolean` | 1 byte | `01` (True), `00` (False) |
| `int` | `LVNumeric(I32)` | 4 bytes BE | `00000001` (1) |
| `float` | `LVNumeric(Double)` | 8 bytes BE | `3FD51EB851EB851F` (0.33) |
| `str` | `LVString` | I32 length + UTF-8 | `0000000B 48656C6C6F20576F726C64` ("Hello World") |
| `list` (homogeneous) | `LVArray` | See Array format | `00000003 ...` (3 elements) |
| `list` (heterogeneous) | `LVCluster` | Concatenated data | No header |
| `tuple` | `LVCluster` | Concatenated data | No header |
| `dict` | `LVCluster` (named) | Concatenated data | No header |
| `LVType` | Unchanged | As defined | - |

**Note**: Boolean is checked before int since `bool` is a subclass of `int` in Python.

## LabVIEW Data Formats

### Arrays

LVArray automatically handles 1D, 2D, 3D, and higher dimensional arrays.

The format is: `[dim0 (I32)] [dim1 (I32)] ... [dimN-1 (I32)] [elements...]`

Dimensions are auto-detected by reading until `prod(dims) * element_size == remaining_bytes`.

**1D Array**: `[num_elements (I32)] + [elements...]`
```python
from src import LVArray, LVI32

arr = LVArray(LVI32)
data = arr.build([1, 2, 3])
# Output: 00000003 00000001 00000002 00000003

parsed = arr.parse(data)  # Returns [1, 2, 3]
```

**2D Array**: `[dim0_size (I32)] [dim1_size (I32)] + [elements...]`
```python
from src import LVArray, LVI32

arr = LVArray(LVI32)
data = arr.build([[1, 2, 3], [4, 5, 6]])
# Output: 00000002 00000003 00000001 00000002 00000003 00000004 00000005 00000006
# Header: dim0=2, dim1=3

parsed = arr.parse(data)  # Returns [[1, 2, 3], [4, 5, 6]]
```

**3D Array**: `[dim0_size (I32)] [dim1_size (I32)] [dim2_size (I32)] + [elements...]`
```python
from src import LVArray, LVI32

arr = LVArray(LVI32)
# 2×4×4 array
data_3d = [
    [[7, 0, 0, 0], [8, 0, 0, 0], [0, 0, 3, 0], [0, 0, 0, 5]],
    [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 6], [0, 0, 0, 0]]
]
serialized = arr.build(data_3d)
# Header: 00000002 00000004 00000004 (dims=2,4,4)

parsed = arr.parse(serialized)  # Returns the original 3D array
```

### Clusters

Clusters concatenate data **without a count header**:
```python
# String "Hello, LabVIEW!" + I32(0)
# Output: 0000000F 48656C6C6F2C204C6162564945572100 00000000
#         ^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^
#         length   "Hello, LabVIEW!"                 I32(0)
```

### Strings

Format: `[length (I32)] + [UTF-8 bytes]`
```python
lvflatten("Hello")
# Output: 00000005 48656C6C6F
```

## Supported LabVIEW Types

- **Numeric**: int8, int16, int32, int64, uint8, uint16, uint32, uint64, float32, float64
- **Boolean**: 8-bit boolean
- **String**: Length-prefixed UTF-8 strings
- **Array**: 1D, 2D, 3D, and N-dimensional arrays of homogeneous types (auto-detects dimensions)
- **Cluster**: Ordered collections of heterogeneous types
- **Variant**: Type descriptor + data
- **Objects**: LabVIEW objects with inheritance support

## Examples

### Example 1: Simple Types

```python
from src import lvflatten

# Primitives
print(lvflatten(1).hex())           # 00000001
print(lvflatten(True).hex())        # 01
print(lvflatten("Hello").hex())     # 0000000548656C6C6F
print(lvflatten(3.14).hex())        # 400921FB54442D18

# Arrays
print(lvflatten([1, 2, 3]).hex())   # 0000000300000001000000020000000003
```

### Example 2: Nested Structures

```python
from src import lvflatten

# Complex nested tuple
data = ("Hello World", 1, 0.15, ["a", "b", "c"], [1, 2, 3])
result = lvflatten(data)
print(f"Result: {result.hex()}")

# Dictionary with nested structures
data = {
    "header": ("v1.0", 123),
    "values": [10, 20, 30],
    "active": True
}
result = lvflatten(data)
print(f"Result: {result.hex()}")
```

### Example 3: Custom LabVIEW Object

```python
from src import LVObject, LVCluster, LVNumeric, LVBoolean, LVString, LVSerializer
import numpy as np

class MyLVObject(LVObject):
    __lv_version__ = (1, 2, 3, 4)
    __lv_library__ = "MyLibrary"
    
    def _initialize_private_data(self) -> LVCluster:
        names = ("timestamp", "value", "status")
        values = (
            LVNumeric(0, np.uint64),
            LVNumeric(0.0, np.float64),
            LVBoolean(False)
        )
        return LVCluster((names, values))

obj = MyLVObject()
obj.set_data(1234567890, 42.5, True)

serializer = LVSerializer()
data = serializer.serialize(obj)
print(f"Serialized object: {data.hex()}")
```

## Testing

Run the test suite:

```bash
# All tests
pytest tests/ -v

# Specific test files
pytest tests/test_auto_flatten.py -v
pytest tests/test_hex_validation.py -v
```

Current test coverage:
- **25 tests total**, all passing ✅
- **17 tests** for auto-flatten functionality
- **8 tests** validating against real LabVIEW HEX examples

Test categories:
- Primitive type inference
- List/tuple/dict inference  
- Nested structures
- Edge cases (empty collections, unsupported types)
- HEX format validation (I32, Double, Boolean, String, Arrays, Clusters)

## API Reference

### Main Functions

#### `lvflatten(data, context=None) -> bytes`

Automatically serialize any Python data to LabVIEW format.

**Parameters:**
- `data`: Any Python type (int, float, str, list, tuple, dict, nested)
- `context`: Optional `SerializationContext` for custom settings

**Returns:**
- `bytes`: LabVIEW-compatible binary data

**Raises:**
- `ValueError`: For empty lists/tuples/dicts
- `TypeError`: For unsupported types

#### `lvunflatten(data, type_hint=None, context=None) -> Any`

Deserialize LabVIEW data to Python (placeholder - not yet implemented).

### Internal Functions

#### `_auto_infer_type(data) -> LVType`

Infer LabVIEW type from Python data. Used internally by `lvflatten()`.

## Project Status

### ✅ Completed
- [x] Auto-detection of Python types
- [x] Modular architecture with clear separation of concerns
- [x] Array 1D/2D/3D/ND serialization (validated against HEX examples)
- [x] Cluster serialization (validated against HEX examples)
- [x] Basic types (I32, Double, Boolean, String)
- [x] Backward compatibility layer
- [x] Comprehensive test suite
- [x] @lvclass decorator for custom objects
- [x] LVArray auto-detection of dimensions (1D, 2D, 3D, ND)
- [x] LVArray default value `[]` in Objects.py for type hints

### 🚧 In Progress / Future Work
- [ ] Fixed Point serialization
- [ ] Complete LVObject serialization (Actor, Commander, etc.)
- [ ] Deserialization (lvunflatten)
- [ ] TypeDescriptor.from_bytes() full implementation
- [ ] Round-trip tests (serialize → deserialize → compare)

## Contributing

Contributions welcome! Please ensure:
- All tests pass: `pytest tests/ -v`
- Code follows existing style
- New features include tests
- HEX output validated against LabVIEW when possible

## References

Additional documentation available in the `docs/` directory:
- `LBTypeDescriptor.txt` - Type descriptor reference
- `LVObjects.txt` - Object serialization format
- `HTML/Type-Descriptors-NI.html` - NI documentation
- `HTML/LabVIEW-Manager-Data-Types-NI.html` - Data types reference

## License

See LICENSE file for details.
