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
from email.policy import default
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

LVArrayType: TypeAlias = Annotated[List[Any] | List[List[Any]], "LabVIEW Array "]
LVClusterType: TypeAlias = Annotated[tuple, "LabVIEW Cluster"]


# ============================================================================
# Array Implementation
# ============================================================================


def LVArray(element_type):
    # Adapter non nécessaire ici, PrefixedArray suffit pour 1D
    return PrefixedArray(Int32ub, element_type)


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

