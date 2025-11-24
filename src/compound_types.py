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
LVClusterType: TypeAlias = Annotated[tuple, "LabVIEW Cluster"]


# ============================================================================
# Array 1D Implementation
# ============================================================================

from construct import PrefixedArray

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
    return PrefixedArray(Int32ub, element_construct)


# ============================================================================
# Array 2D/ND Implementation
# ============================================================================

class Array2DAdapter(Adapter):
    """
    Adapter for LabVIEW 2D/Multi-dimensional Array type.
    
    LabVIEW 2D arrays are encoded as:
    - Int32ub (4 bytes) number of dimensions
    - Int32ub for each dimension size
    - Elements data (serialized in row-major order)
    
    Format: [num_dims (I32)] [dim1_size] [dim2_size] ... + [elements...]
    Example (2×3 matrix):
        0000 0002 0000 0002 0000 0003 [6 elements]
    """
    
    def __init__(self, element_construct: Construct):
        """
        Initialize Array2D adapter with element type.
        
        Args:
            element_construct: Construct definition for array elements
        """
        self.element_construct = element_construct
        # We'll use a custom approach since dimensions are variable
        super().__init__(GreedyBytes)
    
    def _decode(self, obj: bytes, context, path) -> list:
        """Convert bytes to nested Python lists."""
        import io
        stream = io.BytesIO(obj)
        
        # Read number of dimensions
        num_dims_bytes = stream.read(4)
        num_dims = Int32ub.parse(num_dims_bytes)
        
        # Read dimension sizes
        dimensions = []
        for _ in range(num_dims):
            dim_bytes = stream.read(4)
            dimensions.append(Int32ub.parse(dim_bytes))
        
        # Calculate total number of elements
        total_elements = 1
        for dim in dimensions:
            total_elements *= dim
        
        # Read all elements
        elements = []
        for _ in range(total_elements):
            element_bytes = stream.read(self.element_construct.sizeof())
            elements.append(self.element_construct.parse(element_bytes))
        
        # Reshape into nested list structure
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
            # For other dimensions, return flat list
            return elements
    
    def _encode(self, obj: list, context, path) -> bytes:
        """Convert nested Python lists to bytes."""
        import io
        stream = io.BytesIO()
        
        # Determine dimensions
        if isinstance(obj[0], list):
            # 2D array
            num_dims = 2
            dim1 = len(obj)
            dim2 = len(obj[0]) if obj else 0
            dimensions = [dim1, dim2]
            
            # Flatten the array
            elements = []
            for row in obj:
                elements.extend(row)
        else:
            # 1D array treated as 2D with second dimension = 1
            num_dims = 2
            dimensions = [len(obj), 1]
            elements = obj
        
        # Write number of dimensions
        stream.write(Int32ub.build(num_dims))
        
        # Write dimension sizes
        for dim in dimensions:
            stream.write(Int32ub.build(dim))
        
        # Write elements
        for element in elements:
            stream.write(self.element_construct.build(element))
        
        return stream.getvalue()


def LVArray2D(element_construct: Construct) -> Construct:
    """
    Create a LabVIEW 2D/Multi-dimensional Array construct.
    
    Args:
        element_construct: Construct definition for array elements
    
    Returns:
        Construct that can serialize/deserialize 2D arrays
    
    Example:
        >>> from src.construct_impl import LVI32
        >>> array_construct = LVArray2D(LVI32)
        >>> data = array_construct.build([[1, 2, 3], [4, 5, 6]])
        >>> print(data.hex())
        00000002000000020000000300000001...
    """
    return Array2DAdapter(element_construct)


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
    
    Args:
        *field_constructs: Variable number of Construct definitions for fields
    
    Returns:
        Construct that can serialize/deserialize clusters
    
    Example:
        >>> from src.construct_impl import LVString, LVI32
        >>> cluster = LVCluster(LVString, LVI32)
        >>> data = cluster.build(("Hello, LabVIEW!", 0))
        >>> print(data.hex())
        0000000f48656c6c6f2c204c6162564945572100000000
    """
    return ClusterAdapter(field_constructs)
