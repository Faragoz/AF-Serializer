"""
High-Level Serializer - API de alto nivel para serialización/deserialización
"""
from typing import Any, Union
import numpy as np

from .serialization import SerializationContext
from .types import LVType, LVBoolean, LVNumeric, LVString
from .auto_flatten import _auto_infer_type


class LVSerializer:
    """
    API de alto nivel para serialización/deserialización.
    Maneja automáticamente contextos y conversiones.
    """

    def __init__(self, endianness: str = 'big', alignment: bool = True):
        self.context = SerializationContext(endianness, alignment)

    def serialize(self, obj: Union[LVType, Any]) -> bytes:
        """
        Serializa cualquier objeto Python a formato LabVIEW.
        Convierte automáticamente tipos Python a LVType si es necesario.
        """
        lv_obj = self._to_lv_type(obj)
        return lv_obj.serialize(self.context)

    def deserialize(self, data: bytes, type_hint: type) -> Any:
        """
        Deserializa datos LabVIEW.

        Args:
            data: Bytes a deserializar
            type_hint: Tipo esperado (LVType o Python)
        """
        if issubclass(type_hint, LVType):
            instance = type_hint()
            value, _ = instance.deserialize(data, self.context)
            return value
        else:
            # Convertir tipo Python a LVType
            lv_type = self._python_to_lv_type(type_hint)
            instance = lv_type()
            value, _ = instance.deserialize(data, self.context)
            return value

    def _to_lv_type(self, obj: Any) -> LVType:
        """Convierte tipos Python a LVType usando auto-inferencia"""
        return _auto_infer_type(obj)

    def _python_to_lv_type(self, python_type: type) -> type:
        """Mapea tipos Python a clases LVType"""
        mapping = {
            bool: LVBoolean,
            int: lambda: LVNumeric(0, np.int32),
            float: lambda: LVNumeric(0.0, np.float64),
            str: LVString,
        }
        return mapping.get(python_type, LVType)
