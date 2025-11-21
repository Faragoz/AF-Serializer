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
    - VersionList: 4 bytes (I32) per level representing version (major, minor, patch, build)
    - ClusterData: Concatenated cluster data for each inheritance level
"""

from typing import TypeAlias, Annotated, List, Tuple, Optional
from construct import (
    Struct,
    Int8ub,
    Int32ub,
    Bytes,
    GreedyBytes,
    Construct,
    Adapter,
    this,
    Padding,
)


# ============================================================================
# Type Aliases
# ============================================================================

LVObjectType: TypeAlias = Annotated[dict, "LabVIEW Object"]


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
        total_length = Int8ub.parse(stream.read(1))
        
        # Read library name (Pascal string)
        lib_length = Int8ub.parse(stream.read(1))
        library = stream.read(lib_length).decode('utf-8')
        
        # Read class name (Pascal string)
        class_length = Int8ub.parse(stream.read(1))
        classname = stream.read(class_length).decode('utf-8')
        
        # Store only the most derived class name
        class_name = f"{library}:{classname}"
        
        # Read end marker
        end_marker = stream.read(1)
        
        # Read padding to align to 4-byte boundary
        # Calculate bytes: 1 (total_length) + actual string bytes + 1 (end marker)
        bytes_read = 1 + lib_length + 1 + class_length + 1 + 1
        padding_needed = (4 - (bytes_read % 4)) % 4
        if padding_needed > 0:
            stream.read(padding_needed)
        
        # Read VersionList (4 bytes per level - for ALL levels including parents)
        versions = []
        for _ in range(num_levels):
            version_bytes = stream.read(4)
            # Version format: [major][minor][patch][build] as single bytes
            version = Int32ub.parse(version_bytes)
            versions.append(version)
        
        # Read ClusterData for each level (ALL levels including parents)
        cluster_data = []
        for i in range(num_levels):
            if i < len(self.cluster_constructs):
                data = self.cluster_constructs[i].parse_stream(stream)
                cluster_data.append(data)
            else:
                # No construct definition - read remaining data as bytes
                # For the last level, read all remaining
                # For intermediate levels, assume empty (8 bytes of zeros is common)
                if i == num_levels - 1:
                    remaining = stream.read()
                    cluster_data.append(remaining)
                else:
                    # Try to read a chunk (8 bytes is common for empty clusters in LabVIEW)
                    EMPTY_CLUSTER_SIZE = 8  # LabVIEW standard for empty cluster padding
                    chunk = stream.read(EMPTY_CLUSTER_SIZE)
                    cluster_data.append(chunk if chunk else b'')
        
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
        parts = class_name_data.split(':')
        library = parts[0]
        classname = parts[1]
        
        # Calculate total length for ClassName section (ONLY the most derived class)
        total_length = 1 + len(library.encode('utf-8'))  # Length byte + library
        total_length += 1 + len(classname.encode('utf-8'))  # Length byte + class
        total_length += 1  # End marker
        
        # Write total length
        stream.write(Int8ub.build(total_length))
        
        # Write the most derived class name only
        # Write library (Pascal string)
        lib_bytes = library.encode('utf-8')
        stream.write(Int8ub.build(len(lib_bytes)))
        stream.write(lib_bytes)
        
        # Write class name (Pascal string)
        class_bytes = classname.encode('utf-8')
        stream.write(Int8ub.build(len(class_bytes)))
        stream.write(class_bytes)
        
        # Write end marker
        stream.write(b'\x00')
        
        # Write padding to align to 4-byte boundary
        bytes_written = 1 + total_length
        padding_needed = (4 - (bytes_written % 4)) % 4
        if padding_needed > 0:
            stream.write(b'\x00' * padding_needed)
        
        # Write VersionList
        for version in versions:
            stream.write(Int32ub.build(version))
        
        # Write ClusterData
        for i, data in enumerate(cluster_data):
            if i < len(self.cluster_constructs):
                stream.write(self.cluster_constructs[i].build(data))
            else:
                # Write raw bytes if no construct available
                if isinstance(data, bytes):
                    stream.write(data)
                # Note: Tuples without construct definitions are not supported.
                # Users should provide cluster_constructs or pre-serialize to bytes.
        
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
        ...     "versions": [0x01000000],
        ...     "cluster_data": [b'']
        ... })
    
    Example - Three-level inheritance:
        >>> # Message -> Serializable Msg -> echo general Msg
        >>> # Only the MOST DERIVED class name is stored!
        >>> obj_construct = LVObject()
        >>> data = obj_construct.build({
        ...     "num_levels": 3,
        ...     "class_name": "Commander.lvlib:echo general Msg.lvclass",
        ...     "versions": [0x01000000, 0x01000007, 0x01000000],
        ...     "cluster_data": [b'', b'', ...]
        ... })
    """
    return LVObjectAdapter(cluster_constructs)


# ============================================================================
# Helper Functions
# ============================================================================

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
        ...     versions=[0x01000000],
        ...     cluster_data=[b'']
        ... )
    
    Example (new API - three-level inheritance: Message -> Serializable Msg -> echo general Msg):
        >>> obj = create_lvobject(
        ...     class_name="Commander.lvlib:echo general Msg.lvclass",  # Only most derived
        ...     num_levels=3,  # But indicates 3 levels total
        ...     versions=[0x01000000, 0x01000007, 0x01000000],  # 3 versions
        ...     cluster_data=[b'', b'', cluster_bytes]  # 3 data sections
        ... )
    
    Example (old API - backwards compatibility):
        >>> obj = create_lvobject(
        ...     ["Level1.lvlib:Class1.lvclass", "Level2.lvlib:Class2.lvclass"],
        ...     [0x01000000, 0x01000000],
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
