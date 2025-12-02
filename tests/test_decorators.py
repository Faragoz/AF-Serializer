"""
Unit tests for construct_impl decorators.

These tests validate that the @lvclass decorator properly marks classes
and enables automatic serialization.
"""

import pytest
import warnings

from af_serializer import (
    lvfield, is_lvclass, lvflatten, lvunflatten,
    LVObject, LVI32, LVString, LVU16, lvclass,
    get_lvclass_by_name, _LVCLASS_REGISTRY
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
    assert MyClass.__lv_version__ == (1, 0, 0, 1)


def test_lvclass_registers_in_registry():
    """Test that @lvclass registers the class in the global registry."""
    @lvclass(library="TestLib", class_name="RegistryTestClass")
    class RegistryTestClass:
        pass
    
    full_name = "TestLib.lvlib:RegistryTestClass.lvclass"
    assert full_name in _LVCLASS_REGISTRY
    assert get_lvclass_by_name(full_name) is RegistryTestClass


def test_lvclass_registry_without_library():
    """Test that @lvclass without library registers correctly."""
    @lvclass(class_name="NoLibClass")
    class NoLibClass:
        pass
    
    full_name = "NoLibClass.lvclass"
    assert get_lvclass_by_name(full_name) is NoLibClass


# ============================================================================
# Inheritance Tests
# ============================================================================

def test_lvclass_with_multi_level_inheritance():
    """Test @lvclass with multiple inheritance levels."""
    # Create a proper inheritance chain
    @lvclass(library="Actor Framework", class_name="InheritanceMessage")
    class InheritanceMessage:
        pass
    
    @lvclass(library="Serializable Message", class_name="InheritanceSerializableMsg", version=(1, 0, 0, 7))
    class InheritanceSerializableMsg(InheritanceMessage):
        pass
    
    @lvclass(library="Commander", class_name="InheritanceEchoMsg")
    class InheritanceEchoMsg(InheritanceSerializableMsg):
        message: str
        status: LVI32
    
    obj = InheritanceEchoMsg()
    obj.message = "Hello World"
    obj.status = 0
    
    # Serialize and deserialize
    data = lvflatten(obj)
    
    # Auto-detected 3 levels from inheritance chain
    assert data[:4].hex() == "00000003"  # NumLevels = 3


# ============================================================================
# Serialization Integration Tests
# ============================================================================

def test_lvflatten_with_lvclass_decorated_object():
    """Test that lvflatten() works with @lvclass decorated objects."""
    @lvclass(library="TestLib", class_name="SimpleClass1")
    class SimpleClass1:
        count: LVI32
    
    obj = SimpleClass1()
    obj.count = 42
    data = lvflatten(obj)
    
    assert isinstance(data, bytes)
    # Should start with NumLevels = 1
    assert data[:4].hex() == "00000001"


def test_lvclass_roundtrip():
    """Test serialize → deserialize roundtrip with @lvclass."""
    @lvclass(library="TestLib", class_name="RoundtripClass")
    class RoundtripClass:
        message: str
        value: LVI32
    
    obj = RoundtripClass()
    obj.message = "Test Message"
    obj.value = 123
    
    serialized = lvflatten(obj)
    
    # Deserialize - should automatically return RoundtripClass instance
    deserialized = lvunflatten(serialized)
    
    assert isinstance(deserialized, RoundtripClass)
    assert deserialized.message == "Test Message"
    assert deserialized.value == 123


def test_lvclass_roundtrip_with_inheritance():
    """Test serialize → deserialize roundtrip with 3-level inheritance."""
    @lvclass(library="Base", class_name="BaseMsg")
    class BaseMsg:
        pass
    
    @lvclass(library="Middle", class_name="MiddleMsg", version=(1, 0, 0, 7))
    class MiddleMsg(BaseMsg):
        pass
    
    @lvclass(library="Derived", class_name="DerivedMsg")
    class DerivedMsg(MiddleMsg):
        message: str
        code: LVU16
    
    obj = DerivedMsg()
    obj.message = "Hello World"
    obj.code = 42
    
    serialized = lvflatten(obj)
    deserialized = lvunflatten(serialized)
    
    assert isinstance(deserialized, DerivedMsg)
    assert deserialized.message == "Hello World"
    assert deserialized.code == 42


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
    @lvclass(library="TestLib", class_name="MultiFieldClass1")
    class MultiFieldClass1:
        name: str
        count: LVI32
    
    obj = MultiFieldClass1()
    obj.name = "Test"
    obj.count = 100
    data = lvflatten(obj)
    
    assert isinstance(data, bytes)
    assert len(data) > 0


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_lvclass_empty_object():
    """Test @lvclass with object that has no fields."""
    @lvclass(library="TestLib", class_name="EmptyClass1")
    class EmptyClass1:
        pass
    
    obj = EmptyClass1()
    data = lvflatten(obj)
    
    # Should still serialize as a valid LVObject
    assert isinstance(data, bytes)
    assert data[:4].hex() == "00000001"  # NumLevels = 1


def test_lvflatten_integration():
    """Test that lvflatten automatically handles @lvclass objects."""
    @lvclass(library="Commander", class_name="IntegrationEchoMsg")
    class IntegrationEchoMsg:
        message: str
        status: LVI32
    
    msg = IntegrationEchoMsg()
    msg.message = "Hello, LabVIEW!"
    msg.status = 0
    
    # Should serialize automatically without type_hint
    data = lvflatten(msg)
    
    assert isinstance(data, bytes)
    # Verify it's a proper LVObject (single level = 1)
    assert data[:4].hex() == "00000001"  # NumLevels = 1


def test_lvunflatten_class_not_in_registry():
    """Test lvunflatten with class not in registry returns dict with warning."""
    # Create raw LVObject bytes for a class not in registry
    from af_serializer import create_lvobject, LVObject
    
    obj_data = create_lvobject(
        class_name="NonExistent.lvlib:NonExistent.lvclass",
        num_levels=1,
        versions=[(1, 0, 0, 0)],
        cluster_data=[b'']
    )
    
    obj_construct = LVObject()
    serialized = obj_construct.build(obj_data)
    
    # Should warn and return dict
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = lvunflatten(serialized)
        
        # Check that a warning was issued
        assert len(w) >= 1
        assert "not found in registry" in str(w[-1].message)
    
    # Result should be a dict
    assert isinstance(result, dict)
    assert result["class_name"] == "NonExistent.lvlib:NonExistent.lvclass"
