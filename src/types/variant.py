"""
Variant Support - Soporte para tipos variantes de LabVIEW
"""
from typing import Tuple
import struct
from io import BytesIO
import numpy as np

from ..descriptors import TypeDescriptor, TypeDescriptorID
from ..serialization import SerializationContext
from .basic import LVType, LVBoolean, LVNumeric, LVString


class LVVariant(LVType):
    """
    Variant de LabVIEW: TypeDescriptor + datos
    """

    def __init__(self, value: LVType):
        super().__init__(value)

    def serialize(self, context: SerializationContext) -> bytes:
        buffer = BytesIO()

        # Type Descriptor
        td = self._value.get_type_descriptor()
        td_data = td.to_bytes()
        buffer.write(struct.pack(context.endianness + 'I', len(td_data)))
        buffer.write(td_data)

        # Datos
        data = self._value.serialize(context)
        buffer.write(data)

        return buffer.getvalue()

    def deserialize(self, data: bytes, context: SerializationContext) -> Tuple[LVType, int]:
        offset = 0

        # Leer Type Descriptor
        td_length = struct.unpack(context.endianness + 'I', data[offset:offset + 4])[0]
        offset += 4

        td_data = data[offset:offset + td_length]
        td = TypeDescriptor.from_bytes(td_data)
        offset += td_length

        # Crear instancia del tipo apropiado
        type_class = self._get_type_from_descriptor(td)
        instance = type_class()

        # Deserializar datos
        value, consumed = instance.deserialize(data[offset:], context)
        instance.value = value
        offset += consumed

        return instance, offset

    def _get_type_from_descriptor(self, td: TypeDescriptor) -> type:
        """Mapea TypeDescriptor a clase Python"""
        from .compound import LVArray, LVCluster
        
        mapping = {
            TypeDescriptorID.BOOL_8BIT: LVBoolean,
            TypeDescriptorID.INT8: lambda: LVNumeric(0, np.int8),
            TypeDescriptorID.INT16: lambda: LVNumeric(0, np.int16),
            TypeDescriptorID.INT32: lambda: LVNumeric(0, np.int32),
            TypeDescriptorID.INT64: lambda: LVNumeric(0, np.int64),
            TypeDescriptorID.UINT8: lambda: LVNumeric(0, np.uint8),
            TypeDescriptorID.UINT16: lambda: LVNumeric(0, np.uint16),
            TypeDescriptorID.UINT32: lambda: LVNumeric(0, np.uint32),
            TypeDescriptorID.UINT64: lambda: LVNumeric(0, np.uint64),
            TypeDescriptorID.FLOAT32: lambda: LVNumeric(0.0, np.float32),
            TypeDescriptorID.FLOAT64: lambda: LVNumeric(0.0, np.float64),
            TypeDescriptorID.STRING: LVString,
            TypeDescriptorID.ARRAY: LVArray,
            TypeDescriptorID.CLUSTER: LVCluster,
        }
        
        type_class = mapping.get(td.td_id)
        if type_class is None:
            raise ValueError(f"Unsupported type descriptor: {td.td_id}")
        
        # Si es callable (lambda), llamarlo
        if callable(type_class) and not isinstance(type_class, type):
            return type(type_class())
        
        return type_class

    def get_type_descriptor(self) -> TypeDescriptor:
        return TypeDescriptor(TypeDescriptorID.VARIANT)
