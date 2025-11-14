"""
Basic LabVIEW Types - Tipos básicos de LabVIEW
"""
from typing import Any, Union, Tuple
import numpy as np
import struct

from ..descriptors import TypeDescriptor, TypeDescriptorID
from ..serialization import ISerializable, SerializationContext


class LVType(ISerializable):
    """Clase base para todos los tipos LabVIEW"""

    def __init__(self, value: Any = None):
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = self._validate(val)

    def _validate(self, val) -> Any:
        """Validación específica del tipo"""
        return val

    def __repr__(self):
        return f"{self.__class__.__name__}({self._value})"


class LVNumeric(LVType):
    """Base para tipos numéricos"""

    # Mapeo de tipos Python/NumPy a LabVIEW
    TYPE_MAPPING = {
        np.int8: (TypeDescriptorID.INT8, 'b'),
        np.int16: (TypeDescriptorID.INT16, 'h'),
        np.int32: (TypeDescriptorID.INT32, 'i'),
        np.int64: (TypeDescriptorID.INT64, 'q'),
        np.uint8: (TypeDescriptorID.UINT8, 'B'),
        np.uint16: (TypeDescriptorID.UINT16, 'H'),
        np.uint32: (TypeDescriptorID.UINT32, 'I'),
        np.uint64: (TypeDescriptorID.UINT64, 'Q'),
        np.float32: (TypeDescriptorID.FLOAT32, 'f'),
        np.float64: (TypeDescriptorID.FLOAT64, 'd'),
    }

    def __init__(self, value: Union[int, float, np.number],
                 dtype: type = np.float64):
        self.dtype = dtype
        super().__init__(self._to_numpy(value))

    def _to_numpy(self, val):
        """Convierte a tipo NumPy apropiado"""
        if isinstance(val, (int, float)):
            return self.dtype(val)
        elif isinstance(val, np.number):
            return val.astype(self.dtype)
        raise TypeError(f"Cannot convert {type(val)} to {self.dtype}")

    def serialize(self, context: SerializationContext) -> bytes:
        td_id, format_char = self.TYPE_MAPPING[self.dtype]
        return struct.pack(context.endianness + format_char, self._value)

    def deserialize(self, data: bytes, context: SerializationContext) -> Tuple[Any, int]:
        td_id, format_char = self.TYPE_MAPPING[self.dtype]
        size = struct.calcsize(format_char)
        value = struct.unpack(context.endianness + format_char, data[:size])[0]
        return self.dtype(value), size

    def get_type_descriptor(self) -> TypeDescriptor:
        td_id, _ = self.TYPE_MAPPING[self.dtype]
        return TypeDescriptor(td_id)


class LVBoolean(LVType):
    """Boolean de LabVIEW (8-bit)"""

    def serialize(self, context: SerializationContext) -> bytes:
        return struct.pack('B', 1 if self._value else 0)

    def deserialize(self, data: bytes, context: SerializationContext) -> Tuple[bool, int]:
        return bool(data[0]), 1

    def get_type_descriptor(self) -> TypeDescriptor:
        return TypeDescriptor(TypeDescriptorID.BOOL_8BIT)


class LVString(LVType):
    """
    String de LabVIEW: int32 (length) + datos
    """

    def serialize(self, context: SerializationContext) -> bytes:
        encoded = self._value.encode('utf-8')
        length = len(encoded)
        return struct.pack(context.endianness + 'I', length) + encoded

    def deserialize(self, data: bytes, context: SerializationContext) -> Tuple[str, int]:
        length = struct.unpack(context.endianness + 'I', data[:4])[0]
        string_data = data[4:4 + length]
        return string_data.decode('utf-8'), 4 + length

    def get_type_descriptor(self) -> TypeDescriptor:
        return TypeDescriptor(TypeDescriptorID.STRING)
