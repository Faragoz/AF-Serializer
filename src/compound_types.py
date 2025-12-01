"""
LabVIEW Compound Data Types using Construct Library.

This module implements LabVIEW compound data types (Arrays and Clusters)
using the Construct library.

All types use big-endian byte order (network byte order) as required by LabVIEW.

Supported Types:
    - LVArray: Universal array type that auto-detects dimensions (1D, 2D, 3D, etc.)
    - Cluster: Heterogeneous collections (no header, direct concatenation)
"""
import math
from typing import TypeAlias, Annotated, List, Any, Sequence
from construct import (
    Int32ub,
    Construct,
    Adapter,
    GreedyBytes, SizeofError,
)

# ============================================================================
# Type Aliases for Type Hints
# ============================================================================

LVArrayType: TypeAlias = Annotated[List[Any] | List[List[Any]], "LabVIEW Array "]
LVClusterType: TypeAlias = Annotated[tuple, "LabVIEW Cluster"]


# ============================================================================
# Array Implementation
# ============================================================================


class ArrayAdapter(Construct):
    """
    Construct for LabVIEW N-Dimensional Array type with automatic dimension inference.
    
    This construct handles arrays directly from streams, consuming only the bytes
    needed for the array data. It automatically infers the number of dimensions
    by analyzing the dimension values and element size.
    
    LabVIEW Array Format:
        [dim0 (I32)] [dim1 (I32)] ... [dimN-1 (I32)] [elements...]
        
    For 1D arrays:
        Format: [num_elements (I32)] [elements...]
        Example: [1, 2, 3] -> 0000 0003 0000 0001 0000 0002 0000 0003
    
    For ND arrays (2D, 3D, etc.):
        Format: [dim0 (I32)] [dim1 (I32)] ... [elements...]
        Example 2D (2×3): 0000 0002 0000 0003 [6 elements]
        Example 3D (2×4×4): 0000 0002 0000 0004 0000 0004 [32 elements]
    
    Elements are stored in row-major order (C-style).
    
    Dimension inference (for fixed-size elements):
    - Reads I32 values as potential dimensions
    - Verifies by checking if prod(dims) * element_size bytes can be read
    - Uses stream seeking to verify and correct
    
    For variable-size elements, defaults to 1D parsing.
    """
    
    def __init__(self, element_type: Construct):
        """
        Initialize ArrayND construct.
        
        Args:
            element_type: Construct type for array elements
        """
        super().__init__()
        self.element_type = element_type
    
    def _parse(self, stream, context, path) -> List:
        """Parse array from stream with automatic dimension inference."""
        # Get element size for dimension inference
        element_size = None
        try:
            element_size = self.element_type.sizeof()
        except (TypeError, AttributeError, SizeofError):
            pass
        
        if element_size is None:
            # Variable-size elements: fall back to 1D parsing
            count = Int32ub.parse_stream(stream)
            if count == 0:
                return []
            elements = []
            for _ in range(count):
                element = self.element_type.parse_stream(stream)
                elements.append(element)
            return elements
        
        # Fixed-size elements: infer dimensions
        # Strategy: Try dimension counts and see if any gives exact match
        # If no exact match, default to 1D
        
        # Save start position
        start_pos = stream.tell()
        
        # Get stream size to calculate remaining bytes
        stream.seek(0, 2)  # Seek to end
        end_pos = stream.tell()
        stream.seek(start_pos)  # Seek back
        remaining_bytes = end_pos - start_pos
        
        if remaining_bytes == 0:
            return []
        
        if remaining_bytes < 4:
            return []
        
        # Read first dimension
        first_dim = Int32ub.parse_stream(stream)
        if first_dim == 0:
            return []
        
        # Try to find dimension count that gives exact match
        dims = [first_dim]
        found_exact_match = False
        max_dims = 10  # Safety limit
        
        while len(dims) < max_dims:
            # Calculate what this dimension interpretation would mean
            prod = math.prod(dims)
            dims_bytes = len(dims) * 4
            expected_element_bytes = prod * element_size
            expected_total = dims_bytes + expected_element_bytes
            
            if expected_total == remaining_bytes:
                # Exact match! This is the correct interpretation
                found_exact_match = True
                break
            elif expected_total > remaining_bytes:
                # Too many bytes expected, can't be right
                # Remove the last dimension and stop
                if len(dims) > 1:
                    dims.pop()
                break
            
            # Try reading next dimension
            if stream.tell() - start_pos + 4 > remaining_bytes:
                # Not enough bytes for another dimension
                break
                
            next_dim = Int32ub.parse_stream(stream)
            if next_dim == 0:
                # Zero dimension means something went wrong
                # Default to what we have
                break
            dims.append(next_dim)
        
        # If no exact match found, default to 1D (most common case for clusters)
        if not found_exact_match:
            dims = [first_dim]
            # Seek back to position after first dimension
            stream.seek(start_pos + 4)
        
        # Parse elements
        total_elements = math.prod(dims)
        elements = []
        for _ in range(total_elements):
            element = self.element_type.parse_stream(stream)
            elements.append(element)
        
        # Reshape to nested list based on dimensions
        if len(dims) == 1:
            return elements
        else:
            return self._reshape_to_nested_list(elements, dims)
    
    def _build(self, obj: List, stream, context, path):
        """Build array to stream."""
        if not obj:
            # Empty array - write single 0 dimension
            stream.write(Int32ub.build(0))
            return
        
        # Determine dimensions from the nested list
        dims = self._get_dimensions(obj)
        
        # Write all dimension sizes
        for dim_size in dims:
            stream.write(Int32ub.build(dim_size))
        
        # Flatten and write elements in row-major order
        flat_elements = self._flatten_nested_list(obj)
        for element in flat_elements:
            stream.write(self.element_type.build(element))
    
    def _sizeof(self, context, path):
        """Size cannot be determined statically."""
        raise SizeofError("ArrayAdapter size is variable")
    
    def _get_dimensions(self, obj: List) -> List[int]:
        """Get dimensions of a list or nested list."""
        dims = []
        current = obj
        while isinstance(current, list):
            dims.append(len(current))
            if len(current) > 0:
                current = current[0]
            else:
                break
        return dims
    
    def _flatten_nested_list(self, obj: List) -> List:
        """Flatten a nested list to 1D in row-major order."""
        flat = []
        if not isinstance(obj, list):
            return [obj]
        for item in obj:
            if isinstance(item, list):
                flat.extend(self._flatten_nested_list(item))
            else:
                flat.append(item)
        return flat
    
    def _reshape_to_nested_list(self, flat: List, dims: List[int]) -> List:
        """Reshape a flat list to nested list based on dimensions."""
        if len(dims) == 0:
            return flat
        if len(dims) == 1:
            return flat[:dims[0]]
        
        # Calculate size of sub-arrays
        sub_size = 1
        for d in dims[1:]:
            sub_size *= d
        
        result = []
        for i in range(dims[0]):
            start = i * sub_size
            end = start + sub_size
            sub_list = self._reshape_to_nested_list(flat[start:end], dims[1:])
            result.append(sub_list)
        
        return result
    
    def _create_empty_nested_list(self, dims: List[int]) -> List:
        """Create an empty nested list structure based on dimensions."""
        if len(dims) == 0:
            return []
        if len(dims) == 1:
            return [None] * dims[0] if dims[0] > 0 else []
        
        result = []
        for _ in range(dims[0]):
            result.append(self._create_empty_nested_list(dims[1:]))
        return result


def LVArray(element_type):
    """
    Create a LabVIEW Array construct with automatic dimension detection.
    
    This creates an array construct that handles serialization and deserialization
    of LabVIEW arrays. It automatically infers the number of dimensions when
    parsing, making it self-delimiting for use in clusters with multiple arrays.
    
    LabVIEW Array Format:
        [dim0 (I32)] [dim1 (I32)] ... [dimN-1 (I32)] [elements...]
    
    Args:
        element_type: Construct type for array elements
    
    Returns:
        Construct that can serialize/deserialize arrays of any dimension
    
    Examples:
        1D Array:
        >>> from src import LVArray, LVI32
        >>> arr = LVArray(LVI32)
        >>> data = arr.build([1, 2, 3])
        >>> print(data.hex())
        00000003000000010000000200000003
        >>> arr.parse(data)
        [1, 2, 3]
        
        2D Array (2×3):
        >>> arr = LVArray(LVI32)
        >>> data = arr.build([[1, 2, 3], [4, 5, 6]])
        >>> print(data.hex())
        0000000200000003000000010000000200000003000000040000000500000006
        >>> arr.parse(data)
        [[1, 2, 3], [4, 5, 6]]
        
        Multiple Arrays in Cluster:
        >>> cluster = LVCluster(LVArray(LVI32), LVArray(LVI32))
        >>> data = cluster.build(([1, 2, 3], [4, 5, 6]))
        >>> cluster.parse(data)
        ([1, 2, 3], [4, 5, 6])
    """
    return ArrayAdapter(element_type)


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

