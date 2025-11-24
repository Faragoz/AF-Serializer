"""
Unit tests for construct_impl decorators.

These tests validate that the @lvclass decorator properly marks classes
and enables automatic serialization.
"""

import pytest

from src import (
    lvfield, is_lvclass, lvflatten, lvunflatten,
    LVObject, LVI32, LVString, LVU16, lvclass,
)


# ============================================================================
# Decorator Basic Tests
# ============================================================================

def test_lvclass_decorator_sets_attributes():
    """Test that @lvclass decorator properly sets LabVIEW attributes."""
    @lvclass(library="TestLib", class_name="TestClass", version=(1, 2, 3, 4))
    class TestClass:
        pass
    
    assert hasattr(TestClass, '__lv_library__')
    assert TestClass.__lv_library__ == "TestLib"
    assert TestClass.__lv_class_name__ == "TestClass"
    assert TestClass.__lv_version__ == (1, 2, 3, 4)
    assert TestClass.__is_lv_class__ is True


def test_lvclass_decorator_defaults():
    """Test @lvclass with default values."""
    @lvclass()
    class MyClass:
        pass
    
    assert MyClass.__lv_library__ == ""  # Default is empty string, not class name
    assert MyClass.__lv_class_name__ == "MyClass"  # Class name defaults to Python class name
    assert MyClass.__lv_version__ == (1, 0, 0, 0)


def test_lvclass_creates_to_lvobject_method():
    """Test that @lvclass adds to_lvobject() method."""
    @lvclass(library="TestLib", class_name="TestClass")
    class TestClass:
        def __init__(self):
            self.message = "Hello"
            self.count = 42
    
    obj = TestClass()
    lvobj_dict = obj.to_lvobject()
    
    assert isinstance(lvobj_dict, dict)
    assert lvobj_dict["num_levels"] == 1
    assert "TestLib.lvlib:TestClass.lvclass" in lvobj_dict["class_name"]


def test_lvclass_creates_to_bytes_method():
    """Test that @lvclass adds to_bytes() method."""
    @lvclass(library="TestLib", class_name="TestClass")
    class TestClass:
        def __init__(self):
            self.value = 100
    
    obj = TestClass()
    data = obj.to_bytes()
    
    assert isinstance(data, bytes)
    assert len(data) > 0


# ============================================================================
# Inheritance Tests
# ============================================================================

def test_lvclass_with_multi_level_inheritance():
    """Test @lvclass with multiple inheritance levels."""
    # Create a proper inheritance chain
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
    
    obj = EchoGeneralMsg()
    lvobj_dict = obj.to_lvobject()
    
    # Auto-detected 3 levels from inheritance chain
    assert lvobj_dict["num_levels"] == 3
    assert "Commander.lvlib:echo general Msg.lvclass" in lvobj_dict["class_name"]
    assert len(lvobj_dict["versions"]) == 3
    assert len(lvobj_dict["cluster_data"]) == 3


# ============================================================================
# Serialization Integration Tests
# ============================================================================

def test_lvflatten_with_lvclass_decorated_object():
    """Test that lvflatten() works with @lvclass decorated objects."""
    @lvclass(library="TestLib", class_name="SimpleClass")
    class SimpleClass:
        def __init__(self):
            self.count = 42
    
    obj = SimpleClass()
    data = lvflatten(obj)
    
    assert isinstance(data, bytes)
    # Should start with NumLevels = 1
    assert data[:4].hex() == "00000001"


def test_lvclass_roundtrip():
    """Test serialize → deserialize roundtrip with @lvclass."""
    @lvclass(library="TestLib", class_name="TestClass")
    class TestClass:
        def __init__(self):
            self.message = "Test Message"
            self.value = 123
    
    obj = TestClass()
    serialized = obj.to_bytes()
    
    # Deserialize
    obj_construct = LVObject()
    deserialized = obj_construct.parse(serialized)
    
    assert deserialized["num_levels"] == 1
    assert "TestLib.lvlib:TestClass.lvclass" in deserialized["class_name"]


# ============================================================================
# is_lvclass Helper Tests
# ============================================================================

def test_is_lvclass_with_decorated_class():
    """Test is_lvclass() returns True for decorated classes."""
    @lvclass(library="Test")
    class TestClass:
        pass
    
    obj = TestClass()
    assert is_lvclass(obj) is True


def test_is_lvclass_with_regular_class():
    """Test is_lvclass() returns False for regular classes."""
    class RegularClass:
        pass
    
    obj = RegularClass()
    assert is_lvclass(obj) is False


# ============================================================================
# Field Types Tests
# ============================================================================

def test_lvclass_with_typed_fields():
    """Test @lvclass with various field types."""
    @lvclass(library="TestLib", class_name="MultiFieldClass")
    class MultiFieldClass:
        def __init__(self):
            self.name = "Test"
            self.count = 100
            self.active = True
            self.value = 3.14
    
    obj = MultiFieldClass()
    data = obj.to_bytes()
    
    assert isinstance(data, bytes)
    assert len(data) > 0


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_lvclass_empty_object():
    """Test @lvclass with object that has no fields."""
    @lvclass(library="TestLib", class_name="EmptyClass")
    class EmptyClass:
        pass
    
    obj = EmptyClass()
    data = obj.to_bytes()
    
    # Should still serialize as a valid LVObject
    assert isinstance(data, bytes)
    assert data[:4].hex() == "00000001"  # NumLevels = 1


def test_lvflatten_integration():
    """Test that lvflatten automatically handles @lvclass objects."""
    @lvclass(library="Commander", class_name="echo general Msg")
    class EchoMsg:
        def __init__(self):
            self.message = "Hello, LabVIEW!"
            self.status = 0
    
    msg = EchoMsg()
    
    # Should serialize automatically without type_hint
    data = lvflatten(msg)
    
    assert isinstance(data, bytes)
    # Verify it's a proper LVObject (single level = 1)
    assert data[:4].hex() == "00000001"  # NumLevels = 1
