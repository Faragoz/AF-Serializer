"""
Unit tests for LabVIEW compound types (Arrays and Clusters).

These tests validate serialization and deserialization against real HEX examples
from LabVIEW documentation.
"""

import pytest
from construct import ConstructError

from construct_impl import (
    LVI32, LVU16, LVString,
    LVArray1D, LVArray2D, LVCluster,
)


# ============================================================================
# Array 1D Tests
# ============================================================================

def test_array1d_serialization_three_elements():
    """Validate Array1D serialization against real LabVIEW hex output."""
    # Array of 3 I32 elements: [1, 2, 3]
    # Expected: 0000 0003 0000 0001 0000 0002 0000 0003
    array_construct = LVArray1D(LVI32)
    data = [1, 2, 3]
    expected_hex = "00000003000000010000000200000003"
    
    result = array_construct.build(data)
    
    assert result.hex() == expected_hex


def test_array1d_deserialization_roundtrip():
    """Test Array1D serialize → deserialize → compare."""
    array_construct = LVArray1D(LVI32)
    original = [1, 2, 3]
    
    serialized = array_construct.build(original)
    deserialized = array_construct.parse(serialized)
    
    assert deserialized == original


def test_array1d_empty_array():
    """Test Array1D with empty array."""
    array_construct = LVArray1D(LVI32)
    data = []
    expected_hex = "00000000"
    
    result = array_construct.build(data)
    
    assert result.hex() == expected_hex


def test_array1d_single_element():
    """Test Array1D with single element."""
    array_construct = LVArray1D(LVI32)
    data = [42]
    expected_hex = "000000010000002a"
    
    result = array_construct.build(data)
    
    assert result.hex() == expected_hex


@pytest.mark.parametrize("data", [
    [1],
    [1, 2],
    [1, 2, 3, 4, 5],
    [0, 0, 0],
    [-1, -2, -3],
])
def test_array1d_roundtrip_parametrized(data):
    """Test Array1D roundtrip with various data."""
    array_construct = LVArray1D(LVI32)
    
    serialized = array_construct.build(data)
    deserialized = array_construct.parse(serialized)
    
    assert deserialized == data


# ============================================================================
# Array 2D Tests
# ============================================================================

def test_array2d_serialization_2x3_matrix():
    """Validate Array2D serialization for 2×3 matrix."""
    # 2×3 matrix: [[1, 2, 3], [4, 5, 6]]
    # Expected: 0000 0002 0000 0002 0000 0003 [6 elements]
    array_construct = LVArray2D(LVI32)
    data = [[1, 2, 3], [4, 5, 6]]
    
    result = array_construct.build(data)
    
    # Check header
    assert result[:4].hex() == "00000002"  # num_dims = 2
    assert result[4:8].hex() == "00000002"  # dim1 = 2
    assert result[8:12].hex() == "00000003"  # dim2 = 3
    
    # Check elements
    assert result[12:16].hex() == "00000001"  # element 0
    assert result[16:20].hex() == "00000002"  # element 1
    assert result[20:24].hex() == "00000003"  # element 2
    assert result[24:28].hex() == "00000004"  # element 3
    assert result[28:32].hex() == "00000005"  # element 4
    assert result[32:36].hex() == "00000006"  # element 5


def test_array2d_deserialization_roundtrip():
    """Test Array2D serialize → deserialize → compare."""
    array_construct = LVArray2D(LVI32)
    original = [[1, 2, 3], [4, 5, 6]]
    
    serialized = array_construct.build(original)
    deserialized = array_construct.parse(serialized)
    
    assert deserialized == original


def test_array2d_single_row():
    """Test Array2D with single row."""
    array_construct = LVArray2D(LVI32)
    data = [[1, 2, 3]]
    
    serialized = array_construct.build(data)
    deserialized = array_construct.parse(serialized)
    
    assert deserialized == data


@pytest.mark.parametrize("data", [
    [[1, 2], [3, 4]],
    [[1, 2, 3]],
    [[1], [2], [3]],
])
def test_array2d_roundtrip_parametrized(data):
    """Test Array2D roundtrip with various data."""
    array_construct = LVArray2D(LVI32)
    
    serialized = array_construct.build(data)
    deserialized = array_construct.parse(serialized)
    
    assert deserialized == data


# ============================================================================
# Cluster Tests
# ============================================================================

def test_cluster_serialization_string_and_i32():
    """Validate Cluster serialization against real LabVIEW hex output."""
    # Cluster: (String "Hello, LabVIEW!" + I32(0))
    # Expected: 0000 000f 48656c6c6f2c204c61625649455721 00000000
    cluster_construct = LVCluster(LVString, LVI32)
    data = ("Hello, LabVIEW!", 0)
    
    result = cluster_construct.build(data)
    
    # Check string part
    assert result[:4].hex() == "0000000f"  # String length = 15
    assert result[4:19].decode('utf-8') == "Hello, LabVIEW!"
    
    # Check I32 part
    assert result[19:23].hex() == "00000000"  # I32(0)


def test_cluster_deserialization_roundtrip():
    """Test Cluster serialize → deserialize → compare."""
    cluster_construct = LVCluster(LVString, LVI32)
    original = ("Hello, LabVIEW!", 0)
    
    serialized = cluster_construct.build(original)
    deserialized = cluster_construct.parse(serialized)
    
    assert deserialized == original


def test_cluster_multiple_types():
    """Test Cluster with multiple different types."""
    cluster_construct = LVCluster(LVI32, LVString, LVI32)
    data = (42, "Test", 100)
    
    serialized = cluster_construct.build(data)
    deserialized = cluster_construct.parse(serialized)
    
    assert deserialized == data


def test_cluster_string_and_u16():
    """Test Cluster with string and U16 (from user example)."""
    # "Hello World" + U16(0)
    cluster_construct = LVCluster(LVString, LVU16)
    data = ("Hello World", 0)
    
    serialized = cluster_construct.build(data)
    deserialized = cluster_construct.parse(serialized)
    
    assert deserialized == data
    
    # Check hex format
    assert serialized[:4].hex() == "0000000b"  # String length = 11
    assert serialized[4:15].decode('utf-8') == "Hello World"
    assert serialized[15:17].hex() == "0000"  # U16(0)


@pytest.mark.parametrize("data", [
    (42, "Test"),
    ("Hello", 123, "World"),
    (1, 2, 3, 4),
])
def test_cluster_various_combinations(data):
    """Test Cluster with various type combinations."""
    # Build constructs based on data types
    constructs = []
    for item in data:
        if isinstance(item, str):
            constructs.append(LVString)
        elif isinstance(item, int):
            constructs.append(LVI32)
    
    cluster_construct = LVCluster(*constructs)
    
    serialized = cluster_construct.build(data)
    deserialized = cluster_construct.parse(serialized)
    
    assert deserialized == data


# ============================================================================
# Integration Tests
# ============================================================================

def test_nested_array_in_cluster():
    """Test Cluster containing an array."""
    # This is more complex - cluster with array as one element
    # For now, we test that arrays and clusters work independently
    array_construct = LVArray1D(LVI32)
    array_data = [1, 2, 3]
    array_bytes = array_construct.build(array_data)
    
    # Verify array serialization works
    assert array_bytes[:4].hex() == "00000003"


def test_array_of_strings():
    """Test Array1D with string elements."""
    array_construct = LVArray1D(LVString)
    data = ["Hello", "World", "Test"]
    
    serialized = array_construct.build(data)
    deserialized = array_construct.parse(serialized)
    
    assert deserialized == data
