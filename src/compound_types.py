"""
LabVIEW Compound Data Types using Construct Library.

This module implements LabVIEW compound data types (Arrays and Clusters)
using the Construct library.

All types use big-endian byte order (network byte order) as required by LabVIEW.

Supported Types:
    - LVArray: Universal array type that auto-detects dimensions (1D, 2D, 3D, etc.)
    - Cluster: Heterogeneous collections (no header, direct concatenation)
"""
from typing import TypeAlias, Annotated, List, Any, Sequence
from construct import (
    Int32ub,
    Construct,
    Adapter,
    GreedyBytes,
)

# ============================================================================
# Type Aliases for Type Hints
# ============================================================================

LVArrayType: TypeAlias = Annotated[List[Any] | List[List[Any]], "LabVIEW Array "]
LVClusterType: TypeAlias = Annotated[tuple, "LabVIEW Cluster"]


# ============================================================================
# Array Implementation
# ============================================================================


class ArrayNDAdapter(Adapter):
    """
    Adapter for LabVIEW N-Dimensional Array type with auto-dimension detection.
    
    This adapter handles all array dimensions (1D, 2D, 3D, etc.) automatically.
    
    For 1D arrays:
        Format: [num_elements (I32)] [elements...]
        Example: [1, 2, 3] -> 0000 0003 0000 0001 0000 0002 0000 0003
    
    For ND arrays (2D, 3D, etc.):
        Format: [num_dims (I32)] [dim0 (I32)] ... [dimN-1 (I32)] [elements...]
        Example 2D (2×3): 0000 0002 0000 0002 0000 0003 [6 elements]
        Example 3D (2×4×4): 0000 0003 0000 0002 0000 0004 0000 0004 [32 elements]
    
    Elements are stored in row-major order (C-style).
    
    The dimension detection works as follows:
    - When building: Analyzes the nested list structure to determine dimensions
    - When parsing: Reads num_dims from the header, then reads that many dimension sizes
    """
    
    def __init__(self, element_type: Construct):
        """
        Initialize ArrayND adapter.
        
        Args:
            element_type: Construct type for array elements
        """
        self.element_type = element_type
        super().__init__(GreedyBytes)
    
    def _decode(self, obj: bytes, context, path) -> List:
        """Convert bytes to Python list (1D) or nested list (ND)."""
        import io
        stream = io.BytesIO(obj)
        
        # Read first I32 - this is num_dims for ND arrays, or count for 1D
        first_value = Int32ub.parse_stream(stream)
        
        if first_value == 0:
            return []
        
        # For 1D arrays, first_value is the count of elements
        # For ND arrays, first_value is num_dims (2, 3, 4, etc.)
        # We need to determine which case this is
        
        # Get element size if possible
        element_size = None
        try:
            element_size = self.element_type.sizeof()
        except (TypeError, AttributeError):
            # Variable size element, can't easily verify
            pass
        
        # First, check if it's a simple 1D array
        if element_size is not None:
            remaining_after_first = len(obj) - 4  # After first I32
            if remaining_after_first == first_value * element_size:
                # Perfect match for 1D array
                elements = []
                for _ in range(first_value):
                    element = self.element_type.parse_stream(stream)
                    elements.append(element)
                return elements
        
        # Try to interpret as ND array (first_value is num_dims)
        if first_value >= 2:  # Could be num_dims for 2D or higher
            current_pos = stream.tell()
            
            # Read potential dimension sizes
            potential_dims = []
            try:
                for _ in range(first_value):
                    dim = Int32ub.parse_stream(stream)
                    potential_dims.append(dim)
                
                # Calculate expected elements from dims
                expected_elements = 1
                for d in potential_dims:
                    if d <= 0:
                        # Invalid dimension, not an ND array
                        break
                    expected_elements *= d
                else:
                    # All dims valid, check if element count matches
                    if element_size is not None:
                        bytes_for_elements = expected_elements * element_size
                        actual_remaining = len(obj) - stream.tell()
                        
                        if bytes_for_elements == actual_remaining:
                            # This is an ND array!
                            return self._parse_nd_elements(stream, potential_dims)
                    else:
                        # Variable size elements - try to parse and see if it works
                        try:
                            result = self._parse_nd_elements(stream, potential_dims)
                            # Verify we consumed all bytes
                            if stream.tell() == len(obj):
                                return result
                        except Exception:
                            pass
            except Exception:
                pass
            
            # Reset and try as 1D array
            stream.seek(current_pos)
        
        # Parse as 1D array - first_value is the count
        # Reset to beginning and re-read
        stream.seek(4)  # Skip the first I32 (count)
        elements = []
        for _ in range(first_value):
            element = self.element_type.parse_stream(stream)
            elements.append(element)
        
        return elements
    
    def _parse_nd_elements(self, stream, dims: List[int]) -> List:
        """Parse ND array elements and reshape to nested list."""
        total_elements = 1
        for d in dims:
            total_elements *= d
        
        if total_elements == 0:
            return self._create_empty_nested_list(dims)
        
        # Read elements in row-major order
        elements = []
        for _ in range(total_elements):
            element = self.element_type.parse_stream(stream)
            elements.append(element)
        
        # Reshape to nested list based on dimensions
        return self._reshape_to_nested_list(elements, dims)
    
    def _encode(self, obj: List, context, path) -> bytes:
        """Convert Python list or nested list to bytes."""
        import io
        stream = io.BytesIO()
        
        if not obj:
            # Empty array
            stream.write(Int32ub.build(0))
            return stream.getvalue()
        
        # Determine dimensions from the nested list
        dims = self._get_dimensions(obj)
        num_dims = len(dims)
        
        if num_dims == 1:
            # 1D array - just write count and elements
            stream.write(Int32ub.build(dims[0]))
            for element in obj:
                stream.write(self.element_type.build(element))
        else:
            # ND array - write num_dims, dimension sizes, then elements
            stream.write(Int32ub.build(num_dims))
            for dim_size in dims:
                stream.write(Int32ub.build(dim_size))
            
            # Flatten and write elements in row-major order
            flat_elements = self._flatten_nested_list(obj)
            for element in flat_elements:
                stream.write(self.element_type.build(element))
        
        return stream.getvalue()
    
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
    
    This is a universal array type that handles 1D, 2D, 3D, and higher 
    dimensional arrays automatically based on the data structure.
    
    For 1D arrays:
        Format: [num_elements (I32)] [elements...]
        
    For ND arrays (2D, 3D, etc.):
        Format: [num_dims (I32)] [dim0 (I32)] ... [dimN-1 (I32)] [elements...]
    
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
        
        2D Array:
        >>> arr = LVArray(LVI32)
        >>> data = arr.build([[1, 2, 3], [4, 5, 6]])
        >>> print(data.hex())
        000000020000000200000003000000010000000200000003000000040000000500000006
        >>> arr.parse(data)
        [[1, 2, 3], [4, 5, 6]]
        
        3D Array (2×4×4):
        >>> arr = LVArray(LVI32)
        >>> data_3d = [[[1,2,3,4], [5,6,7,8], [9,10,11,12], [13,14,15,16]],
        ...            [[17,18,19,20], [21,22,23,24], [25,26,27,28], [29,30,31,32]]]
        >>> serialized = arr.build(data_3d)
    """
    return ArrayNDAdapter(element_type)


# Aliases for backwards compatibility and explicit usage
LVArray1D = LVArray
LVArray2D = LVArray
LVArrayND = LVArray


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

