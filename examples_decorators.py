#!/usr/bin/env python3
"""
Examples demonstrating the @lvclass decorator for easy LabVIEW Object serialization.

This script shows how to use decorators to convert Python classes to LabVIEW Objects.
"""

from src import (
    lvclass, lvflatten, lvunflatten, LVObject,
)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def main():
    print("\n🚀 @lvclass Decorator Examples")
    
    # ========================================================================
    # Basic Usage - Single Level Object
    # ========================================================================
    print_section("Basic Usage - Single Level Object")
    
    @lvclass(library="MyLib", class_name="SimpleClass")
    class SimpleClass:
        def __init__(self):
            self.message = "Hello, LabVIEW!"
            self.count = 42
            self.active = True
    
    # Create an instance
    obj = SimpleClass()
    
    print(f"Python object:")
    print(f"  message: {obj.message}")
    print(f"  count: {obj.count}")
    print(f"  active: {obj.active}")
    
    # Automatic serialization using lvflatten
    data = lvflatten(obj)
    print(f"\nSerialized with lvflatten():")
    print(f"  Size: {len(data)} bytes")
    print(f"  HEX (first 60): {data[:60].hex()}")
    print(f"  NumLevels: {data[:4].hex()} (1 level)")
    
    # Alternative: use to_bytes() method
    data2 = obj.to_bytes()
    print(f"\nSerialized with to_bytes():")
    print(f"  Same result: {data == data2}")
    
    # ========================================================================
    # Multi-Level Inheritance
    # ========================================================================
    print_section("Multi-Level Inheritance (3 levels)")
    
    print("Example: Message → Serializable Msg → echo general Msg")
    
    # Create proper inheritance chain for 3 levels
    @lvclass(library="Actor Framework", class_name="Message")
    class Message:
        pass
    
    @lvclass(library="Serializable Message", class_name="Serializable Msg", version=(1, 0, 0, 7))
    class SerializableMsg(Message):
        pass
    
    @lvclass(library="Commander", class_name="echo general Msg")
    class EchoGeneralMsg(SerializableMsg):
        def __init__(self):
            self.message = "Hello World"
            self.status = 0
    
    msg = EchoGeneralMsg()
    msg.message = "Hello, LabVIEW from Python!"
    
    print(f"\nPython object:")
    print(f"  message: {msg.message}")
    print(f"  status: {msg.status}")
    
    # Serialize
    data = lvflatten(msg)
    print(f"\nSerialized:")
    print(f"  Size: {len(data)} bytes")
    print(f"  HEX (first 80): {data[:80].hex()}")
    print(f"  NumLevels: {int.from_bytes(data[:4], 'big')} (3 levels)")
    
    # Deserialize to verify
    obj_construct = LVObject()
    deserialized = obj_construct.parse(data)
    print(f"\nDeserialized structure:")
    print(f"  num_levels: {deserialized['num_levels']}")
    print(f"  class_name: {deserialized['class_name']}")
    print(f"  versions: {len(deserialized['versions'])} entries")
    print(f"  cluster_data: {len(deserialized['cluster_data'])} sections")
    
    # ========================================================================
    # Various Data Types
    # ========================================================================
    print_section("Various Data Types")
    
    @lvclass(library="DataTypes", class_name="MixedData")
    class MixedData:
        def __init__(self):
            self.name = "Test"
            self.value = 123
            self.ratio = 3.14159
            self.enabled = True
    
    data_obj = MixedData()
    print(f"Object with mixed types:")
    print(f"  name (str): {data_obj.name}")
    print(f"  value (int): {data_obj.value}")
    print(f"  ratio (float): {data_obj.ratio}")
    print(f"  enabled (bool): {data_obj.enabled}")
    
    data = lvflatten(data_obj)
    print(f"\nSerialized: {len(data)} bytes")
    print(f"  All types handled automatically!")
    
    # ========================================================================
    # Metadata Access
    # ========================================================================
    print_section("Accessing LabVIEW Metadata")
    
    @lvclass(library="Actors", class_name="CustomActor", version=(2, 1, 0, 5))
    class CustomActor:
        pass
    
    print(f"Class metadata:")
    print(f"  Library: {CustomActor.__lv_library__}")
    print(f"  Class name: {CustomActor.__lv_class_name__}")
    print(f"  Version: {CustomActor.__lv_version__}")
    print(f"  Is LV class: {CustomActor.__is_lv_class__}")
    print(f"  Note: num_levels is calculated dynamically based on inheritance")
    
    # ========================================================================
    # to_lvobject() Method
    # ========================================================================
    print_section("Using to_lvobject() Method")
    
    @lvclass(library="Test", class_name="TestClass")
    class TestClass:
        def __init__(self):
            self.value = 999
    
    test_obj = TestClass()
    lvobj_dict = test_obj.to_lvobject()
    
    print(f"LVObject dictionary:")
    print(f"  num_levels: {lvobj_dict['num_levels']}")
    print(f"  class_name: {lvobj_dict['class_name']}")
    print(f"  versions: {lvobj_dict['versions']}")
    print(f"  cluster_data: {len(lvobj_dict['cluster_data'])} sections")
    
    # ========================================================================
    # Comparison with Manual Creation
    # ========================================================================
    print_section("Decorator vs Manual Creation")
    
    print("With decorator:")
    print("```python")
    print("@lvclass(library='MyLib', class_name='MyClass')")
    print("class MyClass:")
    print("    def __init__(self):")
    print("        self.data = 42")
    print("")
    print("obj = MyClass()")
    print("data = lvflatten(obj)  # Automatic!")
    print("```")
    
    print("\nWithout decorator (manual):")
    print("```python")
    print("from src.construct_impl import create_lvobject, LVObject")
    print("")
    print("lvobj = create_lvobject(")
    print("    class_name='MyLib.lvlib:MyClass.lvclass',")
    print("    num_levels=1,")
    print("    versions=[0x01000000],")
    print("    cluster_data=[...]  # Manually serialize")
    print(")")
    print("obj_construct = LVObject()")
    print("data = obj_construct.build(lvobj)")
    print("```")
    
    print("\n✅ Decorator approach is much simpler!")
    
    print("\n" + "=" * 60)
    print("  All decorator examples completed successfully! ✨")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
