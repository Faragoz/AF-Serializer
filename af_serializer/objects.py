"""
LabVIEW Object Types using Construct Library.

This module implements LabVIEW Object (LVObject) serialization.

LabVIEW Objects contain:
    - NumLevels: Number of inheritance levels
    - ClassName: Fully qualified class names (library + class)
    - VersionList: Version numbers for each level
    - ClusterData: Private data clusters for each level

Format Details:
    - NumLevels (I32): 0x00000000 for empty LabVIEW Object
    - ClassName: Total length (I8) + Pascal Strings + End marker (0x00) + Padding
    - VersionList: 8 bytes per level (4 x I16: major, minor, patch, build)
    - ClusterData: Size (I32) + data for each inheritance level
"""

from typing import TypeAlias, Annotated, List, Tuple, Optional, Any, Type
import warnings
import inspect
from construct import (
    Struct,
    Int8ub,
    Int16ub,
    Int32ub,
    GreedyBytes,
    Construct,
    Adapter,
    PrefixedArray
)
from .compound_types import LVArray


# ============================================================================
# Encoding Helper
# ============================================================================

def _get_encoding():
    """
    Get the appropriate encoding for LabVIEW strings.
    Uses 'mbcs' on Windows, 'latin-1' on other platforms.
    """
    import sys
    if sys.platform == 'win32':
        return 'mbcs'
    return 'latin-1'


# ============================================================================
# Type Aliases
# ============================================================================

LVObjectType: TypeAlias = Annotated[dict, "LabVIEW Object"]


# ============================================================================
# Declarative Construct Definitions
# ============================================================================

# Version struct for declarative version serialization
# Format: major(I16) minor(I16) patch(I16) build(I16)
VersionStruct = Struct(
    "major" / Int16ub,
    "minor" / Int16ub,
    "patch" / Int16ub,
    "build" / Int16ub,
)


# ============================================================================
# Helper Functions
# ============================================================================

def _calculate_padding(bytes_count: int, alignment: int = 4) -> int:
    """
    Calculate padding bytes needed to align to specified boundary.
    
    Args:
        bytes_count: Number of bytes already written/read
        alignment: Alignment boundary (default: 4 bytes for LabVIEW)
    
    Returns:
        Number of padding bytes needed
    """
    return (alignment - (bytes_count % alignment)) % alignment


def deserialize_type_hints(type_hints: dict, cluster_bytes: bytes) -> dict:
    """
    Deserialize cluster bytes to {field_name: value}.
    Reads bytes sequentially based on type hints order.
    
    This is the reverse of serialize_type_hints().
    
    Args:
        type_hints: Dictionary of {field_name: type_hint}
        cluster_bytes: Raw cluster data bytes
    
    Returns:
        Dictionary of {field_name: deserialized_value}
    """
    from .basic_types import (
        LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64,
        LVString, LVBoolean, LVDouble, LVSingle
    )
    from .compound_types import ArrayAdapter
    import io
    
    if not type_hints or not cluster_bytes:
        return {}
    
    stream = io.BytesIO(cluster_bytes)
    result = {}
    
    for attr_name, attr_type in type_hints.items():
        try:
            # Deserialize based on type hint
            if hasattr(attr_type, 'parse_stream'):
                # It's a Construct type (LVI32, LVU16, LVString, LVArray, etc.)
                value = attr_type.parse_stream(stream)
            elif attr_type == str:
                value = LVString.parse_stream(stream)
            elif attr_type == bool:
                value = LVBoolean.parse_stream(stream)
            elif attr_type == int:
                value = LVI32.parse_stream(stream)
            elif attr_type == float:
                value = LVDouble.parse_stream(stream)
            else:
                # Unknown type - try to read as bytes
                warnings.warn(f"Unknown type hint for '{attr_name}': {attr_type}, skipping")
                continue
            
            result[attr_name] = value
        except Exception as e:
            warnings.warn(f"Failed to deserialize field '{attr_name}': {e}")
            break  # Stop reading if we encounter an error
    
    return result


# ============================================================================
# LVObject Implementation
# ============================================================================

class LVObjectAdapter(Adapter):
    """
    Adapter for LabVIEW Object type.
    
    LabVIEW objects support inheritance and contain:
    1. NumLevels (I32): Number of inheritance levels (0 for empty object)
    2. ClassName: ONLY the most derived class name (library:class format)
    3. VersionList: Version for EACH level (including all parents)
    4. ClusterData: Private data for EACH level (including all parents)
    
    IMPORTANT: The ClassName field contains ONLY the final derived class,
    not the full inheritance chain. However, NumLevels indicates how many
    levels exist, and VersionList/ClusterData have entries for all levels.
    
    Example - Empty LVObject:
        0000 0000
    
    Example - Actor Object (empty):
        NumLevels: 0000 0001 (1 level)
        ClassName: 25 15 "Actor Framework.lvlib" 0D "Actor.lvclass" 00 [padding]
        VersionList: 0000 0001 (version 1.0.0.1)
        ClusterData: 0000 0000 0000 0000 (empty)
    
    Example - Three-level inheritance (Message -> Serializable Msg -> echo general Msg):
        NumLevels: 0000 0003 (3 levels)
        ClassName: 2A 0F "Commander.lvlib" 18 "echo general Msg.lvclass" 00 [padding]
                   (ONLY the most derived class, not Message or Serializable Msg)
        VersionList: 01000000 01000007 01000000 (3 versions, one per level)
        ClusterData: [empty] [empty] [0x11 "Hello World" 0x00] (3 data sections)
    """
    
    def __init__(self):
        """Initialize LVObject adapter."""
        super().__init__(GreedyBytes)
    

    def _decode(self, obj: bytes, context, path) -> Any:
        """
        Convert bytes to Python object.
        
        Returns either:
        - An instance of a @lvclass decorated class (if found in registry)
        - A dict representing the LVObject (if class not in registry)
        """
        import io
        from .decorators import get_lvclass_by_name
        
        stream = io.BytesIO(obj)
        encoding = _get_encoding()
        
        # Read NumLevels
        num_levels_bytes = stream.read(4)
        num_levels = Int32ub.parse(num_levels_bytes)
        
        if num_levels == 0:
            # Empty object
            warnings.warn("Empty LVObject encountered (num_levels=0)")
            return {
                "num_levels": 0,
                "class_name": None,
                "versions": [],
                "cluster_data": []
            }
        
        # Read ClassName section (ONLY the most derived class)
        # Format: total_length + Pascal strings + end marker (0x00)
        total_length = Int8ub.parse(stream.read(1))
        
        # Read Pascal strings until we hit end marker (length = 0)
        pascal_strings = []
        bytes_read_in_section = 0
        
        while True:
            str_length = Int8ub.parse(stream.read(1))
            bytes_read_in_section += 1
            
            if str_length == 0:
                # End marker found
                break
            
            str_data = stream.read(str_length).decode(encoding)
            bytes_read_in_section += str_length
            pascal_strings.append(str_data)
        
        # Determine library and classname based on number of strings
        if len(pascal_strings) == 1:
            # No library, just class name
            library = ""
            classname = pascal_strings[0]
        elif len(pascal_strings) >= 2:
            # Library + classname (and possibly more, but we only care about first 2)
            library = pascal_strings[0]
            classname = pascal_strings[1]
        else:
            # No strings found - error case
            library = ""
            classname = ""
        
        # Build full class name for registry lookup
        if library:
            full_class_name = f"{library}:{classname}"
        else:
            full_class_name = classname
        
        # Read padding to align to 4-byte boundary
        bytes_read = 1 + bytes_read_in_section
        padding_needed = _calculate_padding(bytes_read)
        if padding_needed > 0:
            stream.read(padding_needed)

        
        # Always read VersionList (8 bytes per level: 4 x I16)
        # LabVIEW always includes versions when num_levels > 0
        versions = []
        for _ in range(num_levels):
            version_dict = VersionStruct.parse_stream(stream)
            versions.append((version_dict.major, version_dict.minor, version_dict.patch, version_dict.build))
        
        # Read ClusterData for each level
        cluster_data = []
        for i in range(num_levels):
            try:
                size = Int32ub.parse_stream(stream)
                
                if size > 0:
                    cluster_data.append(stream.read(size))
                else:
                    cluster_data.append(b'')
            except Exception:
                cluster_data.append(b'')
        
        # Try to find the class in the registry
        target_class = get_lvclass_by_name(full_class_name)
        
        if target_class is None:
            # Class not found in registry - return dict with raw data
            warnings.warn(
                f"Class '{full_class_name}' not found in registry. "
                f"Returning dict with raw bytes. "
                f"Ensure the class is decorated with @lvclass and imported before calling lvunflatten(). "
                f"Use get_lvclass_by_name('{full_class_name}') to check if the class is registered."
            )
            return {
                "num_levels": num_levels,
                "class_name": full_class_name,
                "versions": versions,
                "cluster_data": cluster_data
            }
        
        # Found the class - try to create instance and populate fields
        try:
            instance = target_class()
            
            # Get all type hints from the inheritance chain
            inheritance_chain = []
            for base in inspect.getmro(target_class):
                if hasattr(base, '__is_lv_class__') and base.__is_lv_class__:
                    inheritance_chain.append(base)
            
            # Reverse to go from root to derived (matching cluster_data order)
            inheritance_chain.reverse()
            
            # Deserialize each level's cluster data and populate instance
            for i, level_class in enumerate(inheritance_chain):
                if i >= len(cluster_data):
                    break
                    
                level_hints = level_class.__annotations__ if hasattr(level_class, '__annotations__') else {}
                cluster_bytes = cluster_data[i]
                
                if level_hints and isinstance(cluster_bytes, bytes) and len(cluster_bytes) > 0:
                    try:
                        field_values = deserialize_type_hints(level_hints, cluster_bytes)
                        for field_name, value in field_values.items():
                            setattr(instance, field_name, value)
                    except Exception as e:
                        warnings.warn(
                            f"Failed to deserialize cluster data for level {i} ({level_class.__name__}): {e}. "
                            f"Expected fields: {list(level_hints.keys())}. "
                            f"Cluster bytes length: {len(cluster_bytes)}."
                        )
            
            return instance
            
        except Exception as e:
            warnings.warn(f"Failed to create instance of '{full_class_name}': {e}. Returning dict.")
            return {
                "num_levels": num_levels,
                "class_name": full_class_name,
                "versions": versions,
                "cluster_data": cluster_data
            }
    
    def _encode(self, obj: Any, context, path) -> bytes:
        """Convert Python object (dict or @lvclass instance) to bytes for LVObject."""
        import io
        
        # If obj is an @lvclass instance, convert it to dict first
        if hasattr(obj.__class__, '__is_lv_class__') and obj.__class__.__is_lv_class__:
            obj = _instance_to_lvobject_dict(obj)
        
        stream = io.BytesIO()
        encoding = _get_encoding()
        
        num_levels = obj.get("num_levels", 0)
        
        # Write NumLevels
        stream.write(Int32ub.build(num_levels))
        
        if num_levels == 0:
            # Empty object
            return stream.getvalue()
        
        # Get the most derived class name
        class_name_data = obj.get("class_name", "")
        versions = obj.get("versions", [])
        cluster_data = obj.get("cluster_data", [])
        
        # Parse the class name (library:class format)
        if ':' in class_name_data:
            parts = class_name_data.split(':', 1)
            library = parts[0]
            classname = parts[1]
        else:
            library = ""
            classname = class_name_data
        
        # Calculate total length for ClassName section (ONLY the most derived class)
        total_length = 0
        if library:
            total_length += 1 + len(library.encode(encoding))  # Length byte + library
        total_length += 1 + len(classname.encode(encoding))  # Length byte + class
        total_length += 1  # End marker
        
        # Write total length
        stream.write(Int8ub.build(total_length))
        
        # Write the most derived class name only
        if library:
            lib_bytes = library.encode(encoding)
            stream.write(Int8ub.build(len(lib_bytes)))
            stream.write(lib_bytes)
        
        # Write class name (Pascal string)
        class_bytes = classname.encode(encoding)
        stream.write(Int8ub.build(len(class_bytes)))
        stream.write(class_bytes)
        
        # Write end marker
        stream.write(b'\x00')
        
        # Write padding to align to 4-byte boundary
        bytes_written = 1 + total_length
        padding_needed = _calculate_padding(bytes_written)
        if padding_needed > 0:
            stream.write(b'\x00' * padding_needed)
        
        # Convert cluster_data to bytes if needed
        cluster_bytes_list = []
        for data in cluster_data:
            if isinstance(data, bytes):
                cluster_bytes_list.append(data)
            else:
                cluster_bytes_list.append(b'')
        
        all_clusters_empty = all(len(cb) == 0 for cb in cluster_bytes_list)

        # Always write VersionList for all levels
        for version in versions:
            if not isinstance(version, tuple) or len(version) != 4:
                raise ValueError(f"Version must be a 4-tuple (major, minor, patch, build), got {version}")
            version_dict = {"major": version[0], "minor": version[1], "patch": version[2], "build": version[3]}
            stream.write(VersionStruct.build(version_dict))
        
        # Write ClusterData ONLY if at least one cluster has data
        if not all_clusters_empty:
            for cluster_bytes in cluster_bytes_list:
                stream.write(Int32ub.build(len(cluster_bytes)))
                if len(cluster_bytes) > 0:
                    stream.write(cluster_bytes)
        
        return stream.getvalue()


def _instance_to_lvobject_dict(instance: Any) -> dict:
    """
    Convert an @lvclass instance to a LabVIEW Object dictionary.
    
    Args:
        instance: An instance of an @lvclass decorated class
        
    Returns:
        Dictionary suitable for LVObject serialization
    """
    # Walk up the inheritance chain to find all @lvclass decorated base classes
    inheritance_chain = []
    for base in inspect.getmro(instance.__class__):
        if hasattr(base, '__is_lv_class__') and base.__is_lv_class__:
            inheritance_chain.append(base)

    # Reverse to go from root to derived
    inheritance_chain.reverse()
    
    num_levels = len(inheritance_chain)
    
    # Collect versions for all levels (append then reverse for O(n) instead of O(n²))
    versions = []
    for level_class in inheritance_chain:
        versions.append(level_class.__lv_version__)
    versions.reverse()
    
    # Build cluster data for each level
    cluster_data_list = []
    for i, level_class in enumerate(inheritance_chain):
        level_hints = level_class.__annotations__ if hasattr(level_class, '__annotations__') else {}
        level_values = {}
        for attr_name in level_hints.keys():
            if hasattr(instance, attr_name):
                level_values[attr_name] = getattr(instance, attr_name)

        cluster_bytes = serialize_type_hints(level_hints, level_values)
        cluster_data_list.append(cluster_bytes)
    
    # Use only the most derived class name
    most_derived = inheritance_chain[-1]
    full_class_name = f"{most_derived.__lv_library__}.lvlib:{most_derived.__lv_class_name__}.lvclass" if most_derived.__lv_library__ else f"{most_derived.__lv_class_name__}.lvclass"
    
    return {
        "num_levels": num_levels,
        "class_name": full_class_name,
        "versions": versions,
        "cluster_data": cluster_data_list
    }


def LVObject() -> Construct:
    """
    Create a LabVIEW Object construct.
    
    LabVIEW objects support inheritance with multiple levels.
    Each level has a class name, version, and private data cluster.
    
    Returns:
        Construct that can serialize/deserialize LVObjects
    
    Example - Empty object:
        >>> obj_construct = LVObject()
        >>> data = obj_construct.build({
        ...     "num_levels": 0,
        ...     "class_name": None,
        ...     "versions": [],
        ...     "cluster_data": []
        ... })
        >>> print(data.hex())
        00000000
    
    Example - Single level object:
        >>> obj_construct = LVObject()
        >>> data = obj_construct.build({
        ...     "num_levels": 1,
        ...     "class_name": "Actor Framework.lvlib:Actor.lvclass",
        ...     "versions": [(1, 0, 0, 0)],
        ...     "cluster_data": [b'']
        ... })
    
    Example - Three-level inheritance:
        >>> # Message -> Serializable Msg -> echo general Msg
        >>> # Only the MOST DERIVED class name is stored!
        >>> obj_construct = LVObject()
        >>> data = obj_construct.build({
        ...     "num_levels": 3,
        ...     "class_name": "Commander.lvlib:echo general Msg.lvclass",
        ...     "versions": [(1, 0, 0, 0), (1, 0, 0, 7), (1, 0, 0, 0)],
        ...     "cluster_data": [b'', b'', ...]
        ... })
    """
    return LVObjectAdapter()


# ============================================================================
# Helper Functions
# ============================================================================

def serialize_type_hints(type_hints: dict, values: dict) -> bytes:
    """
    Serialize type hints and their values to cluster data.
    
    IMPORTANT: If ANY type hint has a declared value (exists in values dict),
    then ALL type hints must be serialized with their values or default empty values.
    
    Args:
        type_hints: Dictionary of {field_name: type_hint}
        values: Dictionary of {field_name: actual_value}
    
    Returns:
        Serialized cluster data as bytes
    """
    from .basic_types import (
        LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64,
        LVString, LVBoolean, LVDouble, LVSingle
    )
    from .compound_types import ArrayAdapter
    import io
    
    if not type_hints:
        return b''
    
    # Check if ANY value is declared (not using defaults)
    has_any_value = any(field_name in values for field_name in type_hints.keys())
    
    if not has_any_value:
        # No values declared - return empty cluster
        return b''
    
    # If ANY value is declared, serialize ALL type hints with defaults for missing ones
    stream = io.BytesIO()
    
    for attr_name, attr_type in type_hints.items():
        # Get value or use default
        if attr_name in values:
            value = values[attr_name]
        else:
            # Use default empty value based on type
            if hasattr(attr_type, 'build'):
                if attr_type == LVString:
                    value = ""
                elif attr_type == LVBoolean:
                    value = False
                elif attr_type in (LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64):
                    value = 0
                elif attr_type in (LVDouble, LVSingle):
                    value = 0.0
                elif isinstance(attr_type, ArrayAdapter):
                    value = []
                else:
                    continue
            elif attr_type == str:
                value = ""
            elif attr_type == bool:
                value = False
            elif attr_type == int:
                value = 0
            elif attr_type == float:
                value = 0.0
            elif attr_type == list:
                value = []
            else:
                continue
        
        # Serialize based on type hint
        if hasattr(attr_type, 'build'):
            stream.write(attr_type.build(value))
        elif attr_type == str or isinstance(value, str):
            stream.write(LVString.build(value))
        elif attr_type == bool or isinstance(value, bool):
            stream.write(LVBoolean.build(value))
        elif attr_type == int or isinstance(value, int):
            stream.write(LVI32.build(value))
        elif attr_type == float or isinstance(value, float):
            stream.write(LVDouble.build(value))
    
    return stream.getvalue()


def create_empty_lvobject() -> dict:
    """
    Create an empty LabVIEW Object.
    
    Returns:
        Dictionary representing an empty LVObject
    """
    return {
        "num_levels": 0,
        "class_name": None,
        "versions": [],
        "cluster_data": []
    }


def create_lvobject(class_name: str = None, 
                    num_levels: int = None,
                    versions: List[tuple] = None,
                    cluster_data: Optional[List] = None) -> dict:
    """
    Create a LabVIEW Object with inheritance.
    
    IMPORTANT: The class_name parameter should contain ONLY the most derived
    class name (library:class format), NOT the full inheritance chain.
    However, num_levels indicates how many inheritance levels exist, and
    versions/cluster_data should have entries for ALL levels.
    
    Args:
        class_name: The most derived class name (library:class format)
        num_levels: Number of inheritance levels
        versions: List of version tuples for each level
        cluster_data: Optional list of private data for EACH level
    
    Returns:
        Dictionary representing an LVObject
    
    Example:
        >>> obj = create_lvobject(
        ...     class_name="Commander.lvlib:echo general Msg.lvclass",
        ...     num_levels=3,
        ...     versions=[(1, 0, 0, 0), (1, 0, 0, 7), (1, 0, 0, 0)],
        ...     cluster_data=[b'', b'', cluster_bytes]
        ... )
    """
    if class_name is None:
        raise ValueError("class_name is required")
    
    if num_levels is None:
        num_levels = 1
    
    if versions is None:
        versions = [(1, 0, 0, 0)] * num_levels
    
    if cluster_data is None:
        cluster_data = [b''] * num_levels
    
    return {
        "num_levels": num_levels,
        "class_name": class_name,
        "versions": versions,
        "cluster_data": cluster_data
    }
