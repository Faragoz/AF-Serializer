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

from typing import TypeAlias, Annotated, List, Tuple, Optional
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
    
    def __init__(self, cluster_constructs: Optional[List[Construct]] = None):
        """
        Initialize LVObject adapter.
        
        Args:
            cluster_constructs: Optional list of Construct definitions for private data
                              at each inheritance level. If None, assumes empty clusters.
        """
        self.cluster_constructs = cluster_constructs or []
        super().__init__(GreedyBytes)
    

    def _decode(self, obj: bytes, context, path) -> dict:
        """Convert bytes to Python dict representing LVObject."""
        import io
        stream = io.BytesIO(obj)
        
        # Read NumLevels
        num_levels_bytes = stream.read(4)
        num_levels = Int32ub.parse(num_levels_bytes)
        
        if num_levels == 0:
            # Empty object - maintain backwards compat with class_names
            return {
                "num_levels": 0,
                "class_name": None,
                "class_names": [],  # Backwards compatibility
                "versions": [],
                "cluster_data": []
            }
        
        # Read ClassName section (ONLY the most derived class)
        # Format: total_length + Pascal strings + end marker (0x00)
        total_length = Int8ub.parse(stream.read(1))
        print(f"Debug: ClassName total length = {total_length}")
        
        # Read Pascal strings until we hit end marker (length = 0)
        pascal_strings = []
        bytes_read_in_section = 0
        
        while True:
            str_length = Int8ub.parse(stream.read(1))
            bytes_read_in_section += 1
            
            if str_length == 0:
                # End marker found
                break
            
            str_data = stream.read(str_length).decode('mbcs')
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
        
        # Store only the most derived class name
        class_name = classname if not library else f"{library}:{classname}"
        
        # Read padding to align to 4-byte boundary
        # bytes_read = 1 (total_length byte) + bytes_read_in_section (strings + end marker)
        bytes_read = 1 + bytes_read_in_section
        padding_needed = _calculate_padding(bytes_read)
        if padding_needed > 0:
            stream.read(padding_needed)

        
        # Always read VersionList (8 bytes per level: 4 x I16)
        # Use declarative VersionStruct for clean parsing
        peek = stream.read(1)
        versions = []
        if peek == b'\x00':
            # Pas de VersionList, valeurs par défaut pour tous les niveaux
            versions = [(0, 0, 0, 0)] * num_levels
            # Avancer le curseur pour garder l’alignement
            stream.read(8 * num_levels - 1)
        else:
            # VersionList présent, revenir en arrière
            stream.seek(-1, 1)
            for _ in range(num_levels):
                version_dict = VersionStruct.parse_stream(stream)
                versions.append((version_dict.major, version_dict.minor, version_dict.patch, version_dict.build))
        
        # Try to read ClusterData for each level
        # Format: size (I32) + data
        # If there are no more bytes (all clusters empty), create empty cluster list
        cluster_data = []
        for i in range(num_levels):
            try:
                # Try to read cluster size
                size = Int32ub.parse_stream(stream)
                
                if size > 0:
                    # Read the actual cluster data
                    if i < len(self.cluster_constructs):
                        # Use provided construct to parse
                        data = self.cluster_constructs[i].parse(stream.read(size))
                        cluster_data.append(data)
                    else:
                        # No construct, store raw bytes
                        cluster_data.append(stream.read(size))
                else:
                    # Empty cluster
                    cluster_data.append(b'')
            except Exception as e:
                # No more data available - all remaining clusters are empty
                # This happens when all clusters are empty (no cluster data section in stream)
                # Note: Using broad Exception catch because Construct can raise various exceptions
                # (StreamError, etc.) when stream runs out of data. KeyboardInterrupt and
                # SystemExit are BaseException subclasses, so they won't be caught here.
                cluster_data.append(b'')
        
        return {
            "num_levels": num_levels,
            "class_name": class_name,  # Only the most derived class
            "class_names": [class_name],  # Backwards compatibility - list with single item
            "versions": versions,  # All levels
            "cluster_data": cluster_data  # All levels
        }
    
    def _encode(self, obj: dict, context, path) -> bytes:
        """Convert Python dict to bytes for LVObject."""
        import io
        stream = io.BytesIO()
        
        num_levels = obj.get("num_levels", 0)
        
        # Write NumLevels
        stream.write(Int32ub.build(num_levels))
        
        if num_levels == 0:
            # Empty object
            return stream.getvalue()
        
        # Get the most derived class name (could be single string or last in list for backwards compat)
        class_name_data = obj.get("class_name") or (obj.get("class_names", [])[-1] if obj.get("class_names") else "")
        versions = obj.get("versions", [])
        cluster_data = obj.get("cluster_data", [])
        
        # Parse the class name (library:class format)
        if ':' in class_name_data:
            parts = class_name_data.split(':', 1)  # Limiter à 1 split pour éviter les erreurs
            library = parts[0]
            classname = parts[1]
        else:
            library = ""
            classname = class_name_data
        
        # Calculate total length for ClassName section (ONLY the most derived class)
        # Format: [length bytes] + [strings] + [end marker]
        # When library is present: lib_len + lib + class_len + class + 0x00
        # When library is absent: class_len + class + 0x00
        total_length = 0
        if library:
            total_length += 1 + len(library.encode('mbcs'))  # Length byte + library
        total_length += 1 + len(classname.encode('mbcs'))  # Length byte + class
        total_length += 1  # End marker
        
        # Write total length
        stream.write(Int8ub.build(total_length))
        
        # Write the most derived class name only
        # Write library (Pascal string) only if present
        if library:
            lib_bytes = library.encode('mbcs')
            stream.write(Int8ub.build(len(lib_bytes)))
            stream.write(lib_bytes)
        
        # Write class name (Pascal string)
        class_bytes = classname.encode('mbcs')
        stream.write(Int8ub.build(len(class_bytes)))
        stream.write(class_bytes)
        
        # Write end marker
        stream.write(b'\x00')
        
        # Write padding to align to 4-byte boundary
        bytes_written = 1 + total_length
        padding_needed = _calculate_padding(bytes_written)
        if padding_needed > 0:
            stream.write(b'\x00' * padding_needed)
        
        # Check if all clusters are empty
        # First, convert cluster_data to bytes to check sizes
        cluster_bytes_list = []
        for i, data in enumerate(cluster_data):
            if i < len(self.cluster_constructs):
                cluster_bytes = self.cluster_constructs[i].build(data)
            elif isinstance(data, bytes):
                cluster_bytes = data
            else:
                cluster_bytes = b''
            cluster_bytes_list.append(cluster_bytes)
        
        all_clusters_empty = all(len(cb) == 0 for cb in cluster_bytes_list)

        # If all clusters are empty and no versions provided, use default versions
        if all_clusters_empty:
            versions = [(0, 0, 0, 0)]
        
        # Always write VersionList when num_levels > 0
        # Use declarative VersionStruct for clean serialization
        for version in versions:
            # Version as tuple (major, minor, patch, build)
            if not isinstance(version, tuple) or len(version) != 4:
                raise ValueError(f"Version must be a 4-tuple (major, minor, patch, build), got {version}")
            version_dict = {"major": version[0], "minor": version[1], "patch": version[2], "build": version[3]}
            stream.write(VersionStruct.build(version_dict))
        
        # Write ClusterData ONLY if at least one cluster has data
        # When all clusters are empty, don't write any cluster data (not even size prefixes)
        if not all_clusters_empty:
            for cluster_bytes in cluster_bytes_list:
                # Write size prefix
                stream.write(Int32ub.build(len(cluster_bytes)))
                # Write data
                if len(cluster_bytes) > 0:
                    stream.write(cluster_bytes)
        
        return stream.getvalue()


def LVObject(cluster_constructs: Optional[List[Construct]] = None) -> Construct:
    """
    Create a LabVIEW Object construct.
    
    LabVIEW objects support inheritance with multiple levels.
    Each level has a class name, version, and private data cluster.
    
    Args:
        cluster_constructs: Optional list of Construct definitions for private data
                          at each inheritance level
    
    Returns:
        Construct that can serialize/deserialize LVObjects
    
    Example - Empty object:
        >>> obj_construct = LVObject()
        >>> data = obj_construct.build({
        ...     "num_levels": 0,
        ...     "class_names": [],
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
    return LVObjectAdapter(cluster_constructs)


# ============================================================================
# Helper Functions
# ============================================================================

def serialize_type_hints(type_hints: dict, values: dict) -> bytes:
    """
    Serialize type hints and their values to cluster data.
    
    This function handles the actual serialization of type hints, moving
    the responsibility from the decorator to Object.py.
    
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
                # It's a Construct type - use appropriate default
                if attr_type == LVString:
                    value = ""
                elif attr_type == LVBoolean:
                    value = False
                elif attr_type in (LVI32, LVU32, LVI16, LVU16, LVI8, LVU8, LVI64, LVU64):
                    value = 0
                elif attr_type in (LVDouble, LVSingle):
                    value = 0.0
                elif isinstance(attr_type, ArrayAdapter):
                    # LVArray, LVArray1D, LVArray2D, LVArrayND - default to empty list
                    value = []
                else:
                    print(f"Warning: Unknown Construct type for attribute '{attr_name}:{attr_type}, skipping serialization.")
                    # Unknown Construct type - skip
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
                # Python list type hint - default to empty list
                value = []
            else:
                # Unknown type - skip
                continue
        
        # Serialize based on type hint
        # Check for Construct types FIRST (they have .build method)
        if hasattr(attr_type, 'build'):
            # It's a Construct type (LVI32, LVU16, LVString, LVArray, etc.)
            stream.write(attr_type.build(value))
        # Then check for Python types
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
        "class_names": [],  # Backwards compatibility
        "versions": [],
        "cluster_data": []
    }


def create_lvobject(class_name_or_names = None, 
                    versions_or_num_levels = None,
                    cluster_data: Optional[List] = None,
                    **kwargs) -> dict:
    """
    Create a LabVIEW Object with inheritance.
    
    IMPORTANT: The class_name parameter should contain ONLY the most derived
    class name (library:class format), NOT the full inheritance chain.
    However, num_levels indicates how many inheritance levels exist, and
    versions/cluster_data should have entries for ALL levels.
    
    Supports both old and new APIs:
    - Old: create_lvobject(class_names_list, versions_list, cluster_data_list)
    - New: create_lvobject(class_name=str, num_levels=int, versions=list, cluster_data=list)
    
    Args:
        class_name_or_names: Either a single class name (str) or list of class names (for old API)
        versions_or_num_levels: Either list of versions or num_levels (int)
        cluster_data: Optional list of private data for EACH level
        **kwargs: Keyword arguments for new API (class_name, num_levels, versions, class_names)
    
    Returns:
        Dictionary representing an LVObject
    
    Example (new API - single level):
        >>> obj = create_lvobject(
        ...     class_name="Actor Framework.lvlib:Actor.lvclass",
        ...     num_levels=1,
        ...     versions=[(1, 0, 0, 0)],
        ...     cluster_data=[b'']
        ... )
    
    Example (new API - three-level inheritance: Message -> Serializable Msg -> echo general Msg):
        >>> obj = create_lvobject(
        ...     class_name="Commander.lvlib:echo general Msg.lvclass",  # Only most derived
        ...     num_levels=3,  # But indicates 3 levels total
        ...     versions=[(1, 0, 0, 0), (1, 0, 0, 7), (1, 0, 0, 0)],  # 3 versions in tuple format
        ...     cluster_data=[b'', b'', cluster_bytes]  # 3 data sections
        ... )
    
    Example (old API - backwards compatibility using positional args):
        >>> obj = create_lvobject(
        ...     ["Level1.lvlib:Class1.lvclass", "Level2.lvlib:Class2.lvclass"],
        ...     [(1, 0, 0, 0), (1, 0, 0, 0)],
        ...     [b'', b'']
        ... )
    """
    # Determine if using old API (positional with list) or new API (keyword args)
    class_names_kwarg = kwargs.get('class_names')
    class_name_kwarg = kwargs.get('class_name')
    num_levels_kwarg = kwargs.get('num_levels')
    versions_kwarg = kwargs.get('versions')
    
    # Old API detection: first arg is a list
    if isinstance(class_name_or_names, list):
        # Old API: create_lvobject(class_names_list, versions_list, cluster_data_list)
        class_names = class_name_or_names
        versions = versions_or_num_levels if versions_or_num_levels is not None else []
        num_levels = len(class_names)
        class_name = class_names[-1] if class_names else ""
        if cluster_data is None:
            cluster_data = [b''] * num_levels
    elif class_names_kwarg is not None:
        # Keyword arg with old name: class_names=list
        class_names = class_names_kwarg
        versions = versions_kwarg if versions_kwarg is not None else []
        num_levels = len(class_names)
        class_name = class_names[-1] if class_names else ""
        if cluster_data is None:
            cluster_data = [b''] * num_levels
    else:
        # New API: class_name=str, num_levels=int
        class_name = class_name_kwarg or class_name_or_names
        num_levels = num_levels_kwarg or (versions_or_num_levels if isinstance(versions_or_num_levels, int) else 1)
        versions = versions_kwarg or (versions_or_num_levels if isinstance(versions_or_num_levels, list) else [0x01000000] * num_levels)
        
        if class_name is None:
            raise ValueError("class_name is required")
        if cluster_data is None:
            cluster_data = [b''] * num_levels
    
    return {
        "num_levels": num_levels,
        "class_name": class_name,
        "class_names": [class_name],  # Backwards compatibility
        "versions": versions,
        "cluster_data": cluster_data
    }
