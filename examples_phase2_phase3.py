#!/usr/bin/env python3
"""
Examples demonstrating Phase 2 and Phase 3 of Construct-based LabVIEW serialization.

This script shows how to use compound types (Arrays, Clusters) and Objects.
"""

from src import (
    LVI32, LVU16, LVString,
    LVArray1D, LVArray2D, LVCluster,
    LVObject, create_empty_lvobject, create_lvobject,
)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def main():
    print("\n🚀 Phase 2 & 3: Compound Types and Objects")
    
    # ========================================================================
    # Phase 2: Array 1D
    # ========================================================================
    print_section("Array 1D - Homogeneous Collections")
    
    # Array of I32
    array_construct = LVArray1D(LVI32)
    data = [1, 2, 3]
    serialized = array_construct.build(data)
    print(f"Array 1D [1, 2, 3]:")
    print(f"  HEX: {serialized.hex()}")
    print(f"  Format: [count] + [elements]")
    print(f"  Count: {serialized[:4].hex()} (3 elements)")
    print(f"  Elements: {serialized[4:].hex()}")
    
    # Deserialize
    deserialized = array_construct.parse(serialized)
    print(f"  Deserialized: {deserialized} ✓")
    
    # Array of strings
    print("\nArray 1D of strings:")
    string_array = LVArray1D(LVString)
    data = ["Hello", "World", "Test"]
    serialized = string_array.build(data)
    print(f"  Data: {data}")
    print(f"  HEX (first 20 bytes): {serialized[:20].hex()}...")
    deserialized = string_array.parse(serialized)
    print(f"  Deserialized: {deserialized} ✓")
    
    # ========================================================================
    # Phase 2: Array 2D
    # ========================================================================
    print_section("Array 2D - Multi-dimensional Arrays")
    
    # 2×3 matrix
    array2d_construct = LVArray2D(LVI32)
    data = [[1, 2, 3], [4, 5, 6]]
    serialized = array2d_construct.build(data)
    print(f"Array 2D (2×3 matrix):")
    print(f"  Data: {data}")
    print(f"  HEX: {serialized.hex()}")
    print(f"  Format: [num_dims][dim1_size][dim2_size] + [elements]")
    print(f"  Num dims: {serialized[:4].hex()} (2 dimensions)")
    print(f"  Dim 1: {serialized[4:8].hex()} (2 rows)")
    print(f"  Dim 2: {serialized[8:12].hex()} (3 columns)")
    
    # Deserialize
    deserialized = array2d_construct.parse(serialized)
    print(f"  Deserialized: {deserialized} ✓")
    
    # ========================================================================
    # Phase 2: Cluster
    # ========================================================================
    print_section("Cluster - Heterogeneous Collections")
    
    # String + I32 cluster
    cluster_construct = LVCluster(LVString, LVI32)
    data = ("Hello, LabVIEW!", 0)
    serialized = cluster_construct.build(data)
    print(f"Cluster (String + I32):")
    print(f"  Data: {data}")
    print(f"  HEX: {serialized.hex()}")
    print(f"  Format: Direct concatenation (NO header)")
    print(f"  String length: {serialized[:4].hex()}")
    print(f"  String: {serialized[4:19].decode('utf-8')}")
    print(f"  I32: {serialized[19:23].hex()}")
    
    # Deserialize
    deserialized = cluster_construct.parse(serialized)
    print(f"  Deserialized: {deserialized} ✓")
    
    # String + U16 cluster (from user example)
    print("\nCluster (String + U16) - 'Hello World' + 0:")
    cluster_construct = LVCluster(LVString, LVU16)
    data = ("Hello World", 0)
    serialized = cluster_construct.build(data)
    print(f"  Data: {data}")
    print(f"  HEX: {serialized.hex()}")
    deserialized = cluster_construct.parse(serialized)
    print(f"  Deserialized: {deserialized} ✓")
    
    # Multiple types
    print("\nCluster with multiple types (I32 + String + I32):")
    cluster_construct = LVCluster(LVI32, LVString, LVI32)
    data = (42, "Test", 100)
    serialized = cluster_construct.build(data)
    print(f"  Data: {data}")
    print(f"  HEX (first 30 bytes): {serialized[:30].hex()}...")
    deserialized = cluster_construct.parse(serialized)
    print(f"  Deserialized: {deserialized} ✓")
    
    # ========================================================================
    # Phase 3: Empty LVObject
    # ========================================================================
    print_section("Phase 3: LVObject - Empty Object")
    
    obj_construct = LVObject()
    obj = create_empty_lvobject()
    serialized = obj_construct.build(obj)
    print(f"Empty LVObject:")
    print(f"  HEX: {serialized.hex()}")
    print(f"  Format: NumLevels = 0")
    
    deserialized = obj_construct.parse(serialized)
    print(f"  Deserialized NumLevels: {deserialized['num_levels']} ✓")
    
    # ========================================================================
    # Phase 3: Single-Level Object
    # ========================================================================
    print_section("Phase 3: LVObject - Single Level (Actor)")
    
    obj_construct = LVObject()
    obj = create_lvobject(
        class_names=["Actor Framework.lvlib:Actor.lvclass"],
        versions=[(1, 0, 0, 0)],  # Use tuple format
        cluster_data=[b'\x00\x00\x00\x00\x00\x00\x00\x00']
    )
    serialized = obj_construct.build(obj)
    print(f"Actor Object (single level):")
    print(f"  Class: {obj['class_names'][0]}")
    print(f"  Version: {obj['versions'][0]} (1.0.0.0)")
    print(f"  HEX (first 40 bytes): {serialized[:40].hex()}...")
    print(f"  NumLevels: {serialized[:4].hex()} (1 level)")
    
    deserialized = obj_construct.parse(serialized)
    print(f"  Deserialized:")
    print(f"    NumLevels: {deserialized['num_levels']}")
    print(f"    Class: {deserialized['class_names'][0]}")
    print(f"  ✓")
    
    # ========================================================================
    # Phase 3: Three-Level Inheritance
    # ========================================================================
    print_section("Phase 3: LVObject - Three-Level Inheritance")
    
    print("Example from user comment:")
    print("  Inheritance chain:")
    print("    1. Actor Framework.lvlib:Message.lvclass")
    print("    2. Serializable Message.lvlib:Serializable Msg.lvclass")
    print("    3. Commander.lvlib:echo general Msg.lvclass")
    
    # Create cluster for level 3 data
    cluster_construct = LVCluster(LVString, LVU16)
    cluster_data = ("Hello World", 0)
    cluster_bytes = cluster_construct.build(cluster_data)
    
    obj_construct = LVObject()
    obj = create_lvobject(
        class_names=[
            "Actor Framework.lvlib:Message.lvclass",
            "Serializable Message.lvlib:Serializable Msg.lvclass",
            "Commander.lvlib:echo general Msg.lvclass"
        ],
        versions=[(1, 0, 0, 0), (1, 0, 0, 7), (1, 0, 0, 0)],  # Use tuple format
        cluster_data=[
            b'\x00\x00\x00\x00\x00\x00\x00\x00',  # Empty for level 1
            b'\x00\x00\x00\x00\x00\x00\x00\x00',  # Empty for level 2
            cluster_bytes  # "Hello World" + U16(0) for level 3
        ]
    )
    
    serialized = obj_construct.build(obj)
    print(f"\nThree-level object:")
    print(f"  NumLevels: {serialized[:4].hex()} (3 levels)")
    print(f"  Total size: {len(serialized)} bytes")
    print(f"  HEX (first 60 bytes): {serialized[:60].hex()}...")
    
    print(f"\n  Versions:")
    print(f"    Level 1: {obj['versions'][0]} (1.0.0.0)")
    print(f"    Level 2: {obj['versions'][1]} (1.0.0.7)")
    print(f"    Level 3: {obj['versions'][2]} (1.0.0.0)")
    
    deserialized = obj_construct.parse(serialized)
    print(f"\n  Deserialized:")
    print(f"    NumLevels: {deserialized['num_levels']}")
    print(f"    Classes: {len(deserialized['class_names'])}")
    for i, cn in enumerate(deserialized['class_names'], 1):
        print(f"      Level {i}: {cn}")
    print(f"  ✓")
    
    # ========================================================================
    # Integration: Array of Clusters
    # ========================================================================
    print_section("Integration: Complex Nested Structures")
    
    # Array of clusters isn't directly supported, but we can serialize
    # individual clusters and combine them
    print("Array of 2 clusters (each: String + I32):")
    cluster_construct = LVCluster(LVString, LVI32)
    clusters = [
        ("First", 1),
        ("Second", 2)
    ]
    
    # Serialize each cluster
    serialized_clusters = [cluster_construct.build(c) for c in clusters]
    print(f"  Cluster 1: {clusters[0]} -> {serialized_clusters[0].hex()[:40]}...")
    print(f"  Cluster 2: {clusters[1]} -> {serialized_clusters[1].hex()[:40]}...")
    
    # Could be combined with Array1D wrapper if needed
    print(f"  Individual clusters can be used in arrays or objects ✓")
    
    print("\n" + "=" * 60)
    print("  All Phase 2 & 3 examples completed successfully! ✨")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
