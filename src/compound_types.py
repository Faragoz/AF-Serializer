"""
LabVIEW Compound Data Types using Construct Library.

This module implements LabVIEW compound data types (Arrays and Clusters)
using the Construct library.

All types use big-endian byte order (network byte order) as required by LabVIEW.

Supported Types:
    - Array1D: 1D arrays with homogeneous elements
    - Array2D: 2D/ND arrays with dimension information
    - Cluster: Heterogeneous collections (no header, direct concatenation)
"""

from typing import TypeAlias, Annotated, List, Any, Sequence
from construct import (
    Int32ub,
    Construct,
    Adapter,
    GreedyBytes,
    PrefixedArray,
)


# ============================================================================
# Type Aliases for Type Hints
# ============================================================================

LVArray1DType: TypeAlias = Annotated[List[Any], "LabVIEW 1D Array"]
LVArray2DType: TypeAlias = Annotated[List[List[Any]], "LabVIEW 2D Array"]
LVArrayType: TypeAlias = Annotated[List[Any] | List[List[Any]], "LabVIEW Array (auto-detects 1D or 2D)"]
LVClusterType: TypeAlias = Annotated[tuple, "LabVIEW Cluster"]


# ============================================================================
# Unified Array Implementation
# ============================================================================

from construct import PrefixedArray


# ============================================================================
# Array Adapter (Auto-detects 1D or 2D)
# ============================================================================

class ArrayAdapter(Adapter):
    """
    Unified adapter for LabVIEW Arrays that auto-detects dimensions.
    
    Automatically determines if data is 1D or 2D and serializes accordingly:
    - 1D: [count (I32)] + [elements...] (using PrefixedArray declaratively)
    - 2D: [num_dims (I32)] [dim1] [dim2] + [elements...]
    """
    
    def __init__(self, element_construct: Construct):
        self.element_construct = element_construct
        # Use PrefixedArray for 1D case declaratively
        self.array_1d = PrefixedArray(Int32ub, element_construct)
        super().__init__(GreedyBytes)
    
    def _decode(self, obj: bytes, context, path):
        """
        Auto-detect dimension format and decode.
        
        Detection strategy:
        - If first I32 == 2, peek at next two I32s
        - If they look like dimension sizes followed by data that could be elements,
          treat as 2D
        - Otherwise treat as 1D
        
        Note: This heuristic works for most cases but has edge cases.
        Use LVArray1D/LVArray2D directly if you need guaranteed behavior.
        """
        import io
        import struct
        stream = io.BytesIO(obj)
        
        # Handle empty array case
        if len(obj) == 4:
            # Could be empty 1D array (just count=0)
            first_int = Int32ub.parse(obj)
            if first_int == 0:
                return []
        
        # Read first I32
        first_int = Int32ub.parse_stream(stream)
        
        # Heuristic for 2D detection
        next_pos = stream.tell()
        try:
            # Read next two I32s
            second_int = Int32ub.parse_stream(stream)
            third_int = Int32ub.parse_stream(stream)
            stream.seek(next_pos)  # Reset position
            
            # If first_int == 2 (num_dims), second and third should be dimension sizes
            # They should be positive and reasonable (not too large, not data values)
            if (first_int == 2 and 
                0 < second_int < 1000 and 
                0 < third_int < 1000):
                # Check if total bytes makes sense for 2D
                expected_size = 12 + (second_int * third_int * self._estimate_element_size())
                if abs(len(obj) - expected_size) < 100:  # Some tolerance
                    return self._decode_2d(obj)
            
            # Otherwise treat as 1D
            return self._decode_1d(obj)
        except (EOFError, struct.error):
            # If we can't read enough data, treat as 1D
            return self._decode_1d(obj)
    
    def _estimate_element_size(self) -> int:
        """Estimate element size for heuristic. Returns 4 as default."""
        try:
            return self.element_construct.sizeof()
        except:
            return 4  # Default for I32
    
    def _decode_1d(self, obj: bytes):
        """Decode as 1D array using declarative PrefixedArray."""
        return self.array_1d.parse(obj)
    
    def _decode_2d(self, obj: bytes):
        """Decode as 2D array."""
        import io
        stream = io.BytesIO(obj)
        
        num_dims = Int32ub.parse_stream(stream)
        dimensions = []
        for _ in range(num_dims):
            dimensions.append(Int32ub.parse_stream(stream))
        
        total_elements = 1
        for dim in dimensions:
            total_elements *= dim
        
        elements = []
        for _ in range(total_elements):
            # Use parse_stream to handle variable-length types
            elements.append(self.element_construct.parse_stream(stream))
        
        if num_dims == 2:
            result = []
            idx = 0
            for _ in range(dimensions[0]):
                row = []
                for _ in range(dimensions[1]):
                    row.append(elements[idx])
                    idx += 1
                result.append(row)
            return result
        else:
            return elements
    
    def _encode(self, obj, context, path) -> bytes:
        """Auto-detect dimensions and encode."""
        import io
        stream = io.BytesIO()
        
        # Handle empty array
        if not obj:
            # Empty 1D array: just count of 0
            stream.write(Int32ub.build(0))
            return stream.getvalue()
        
        # Check if 1D or 2D
        if isinstance(obj[0], list):
            # 2D array
            num_dims = 2
            dim1 = len(obj)
            dim2 = len(obj[0]) if obj else 0
            
            stream.write(Int32ub.build(num_dims))
            stream.write(Int32ub.build(dim1))
            stream.write(Int32ub.build(dim2))
            
            for row in obj:
                for element in row:
                    stream.write(self.element_construct.build(element))
            return stream.getvalue()
        else:
            # 1D array - use declarative PrefixedArray
            return self.array_1d.build(obj)


def LVArray(element_construct: Construct) -> Construct:
    """
    Create a unified LabVIEW Array construct that auto-detects dimensions.
    
    Automatically handles both 1D and 2D arrays:
    - For 1D lists: [count] + [elements...] (uses PrefixedArray declaratively)
    - For 2D lists (list of lists): [num_dims] [dim1] [dim2] + [elements...]
    
    Args:
        element_construct: Construct definition for array elements
    
    Returns:
        Construct that can serialize/deserialize arrays
    
    Example:
        >>> from src import LVI32, LVArray
        >>> array_construct = LVArray(LVI32)
        >>> # 1D array
        >>> data = array_construct.build([1, 2, 3])
        >>> # 2D array
        >>> data = array_construct.build([[1, 2], [3, 4]])
    """
    return ArrayAdapter(element_construct)


# Simplified implementations using declarative Construct primitives
def LVArray1D(element_construct: Construct) -> Construct:
    """
    Create a LabVIEW 1D Array construct.
    
    Uses Construct's built-in PrefixedArray for clean, declarative definition.
    
    LabVIEW 1D arrays are encoded as:
    - Int32ub (4 bytes, big-endian) number of elements
    - Elements data (serialized using element type)
    
    Format: [num_elements (I32)] + [elements...]
    Example (3 elements: 1, 2, 3):
        0000 0003 0000 0001 0000 0002 0000 0003
    
    Args:
        element_construct: Construct definition for array elements (e.g., LVI32)
    
    Returns:
        Construct that can serialize/deserialize 1D arrays
    
    Example:
        >>> from src import LVI32, LVArray1D
        >>> array_construct = LVArray1D(LVI32)
        >>> data = array_construct.build([1, 2, 3])
        >>> print(data.hex())
        0000000300000001000000020000000003
    """
    # Use Construct's PrefixedArray declaratively - this is the unified, simpler approach
    return PrefixedArray(Int32ub, element_construct)


def LVArray2D(element_construct: Construct) -> Construct:
    """
    Create a LabVIEW 2D/Multi-dimensional Array construct.
    
    For 2D arrays, use the unified LVArray which auto-detects dimensions.
    
    Args:
        element_construct: Construct definition for array elements
    
    Returns:
        Construct that can serialize/deserialize 2D arrays
    
    Example:
        >>> from src import LVI32, LVArray2D
        >>> array_construct = LVArray2D(LVI32)
        >>> data = array_construct.build([[1, 2, 3], [4, 5, 6]])
        >>> print(data.hex())
        00000002000000020000000300000001...
    """
    # For 2D, use the unified auto-detecting adapter
    return LVArray(element_construct)


# ============================================================================
# Cluster Implementation
# ============================================================================

class ClusterAdapter(Adapter):
    """
    Adapter for LabVIEW Cluster type.
    
    LabVIEW clusters are heterogeneous collections that concatenate data
    WITHOUT a count header. Data is concatenated directly.
    
    Format: Direct concatenation (NO header!)
    Example (String "Hello, LabVIEW!" + I32(0)):
        0000 000f 48656c6c6f2c204c61625649455721 00000000
        ^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^^^^
        length   "Hello, LabVIEW!"                 I32(0)
    """
    
    def __init__(self, field_constructs: Sequence[Construct]):
        """
        Initialize Cluster adapter with field types.
        
        Args:
            field_constructs: Sequence of Construct definitions for each field
        """
        self.field_constructs = list(field_constructs)
        # Use GreedyBytes as we'll handle serialization manually
        super().__init__(GreedyBytes)
    
    def _decode(self, obj: bytes, context, path) -> tuple:
        """Convert bytes to Python tuple."""
        import io
        stream = io.BytesIO(obj)
        
        values = []
        for field_construct in self.field_constructs:
            # For variable-length types (like strings), parse directly from stream
            # For fixed-length types, we can read the exact number of bytes
            try:
                # Try to parse directly from stream (works for all types)
                field_value = field_construct.parse_stream(stream)
                values.append(field_value)
            except Exception as e:
                # If parse_stream fails, try reading fixed size if available
                if hasattr(field_construct, 'sizeof'):
                    try:
                        size = field_construct.sizeof()
                        field_bytes = stream.read(size)
                        values.append(field_construct.parse(field_bytes))
                    except (AttributeError, TypeError):
                        # sizeof() failed, re-raise original error
                        raise e
                else:
                    raise e
        
        return tuple(values)
    
    def _encode(self, obj: tuple, context, path) -> bytes:
        """Convert Python tuple to bytes."""
        import io
        stream = io.BytesIO()
        
        for i, value in enumerate(obj):
            field_construct = self.field_constructs[i]
            stream.write(field_construct.build(value))
        
        return stream.getvalue()


def LVCluster(*field_constructs: Construct) -> Construct:
    """
    Create a LabVIEW Cluster construct.
    
    Clusters are heterogeneous collections with NO header.
    Data is concatenated directly in order.
    
    Uses declarative Construct parsing with parse_stream for clean implementation.
    
    Args:
        *field_constructs: Variable number of Construct definitions for fields
    
    Returns:
        Construct that can serialize/deserialize clusters
    
    Example:
        >>> from src import LVString, LVI32, LVCluster
        >>> cluster = LVCluster(LVString, LVI32)
        >>> data = cluster.build(("Hello, LabVIEW!", 0))
        >>> print(data.hex())
        0000000f48656c6c6f2c204c6162564945572100000000
    """
    return ClusterAdapter(field_constructs)
