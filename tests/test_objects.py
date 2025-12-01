"""
Unit tests for LabVIEW Object types.

These tests validate LVObject serialization and deserialization against
real HEX examples from LabVIEW documentation.
"""

import pytest
import warnings

from src import (
    LVObject, LVI32, LVU16, LVString, LVCluster,
    create_empty_lvobject, create_lvobject,
)


# ============================================================================
# Empty LVObject Tests
# ============================================================================

def test_lvobject_empty_serialization():
    """Validate empty LVObject serialization."""
    # Expected: 0000 0000
    obj_construct = LVObject()
    data = create_empty_lvobject()
    expected_hex = "00000000"
    
    result = obj_construct.build(data)
    
    assert result.hex() == expected_hex


def test_lvobject_empty_deserialization():
    """Test empty LVObject deserialization."""
    obj_construct = LVObject()
    data_bytes = bytes.fromhex("00000000")
    
    # Empty object will generate a warning
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        result = obj_construct.parse(data_bytes)
    
    assert result["num_levels"] == 0
    assert result["versions"] == []
    assert result["cluster_data"] == []


def test_lvobject_empty_roundtrip():
    """Test empty LVObject serialize → deserialize → compare."""
    obj_construct = LVObject()
    original = create_empty_lvobject()
    
    serialized = obj_construct.build(original)
    
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        deserialized = obj_construct.parse(serialized)
    
    assert deserialized["num_levels"] == original["num_levels"]


# ============================================================================
# Single Level Object Tests (Actor)
# ============================================================================

def test_lvobject_actor_serialization():
    """Validate Actor object serialization."""
    obj_construct = LVObject()
    data = create_lvobject(
        class_name="Actor Framework.lvlib:Actor.lvclass",
        num_levels=1,
        versions=[(1, 0, 0, 0)],
        cluster_data=[b'\x00\x00\x00\x00\x00\x00\x00\x00']
    )
    
    result = obj_construct.build(data)
    
    # Check NumLevels
    assert result[:4].hex() == "00000001"  # 1 level
    
    # Check that it starts with expected pattern
    assert result[4:5].hex() == "25"  # Total length byte


def test_lvobject_single_level_roundtrip():
    """Test single-level object roundtrip."""
    obj_construct = LVObject()
    original = create_lvobject(
        class_name="MyLibrary.lvlib:MyClass.lvclass",
        num_levels=1,
        versions=[(1, 0, 0, 0)],
        cluster_data=[b'']
    )
    
    serialized = obj_construct.build(original)
    
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        deserialized = obj_construct.parse(serialized)
    
    assert deserialized["num_levels"] == 1
    assert "MyLibrary.lvlib" in deserialized["class_name"]
    assert "MyClass.lvclass" in deserialized["class_name"]


# ============================================================================
# Three-Level Inheritance Tests (echo general Msg)
# ============================================================================

def test_lvobject_three_level_inheritance():
    """
    Test three-level inheritance object.
    """
    # Create cluster for third level data: "Hello World" + U16(0)
    cluster_construct = LVCluster(LVString, LVU16)
    cluster_data_3 = ("Hello World", 0)
    cluster_bytes_3 = cluster_construct.build(cluster_data_3)
    
    obj_construct = LVObject()
    data = create_lvobject(
        class_name="Commander.lvlib:echo general Msg.lvclass",
        num_levels=3,
        versions=[(1, 0, 0, 0), (1, 0, 0, 7), (1, 0, 0, 0)],
        cluster_data=[
            b'\x00\x00\x00\x00\x00\x00\x00\x00',  # Empty for level 1
            b'\x00\x00\x00\x00\x00\x00\x00\x00',  # Empty for level 2
            cluster_bytes_3  # "Hello World" + U16(0) for level 3
        ]
    )
    
    result = obj_construct.build(data)
    
    # Check NumLevels
    assert result[:4].hex() == "00000003"  # 3 levels


def test_lvobject_three_level_class_names():
    """
    Test that three-level object has correct structure.
    
    IMPORTANT: According to LabVIEW spec, only the MOST DERIVED class name
    is stored in the serialized format.
    """
    obj_construct = LVObject()
    data = create_lvobject(
        class_name="Commander.lvlib:echo general Msg.lvclass",
        num_levels=3,
        versions=[(1, 0, 0, 0), (1, 0, 0, 7), (1, 0, 0, 0)],
        cluster_data=[b'', b'', b'']
    )
    
    serialized = obj_construct.build(data)
    
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        deserialized = obj_construct.parse(serialized)
    
    # Verify correct structure per LabVIEW spec
    assert deserialized["num_levels"] == 3  # 3 levels of inheritance
    assert "echo general Msg.lvclass" in deserialized["class_name"]
    assert len(deserialized["versions"]) == 3  # 3 versions (one per level)
    assert len(deserialized["cluster_data"]) == 3  # 3 data sections (one per level)


def test_lvobject_versions():
    """Test that version information is preserved."""
    cluster_construct = LVCluster(LVString, LVU16)
    cluster_data_3 = ("Hello World", 0)
    cluster_bytes_3 = cluster_construct.build(cluster_data_3)

    obj_construct = LVObject()
    data = create_lvobject(
        class_name="Test.lvlib:Test.lvclass",
        num_levels=1,
        versions=[(1, 2, 3, 4)],
        cluster_data=[cluster_bytes_3]
    )
    
    serialized = obj_construct.build(data)
    
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        deserialized = obj_construct.parse(serialized)
    
    assert deserialized["versions"][0] == (1, 2, 3, 4)


# ============================================================================
# Helper Function Tests
# ============================================================================

def test_create_empty_lvobject_helper():
    """Test create_empty_lvobject helper function."""
    obj = create_empty_lvobject()
    
    assert obj["num_levels"] == 0
    assert obj["versions"] == []
    assert obj["cluster_data"] == []


def test_create_lvobject_helper():
    """Test create_lvobject helper function."""
    obj = create_lvobject(
        class_name="Test.lvlib:Test.lvclass",
        num_levels=1,
        versions=[(1, 0, 0, 0)]
    )
    
    assert obj["num_levels"] == 1
    assert len(obj["versions"]) == 1
    assert len(obj["cluster_data"]) == 1


def test_create_lvobject_with_data():
    """Test create_lvobject with custom cluster data."""
    cluster_data = [b'\x00\x00\x00\x00']
    obj = create_lvobject(
        class_name="Test.lvlib:Test.lvclass",
        num_levels=1,
        versions=[(1, 0, 0, 0)],
        cluster_data=cluster_data
    )
    
    assert obj["cluster_data"] == cluster_data


# ============================================================================
# Integration Tests
# ============================================================================

def test_lvobject_with_complex_data():
    """Test LVObject with complex cluster data."""
    # Create a cluster for the private data
    cluster_construct = LVCluster(LVI32, LVString)
    cluster_data = (42, "Test Data")
    cluster_bytes = cluster_construct.build(cluster_data)
    
    obj_construct = LVObject()
    obj = create_lvobject(
        class_name="MyLib.lvlib:MyClass.lvclass",
        num_levels=1,
        versions=[(1, 0, 0, 0)],
        cluster_data=[cluster_bytes]
    )
    
    serialized = obj_construct.build(obj)
    
    # Should serialize without error
    assert len(serialized) > 4  # More than just NumLevels


def test_lvobject_multiple_versions():
    """Test LVObject with different version numbers."""
    obj_construct = LVObject()
    obj = create_lvobject(
        class_name="Derived.lvlib:Derived.lvclass",
        num_levels=2,
        versions=[(1, 0, 0, 0), (2, 0, 0, 5)],
        cluster_data=[b'\x00\x01', b'\x00\x02']
    )
    
    serialized = obj_construct.build(obj)
    
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        deserialized = obj_construct.parse(serialized)
    
    assert deserialized["num_levels"] == 2
    assert deserialized["versions"][0] == (1, 0, 0, 0)
    assert deserialized["versions"][1] == (2, 0, 0, 5)


@pytest.mark.parametrize("num_levels", [1, 2, 3, 4, 5])
def test_lvobject_various_inheritance_depths(num_levels):
    """
    Test LVObject with various inheritance depths.
    
    Per LabVIEW spec: Only the MOST DERIVED class name is serialized.
    """
    class_name = f"Level{num_levels-1}.lvlib:Class{num_levels-1}.lvclass"
    versions = [(1, 0, 0, 0)] * num_levels
    cluster_data = [b''] * num_levels
    
    obj_construct = LVObject()
    obj = create_lvobject(
        class_name=class_name,
        num_levels=num_levels,
        versions=versions,
        cluster_data=cluster_data
    )
    
    serialized = obj_construct.build(obj)
    
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        deserialized = obj_construct.parse(serialized)
    
    assert deserialized["num_levels"] == num_levels
    assert len(deserialized["versions"]) == num_levels
    assert len(deserialized["cluster_data"]) == num_levels


# ============================================================================
# Declarative Object Tests
# ============================================================================

def test_version_struct_declarative():
    """Test that VersionStruct is used declaratively in LVObject."""
    from src.objects import VersionStruct
    
    # Test building a version
    version_data = {"major": 1, "minor": 2, "patch": 3, "build": 4}
    result = VersionStruct.build(version_data)
    
    # Each field is Int16ub, so 8 bytes total
    assert len(result) == 8
    assert result.hex() == "0001000200030004"
    
    # Test parsing
    parsed = VersionStruct.parse(result)
    assert parsed.major == 1
    assert parsed.minor == 2
    assert parsed.patch == 3
    assert parsed.build == 4


def test_cluster_data_struct_declarative():
    """Test that ClusterDataStruct is used declaratively in LVObject."""
    from src.objects import ClusterDataStruct
    
    # Test building cluster data
    cluster_data = {"size": 5, "data": b"Hello"}
    result = ClusterDataStruct.build(cluster_data)
    
    # size (4 bytes) + data (5 bytes)
    assert len(result) == 9
    assert result[:4].hex() == "00000005"  # size = 5
    assert result[4:] == b"Hello"
    
    # Test parsing
    parsed = ClusterDataStruct.parse(result)
    assert parsed.size == 5
    assert parsed.data == b"Hello"


def test_lvobject_declarative_backward_compatibility():
    """Test that declarative LVObject maintains backward compatibility."""
    # Create an object with known binary format and verify it parses correctly
    obj_construct = LVObject()
    
    # Build an object with unique class name to avoid registry collisions
    original = create_lvobject(
        class_name="BackwardCompatLib.lvlib:BackwardCompatClass.lvclass",
        num_levels=1,
        versions=[(1, 0, 0, 0)],
        cluster_data=[b'\x00\x00\x00\x01']  # I32(1)
    )
    
    serialized = obj_construct.build(original)
    
    # Verify it starts with NumLevels = 1
    assert serialized[:4].hex() == "00000001"
    
    # Parse it back - will return dict since class is not in registry
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        deserialized = obj_construct.parse(serialized)
    
    # Verify structure is preserved (returns dict for unregistered class)
    assert isinstance(deserialized, dict)
    assert deserialized["num_levels"] == 1
    assert deserialized["versions"][0] == (1, 0, 0, 0)
    assert deserialized["cluster_data"][0] == b'\x00\x00\x00\x01'
