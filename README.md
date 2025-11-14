# AF-Serializer

LabVIEW data serialization library for Python. Serialize Python data structures to LabVIEW-compatible binary format.

## Features

- **Auto-detection of Python types** - Automatically infers LabVIEW types from Python data
- **Simple API** - Use `lvflatten()` to serialize any Python object
- **Support for complex structures** - Handles nested lists, tuples, dictionaries, and custom objects
- **LabVIEW compatibility** - Produces binary format compatible with LabVIEW flatten/unflatten

## Installation

```bash
pip install numpy  # Required dependency
```

## Quick Start

### Auto-Flatten (Recommended)

Use `lvflatten()` to automatically serialize Python data without manual type specification:

```python
from src.Serializer import lvflatten

# Simple types
lvflatten(42)                    # Integer
lvflatten(3.14)                  # Float
lvflatten("Hello World")         # String
lvflatten(True)                  # Boolean

# Lists (homogeneous → Array)
lvflatten([1, 2, 3, 4, 5])

# Tuples (→ Cluster)
lvflatten(("Hello", 1, 0.15))

# Dictionaries (→ Named Cluster)
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
from src.Serializer import LVSerializer, LVNumeric, LVString, LVCluster
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

## Type Inference Rules

The auto-detection system (`_auto_infer_type()`) uses these rules:

| Python Type | LabVIEW Type | Notes |
|-------------|--------------|-------|
| `bool` | `LVBoolean` | Detected before `int` (bool is subclass of int) |
| `int` | `LVNumeric(np.int32)` | 32-bit signed integer |
| `float` | `LVNumeric(np.float64)` | 64-bit double |
| `str` | `LVString` | UTF-8 encoded |
| `list` (homogeneous) | `LVArray` | All elements same type → Array |
| `list` (heterogeneous) | `LVCluster` | Mixed types → Cluster without names |
| `tuple` | `LVCluster` | Always becomes Cluster without names |
| `dict` | `LVCluster` | Keys become field names (named Cluster) |
| `LVType` | Unchanged | Already a LabVIEW type |

## Supported LabVIEW Types

- **Numeric**: int8, int16, int32, int64, uint8, uint16, uint32, uint64, float32, float64
- **Boolean**: 8-bit boolean
- **String**: Length-prefixed UTF-8 strings
- **Array**: 1D arrays of homogeneous types
- **Cluster**: Ordered collections of heterogeneous types
- **Variant**: Type descriptor + data
- **Objects**: LabVIEW objects with inheritance support

## Examples

### Example 1: Original User Request

```python
from src.Serializer import lvflatten

# Complex nested tuple
data = ("Hello World", 1, 0.15, ["a", "b", "c"], [1, 2, 3])
result = lvflatten(data)
print(f"Result: {result.hex()}")
```

### Example 2: Nested Structure

```python
# Dictionary with nested structures
data = {
    "header": ("v1.0", 123),
    "values": [10, 20, 30],
    "active": True
}
result = lvflatten(data)
```

### Example 3: Custom LabVIEW Object

```python
from src.Serializer import LVObject, LVCluster, LVNumeric, LVBoolean, LVString
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
```

## Testing

Run the test suite:

```bash
pytest tests/test_auto_flatten.py -v
```

All 17 tests validate:
- Primitive type inference
- List/tuple/dict inference  
- Nested structures
- Edge cases (empty collections, unsupported types)

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

## Architecture

The library is organized in layers:

1. **Type Descriptors** - Base LabVIEW type system
2. **Serialization Context** - Configuration for endianness, alignment
3. **Basic Types** - Numeric, Boolean, String
4. **Compound Types** - Array, Cluster
5. **Objects** - LabVIEW objects with inheritance
6. **Variant Support** - Dynamic typing
7. **Auto-Inference** - Automatic type detection
8. **High-Level API** - LVSerializer class

## Contributing

Contributions welcome! Please ensure:
- All tests pass: `pytest tests/`
- Code follows existing style
- New features include tests

## License

See LICENSE file for details.

## Documentation

Additional documentation available in the `docs/` directory:
- `LBTypeDescriptor.txt` - Type descriptor reference
- `LVObjects.txt` - Object serialization format
- PDFs with detailed LabVIEW format specifications
