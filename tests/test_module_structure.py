"""
Tests for the new modular structure - ensuring all imports work correctly
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_import_from_main_module():
    """Test importing from main src module"""
    from src import (
        lvflatten,
        lvunflatten,
        LVSerializer,
        LVType,
        LVNumeric,
        LVBoolean,
        LVString,
        LVArray,
        LVCluster,
        LVObject,
        LVObjectMetadata,
        LVVariant,
        TypeDescriptor,
        TypeDescriptorID,
        SerializationContext,
        ISerializable,
        lvclass,
    )
    
    assert callable(lvflatten)
    assert callable(lvunflatten)
    assert LVSerializer is not None
    assert lvclass is not None


def test_import_from_types():
    """Test importing from types submodule"""
    from src.types import (
        LVType,
        LVNumeric,
        LVBoolean,
        LVString,
        LVArray,
        LVCluster,
        LVObject,
        LVObjectMetadata,
        LVVariant,
    )
    
    assert LVType is not None
    assert LVNumeric is not None
    assert LVBoolean is not None


def test_import_from_basic():
    """Test importing from types.basic"""
    from src.types.basic import LVType, LVNumeric, LVBoolean, LVString
    
    assert LVType is not None
    assert LVNumeric is not None
    assert LVBoolean is not None
    assert LVString is not None


def test_import_from_compound():
    """Test importing from types.compound"""
    from src.types.compound import LVArray, LVCluster
    
    assert LVArray is not None
    assert LVCluster is not None


def test_import_from_objects():
    """Test importing from types.objects"""
    from src.types.objects import LVObject, LVObjectMetadata
    
    assert LVObject is not None
    assert LVObjectMetadata is not None


def test_import_from_variant():
    """Test importing from types.variant"""
    from src.types.variant import LVVariant
    
    assert LVVariant is not None


def test_import_from_descriptors():
    """Test importing from descriptors"""
    from src.descriptors import TypeDescriptor, TypeDescriptorID
    
    assert TypeDescriptor is not None
    assert TypeDescriptorID is not None


def test_import_from_serialization():
    """Test importing from serialization"""
    from src.serialization import SerializationContext, ISerializable
    
    assert SerializationContext is not None
    assert ISerializable is not None


def test_import_from_auto_flatten():
    """Test importing from auto_flatten"""
    from src.auto_flatten import lvflatten, lvunflatten, _auto_infer_type
    
    assert callable(lvflatten)
    assert callable(lvunflatten)
    assert callable(_auto_infer_type)


def test_import_from_lv_serializer():
    """Test importing from lv_serializer"""
    from src.lv_serializer import LVSerializer
    
    assert LVSerializer is not None


def test_import_from_decorators():
    """Test importing from decorators"""
    from src.decorators import lvclass
    
    assert callable(lvclass)


def test_backward_compatibility_import():
    """Test backward compatibility through Serializer.py"""
    from Serializer import (
        lvflatten,
        LVType,
        LVNumeric,
        LVBoolean,
        LVString,
        LVArray,
        LVCluster,
        LVSerializer,
    )
    
    assert callable(lvflatten)
    assert LVType is not None
    assert LVNumeric is not None
    assert LVSerializer is not None


def test_functional_import():
    """Test that imports are functional, not just present"""
    from src import lvflatten, LVNumeric
    import numpy as np
    
    # Test lvflatten works
    result = lvflatten(42)
    assert isinstance(result, bytes)
    assert len(result) == 4
    
    # Test LVNumeric works
    num = LVNumeric(42, np.int32)
    assert num.value == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
