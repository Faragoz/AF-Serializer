import pytest
import numpy as np
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from Serializer import (
    lvflatten, _auto_infer_type,
    LVBoolean, LVNumeric, LVString, LVArray, LVCluster
)


def test_auto_infer_primitives():
    """Test inferencia de tipos primitivos"""
    assert isinstance(_auto_infer_type(True), LVBoolean)
    assert isinstance(_auto_infer_type(42), LVNumeric)
    assert isinstance(_auto_infer_type(3.14), LVNumeric)
    assert isinstance(_auto_infer_type("hello"), LVString)


def test_auto_infer_list_homogeneous():
    """Test inferencia de listas homogéneas → Array"""
    result = _auto_infer_type([1, 2, 3, 4])
    assert isinstance(result, LVArray)
    assert len(result.value) == 4


def test_auto_infer_list_heterogeneous():
    """Test inferencia de listas heterogéneas → Cluster"""
    result = _auto_infer_type([1, "hello", 3.14])
    assert isinstance(result, LVCluster)
    assert len(result.value) == 3


def test_auto_infer_tuple():
    """Test inferencia de tuplas → Cluster sin nombres"""
    result = _auto_infer_type(("Hello World", 1, 0.15))
    assert isinstance(result, LVCluster)
    assert not result.named


def test_auto_infer_dict():
    """Test inferencia de diccionarios → Cluster con nombres"""
    result = _auto_infer_type({"x": 10, "y": 20})
    assert isinstance(result, LVCluster)
    assert result.named
    assert "x" in result.names


def test_lvflatten_original_example():
    """Test del ejemplo original del usuario"""
    data = ("Hello World", 1, 0.15, ["a", "b", "c"], [1, 2, 3])
    result = lvflatten(data)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_lvflatten_nested():
    """Test estructura anidada compleja"""
    data = {
        "header": ("v1.0", 123),
        "values": [10, 20, 30],
        "active": True
    }
    result = lvflatten(data)
    assert isinstance(result, bytes)


def test_empty_list_raises():
    """Test que lista vacía lanza error"""
    with pytest.raises(ValueError, match="empty list"):
        _auto_infer_type([])


def test_empty_tuple_raises():
    """Test que tupla vacía lanza error"""
    with pytest.raises(ValueError, match="empty tuple"):
        _auto_infer_type(())


def test_empty_dict_raises():
    """Test que dict vacío lanza error"""
    with pytest.raises(ValueError, match="empty dict"):
        _auto_infer_type({})


def test_unsupported_type_raises():
    """Test que tipo no soportado lanza error"""
    with pytest.raises(TypeError):
        _auto_infer_type(object())


def test_lvflatten_simple_types():
    """Test lvflatten con tipos simples"""
    # Integer
    result = lvflatten(42)
    assert isinstance(result, bytes)
    
    # Float
    result = lvflatten(3.14)
    assert isinstance(result, bytes)
    
    # String
    result = lvflatten("Hello")
    assert isinstance(result, bytes)
    
    # Boolean
    result = lvflatten(True)
    assert isinstance(result, bytes)


def test_lvflatten_homogeneous_list():
    """Test lvflatten con lista homogénea"""
    result = lvflatten([1, 2, 3, 4, 5])
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_lvflatten_dict_structure():
    """Test lvflatten con estructura dict"""
    data = {"x": 10, "y": 20, "label": "Point A"}
    result = lvflatten(data)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_auto_infer_already_lvtype():
    """Test que LVType existente se retorna tal cual"""
    original = LVNumeric(42, np.int32)
    result = _auto_infer_type(original)
    assert result is original


def test_nested_lists():
    """Test con listas anidadas"""
    data = [[1, 2], [3, 4], [5, 6]]
    result = lvflatten(data)
    assert isinstance(result, bytes)


def test_boolean_before_int():
    """Test que boolean se detecta antes que int (bool es subclase de int)"""
    result = _auto_infer_type(True)
    assert isinstance(result, LVBoolean)
    assert not isinstance(result, LVNumeric)
