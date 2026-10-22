# Construct-based LabVIEW Serialization Implementation

This module provides an alternative implementation of AF-Serializer using the [Construct](https://construct.readthedocs.io/) library for declarative binary format definitions.

## Architecture

### Design Philosophy

This implementation prioritizes:

1. **Readability** - Declarative format definitions that are self-documenting
2. **Type Safety** - Full type hints coverage using Python's typing system
3. **Maintainability** - Clean separation of concerns with minimal boilerplate
4. **Correctness** - Validated against real LabVIEW HEX examples

### Module Structure

```
af_serializer/
├── __init__.py          # Public API exports
├── basic_types.py       # Basic type definitions (Phase 1) ✅
├── compound_types.py    # Arrays and Clusters (Phase 2) ✅
├── objects.py           # LVObject types (Phase 3) ✅
├── api.py               # Public API: lvflatten(), lvunflatten()
└── README.md            # This file
```

### Type System

The implementation uses Construct's declarative format definitions combined with Python type hints:

```python
from construct import Int32sb, Float64b, Struct, Bytes, this
from typing import TypeAlias, Annotated

# Type alias for documentation
LVI32Type: TypeAlias = Annotated[int, "LabVIEW I32 (signed 32-bit integer)"]

# Construct definition
LVI32 = Int32sb  # Big-endian signed 32-bit integer
```

This approach provides:
- **Declarative definitions** - Easy to understand and modify
- **Automatic validation** - Construct validates data during parse/build
- **Type safety** - Type hints help catch errors at development time
- **Self-documentation** - Type aliases include descriptions

## Usage

### Basic Example

```python
from af_serializer import lvflatten, lvunflatten, LVI32, LVString

# Serialize (auto-detect type)
data = lvflatten(42)
print(data.hex())  # Output: 0000002a

# Serialize with explicit type
data = lvflatten(42, LVI32)
print(data.hex())  # Output: 0000002a

# Deserialize (requires type hint)
value = lvunflatten(data, LVI32)
print(value)  # Output: 42
```

### All Basic Types

```python
from af_serializer import (
    lvflatten, lvunflatten,
    LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64,
    LVDouble, LVSingle, LVBoolean, LVString
)

# Integer types
lvflatten(42, LVI32)        # Signed 32-bit: 0000002a
lvflatten(42, LVU32)        # Unsigned 32-bit: 0000002a
lvflatten(1000, LVI16)      # Signed 16-bit: 03e8
lvflatten(127, LVI8)        # Signed 8-bit: 7f
lvflatten(2**63-1, LVI64)   # Signed 64-bit: 7fffffffffffffff

# Floating point
lvflatten(3.14, LVDouble)   # 64-bit IEEE 754: 40091eb851eb851f
lvflatten(3.14, LVSingle)   # 32-bit IEEE 754: 4048f5c3

# Boolean (validated: only 0x00 or 0x01)
lvflatten(True, LVBoolean)   # 01
lvflatten(False, LVBoolean)  # 00

# String (Pascal String with Int32ub length)
lvflatten("Hello", LVString)  # 0000000548656c6c6f
```

### Auto-detection

The `lvflatten()` function can auto-detect basic Python types:

```python
lvflatten(42)           # Auto-detects as I32
lvflatten(3.14)         # Auto-detects as Double
lvflatten("Hello")      # Auto-detects as String
lvflatten(True)         # Auto-detects as Boolean
```

### Convenience Functions

For common operations, use the convenience functions:

```python
from af_serializer import (
    flatten_i32, unflatten_i32,
    flatten_double, unflatten_double,
    flatten_string, unflatten_string,
    flatten_boolean, unflatten_boolean,
)

# I32
data = flatten_i32(42)
value = unflatten_i32(data)

# Double
data = flatten_double(3.14)
value = unflatten_double(data)

# String
data = flatten_string("Hello")
value = unflatten_string(data)

# Boolean
data = flatten_boolean(True)
value = unflatten_boolean(data)
```

### Phase 2: Arrays and Clusters

#### Array 1D

Create 1D arrays with homogeneous elements:

```python
from af_serializer import LVArray1D, LVI32

# Create array construct
array_construct = LVArray1D(LVI32)

# Serialize
data = array_construct.build([1, 2, 3])
print(data.hex())  # 00000003000000010000000200000003

# Deserialize
values = array_construct.parse(data)  # [1, 2, 3]

# Arrays of strings
string_array = LVArray1D(LVString)
data = string_array.build(["Hello", "World"])
```

#### Array 2D

Create multi-dimensional arrays:

```python
from af_serializer import LVArray2D, LVI32

# Create 2D array construct
array_construct = LVArray2D(LVI32)

# Serialize 2×3 matrix
data = array_construct.build([[1, 2, 3], [4, 5, 6]])
print(data.hex())  # 000000020000000200000003[elements...]

# Deserialize
matrix = array_construct.parse(data)  # [[1, 2, 3], [4, 5, 6]]
```

#### Cluster

Create heterogeneous collections (NO header, direct concatenation):

```python
from af_serializer import LVCluster, LVString, LVI32, LVU16

# String + I32 cluster
cluster = LVCluster(LVString, LVI32)
data = cluster.build(("Hello, LabVIEW!", 0))
print(data.hex())  # 0000000f48656c6c6f2c204c61625649455721 00000000

# Deserialize
values = cluster.parse(data)  # ("Hello, LabVIEW!", 0)

# Multiple types
cluster = LVCluster(LVI32, LVString, LVI32)
data = cluster.build((42, "Test", 100))
```

### Phase 3: LabVIEW Objects

#### Empty Object

```python
from af_serializer import LVObject, create_empty_lvobject

obj_construct = LVObject()
obj = create_empty_lvobject()

data = obj_construct.build(obj)
print(data.hex())  # 00000000
```

#### Single-Level Object

```python
from af_serializer import LVObject, create_lvobject

obj_construct = LVObject()
obj = create_lvobject(
    class_names=["Actor Framework.lvlib:Actor.lvclass"],
    versions=[0x01000000],
    cluster_data=[b'\x00\x00\x00\x00\x00\x00\x00\x00']
)

data = obj_construct.build(obj)
deserialized = obj_construct.parse(data)
```

#### Three-Level Inheritance

Example: Message → Serializable Msg → echo general Msg

```python
from af_serializer import LVObject, LVCluster, LVString, LVU16, create_lvobject

# Create cluster for level 3 data: "Hello World" + U16(0)
cluster_construct = LVCluster(LVString, LVU16)
cluster_data = ("Hello World", 0)
cluster_bytes = cluster_construct.build(cluster_data)

obj_construct = LVObject()
obj = create_lvobject(
    class_names=[
        "Actor Framework.lvlib:Message.lvclass",
        "Serializable Message.lvlib:Serializable Msg.lvclass",
        "Commander.lvlib:echo general Msg.lvclass"
    ],
    versions=[
        0x01000000,  # Level 1: 1.0.0.0
        0x01000007,  # Level 2: 1.0.0.7
        0x01000000   # Level 3: 1.0.0.0
    ],
    cluster_data=[
        b'\x00\x00\x00\x00\x00\x00\x00\x00',  # Empty for level 1
        b'\x00\x00\x00\x00\x00\x00\x00\x00',  # Empty for level 2
        cluster_bytes  # "Hello World" + U16(0) for level 3
    ]
)

data = obj_construct.build(obj)
deserialized = obj_construct.parse(data)
print(f"NumLevels: {deserialized['num_levels']}")  # 3
print(f"Classes: {deserialized['class_names']}")
```

## Binary Formats

All formats use **big-endian byte order** (network byte order) as required by LabVIEW.

### Integer Types

| Type | Size | Format | Example (42) |
|------|------|--------|--------------|
| LVI32 | 4 bytes | Signed 32-bit BE | `0000002a` |
| LVU32 | 4 bytes | Unsigned 32-bit BE | `0000002a` |
| LVI16 | 2 bytes | Signed 16-bit BE | `002a` |
| LVU16 | 2 bytes | Unsigned 16-bit BE | `002a` |
| LVI8 | 1 byte | Signed 8-bit | `2a` |
| LVU8 | 1 byte | Unsigned 8-bit | `2a` |
| LVI64 | 8 bytes | Signed 64-bit BE | `000000000000002a` |
| LVU64 | 8 bytes | Unsigned 64-bit BE | `000000000000002a` |

### Floating Point Types

| Type | Size | Format | Example (3.14) |
|------|------|--------|----------------|
| LVDouble | 8 bytes | IEEE 754 double BE | `40091eb851eb851f` |
| LVSingle | 4 bytes | IEEE 754 float BE | `4048f5c3` |

### Boolean Type

**Format**: 1 byte, validated to be either `0x00` (False) or `0x01` (True)

| Value | Hex |
|-------|-----|
| False | `00` |
| True | `01` |

**Note**: Deserialization will raise `ValidationError` if the byte is not `0x00` or `0x01`.

### String Type

**Format**: Pascal String with `Int32ub` length prefix + UTF-8 encoded data

```
[length (4 bytes, big-endian)] + [UTF-8 bytes]
```

**Example**: "Hello" → `00000005 48656c6c6f`

- Length: `0x00000005` (5 bytes)
- Data: `48656c6c6f` ("Hello" in UTF-8)

**Empty string**: `00000000` (length = 0, no data)

## Comparison with Original Implementation

### Original (OOP-based)

```python
# Original implementation
from af_serializer import LVNumeric, LVString, LVSerializer
import numpy as np

serializer = LVSerializer()
num = LVNumeric(42, np.int32)
text = LVString("Hello")

data = serializer.serialize(num)
```

**Pros**:
- Object-oriented design
- Rich type system with LVType base class
- Support for complex nested structures

**Cons**:
- More boilerplate (need to import numpy, create instances)
- Manual struct.pack() calls
- Less declarative

### Construct Implementation

```python
# Construct implementation
from af_serializer import lvflatten, LVI32

data = lvflatten(42, LVI32)
```

**Pros**:
- Declarative format definitions
- Less boilerplate
- Built-in validation
- Type hints throughout
- Auto-detection for basic types
- More readable

**Cons**:
- Learning curve for Construct library
- Less familiar for OOP developers
- Currently Phase 1 only (basic types)

## Testing

The implementation includes comprehensive unit tests:

```bash
# Run all construct_impl tests
pytest tests/construct_impl/ -v

# Run specific test file
pytest tests/construct_impl/test_basic_types.py -v

# Run with coverage
pytest tests/construct_impl/ --cov=af_serializer --cov-report=term-missing
```

### Test Coverage

- ✅ All basic integer types (I8, I16, I32, I64, U8, U16, U32, U64)
- ✅ Floating point types (Single, Double)
- ✅ Boolean with validation
- ✅ String with UTF-8 support
- ✅ Round-trip tests (serialize → deserialize)
- ✅ Edge cases (zero, max/min values, empty strings)
- ✅ Error handling (invalid values, type mismatches)
- ✅ Auto-detection
- ✅ Real HEX validation against LabVIEW examples

## Roadmap

### Phase 1: Basic Types ✅ COMPLETED

- [x] Integer types (I8-I64, U8-U64)
- [x] Floating point (Single, Double)
- [x] Boolean with validation
- [x] String (Pascal String)
- [x] API functions (lvflatten, lvunflatten)
- [x] Comprehensive unit tests (64 tests)
- [x] Documentation

### Phase 2: Compound Types ✅ COMPLETED

- [x] **LVArray1D**: 1D arrays with homogeneous elements
  ```python
  array_construct = LVArray1D(LVI32)
  data = array_construct.build([1, 2, 3])
  # Result: 0000 0003 0000 0001 0000 0002 0000 0003
  ```
  Format: `[num_elements (I32)] + [elements...]`

- [x] **LVArray2D**: Multi-dimensional arrays
  ```python
  array_construct = LVArray2D(LVI32)
  data = array_construct.build([[1, 2, 3], [4, 5, 6]])
  # Result: 0000 0002 0000 0002 0000 0003 [6 elements]
  ```
  Format: `[num_dims (I32)] [dim1_size] [dim2_size] + [elements...]`

- [x] **LVCluster**: Heterogeneous collections (NO header!)
  ```python
  cluster = LVCluster(LVString, LVI32)
  data = cluster.build(("Hello, LabVIEW!", 0))
  # Result: 0000 000f 48656c6c6f2c204c61625649455721 00000000
  ```
  Format: Direct concatenation without header

- [x] Comprehensive unit tests (24 tests)
- [x] Examples and documentation

### Phase 3: LVObject Types ✅ COMPLETED

- [x] **LVObject**: LabVIEW object serialization with inheritance
  ```python
  obj_construct = LVObject()
  obj = create_lvobject(
      class_names=["Actor Framework.lvlib:Actor.lvclass"],
      versions=[0x01000000],
      cluster_data=[b'']
  )
  data = obj_construct.build(obj)
  ```
  
- [x] Empty LVObject support (`0000 0000`)
- [x] Single-level objects (Actor example)
- [x] Multi-level inheritance (3+ levels)
- [x] ClassName encoding with Pascal strings
- [x] VersionList tracking
- [x] ClusterData for private state
- [x] Helper functions (create_empty_lvobject, create_lvobject)
- [x] Comprehensive unit tests (18 tests)
- [x] Real-world examples (echo general Msg with 3-level inheritance)

## Implementation Notes

### Big-Endian Byte Order

All types use big-endian byte order (network byte order) as required by LabVIEW:

```python
LVI32 = Int32sb  # 'b' suffix = big-endian
LVDouble = Float64b  # 'b' suffix = big-endian
```

### Validation

The implementation includes automatic validation:

```python
# Boolean validation
lvflatten(True, LVBoolean)   # OK: 0x01
lvunflatten(b'\x02', LVBoolean)  # ERROR: ValidationError
```

### UTF-8 Strings

String encoding uses UTF-8, supporting international characters:

```python
lvflatten("日本語")  # Japanese characters
lvflatten("Hello 👋 World 🌍")  # Emoji
```

### Type Hints

All functions include full type hints:

```python
def lvflatten(data: Any, type_hint: Optional[Construct] = None) -> bytes:
    """Serialize Python data to LabVIEW format."""
    ...

def lvunflatten(data: bytes, type_hint: Construct) -> Any:
    """Deserialize LabVIEW data to Python."""
    ...
```

## Contributing

When adding new types:

1. **Define type alias** in `basic_types.py`:
   ```python
   LVMyType: TypeAlias = Annotated[type, "Description"]
   ```

2. **Define Construct format**:
   ```python
   LVMyType = Int32sb  # Or custom Adapter
   ```

3. **Add to API** if needed in `api.py`

4. **Write tests** in `tests/construct_impl/test_*.py`:
   - Serialization with real HEX examples
   - Deserialization
   - Round-trip tests
   - Edge cases
   - Error handling

5. **Update documentation** in this README

## References

- [Construct Documentation](https://construct.readthedocs.io/)
- `docs/LBTypeDescriptor.txt` - Type Descriptor IDs
- `docs/LVObjects.txt` - Object serialization format
- `docs/HTML/LabVIEW-Manager-Data-Types-NI.html` - LabVIEW data types
- `docs/HTML/Type-Descriptors-NI.html` - Type descriptor structure

## License

See main project LICENSE file.
