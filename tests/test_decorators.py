"""
Tests for the @lvclass decorator and integration with lvflatten
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from decorators import lvclass


def test_lvclass_decorator_basic():
    """Test that @lvclass decorator properly sets attributes"""
    
    @lvclass(library="TestLib", class_name="TestClass", version=(1, 2, 3, 4))
    class TestObj:
        field1: int = 0
        field2: str = ""
    
    assert hasattr(TestObj, '__lv_library__')
    assert hasattr(TestObj, '__lv_class_name__')
    assert hasattr(TestObj, '__lv_version__')
    assert hasattr(TestObj, '__is_lv_class__')
    
    assert TestObj.__lv_library__ == "TestLib"
    assert TestObj.__lv_class_name__ == "TestClass"
    assert TestObj.__lv_version__ == (1, 2, 3, 4)
    assert TestObj.__is_lv_class__ == True


def test_lvclass_decorator_defaults():
    """Test @lvclass with default values"""
    
    @lvclass()
    class MyClass:
        value: int = 0
    
    assert MyClass.__lv_library__ == ""
    assert MyClass.__lv_class_name__ == "MyClass"
    assert MyClass.__lv_version__ == (1, 0, 0, 0)


def test_lvclass_instantiation():
    """Test that decorated classes can still be instantiated"""
    
    @lvclass(library="Commander", class_name="echo general Msg")
    class EchoMsg:
        message: str = "default"
        status: int = 0
    
    msg = EchoMsg()
    assert msg.message == "default"
    assert msg.status == 0
    
    msg.message = "Hello, LabVIEW!"
    msg.status = 1
    assert msg.message == "Hello, LabVIEW!"
    assert msg.status == 1


def test_lvclass_inheritance():
    """Test that @lvclass works with inheritance"""
    
    @lvclass(library="Base", class_name="BaseClass")
    class BaseClass:
        base_field: int = 0
    
    @lvclass(library="Derived", class_name="DerivedClass")
    class DerivedClass(BaseClass):
        derived_field: str = ""
    
    assert DerivedClass.__lv_library__ == "Derived"
    assert DerivedClass.__lv_class_name__ == "DerivedClass"
    
    obj = DerivedClass()
    obj.base_field = 42
    obj.derived_field = "test"
    assert obj.base_field == 42
    assert obj.derived_field == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
