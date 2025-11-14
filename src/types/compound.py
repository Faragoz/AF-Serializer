"""
Compound LabVIEW Types - Arrays y Clusters
"""
from typing import List, Tuple, Union, Optional, Any
import struct
import numpy as np
from io import BytesIO

from ..descriptors import TypeDescriptor, TypeDescriptorID
from ..serialization import SerializationContext
from .basic import LVType


class LVArray(LVType):
    """
    Array de LabVIEW: dimensiones + datos
    Formato 1D: [num_elements (I32)] + [elements...]
    Formato 2D+: [num_dims (I32)] [dim1_size] [dim2_size] ... + [elements...]
    """

    def __init__(self, elements: List[LVType], element_type: type, dimensions: Optional[Tuple[int, ...]] = None):
        self.element_type = element_type
        self.dimensions = dimensions if dimensions else (len(elements),)
        super().__init__(elements)

    def serialize(self, context: SerializationContext) -> bytes:
        buffer = BytesIO()

        # Para arrays 1D: solo escribir num_elements
        # Para arrays 2D+: escribir num_dims + dim_sizes
        if len(self.dimensions) == 1:
            # Array 1D: [num_elements] + [elements]
            buffer.write(struct.pack(context.endianness + 'I', self.dimensions[0]))
        else:
            # Array 2D+: [num_dims] [dim1_size] [dim2_size] ... + [elements]
            buffer.write(struct.pack(context.endianness + 'I', len(self.dimensions)))
            for dim_size in self.dimensions:
                buffer.write(struct.pack(context.endianness + 'I', dim_size))

        # Serializar elementos
        for elem in self._value:
            buffer.write(elem.serialize(context))

        return buffer.getvalue()

    def deserialize(self, data: bytes, context: SerializationContext) -> Tuple[List, int]:
        offset = 0

        # Leer dimensiones
        num_dims = struct.unpack(context.endianness + 'I', data[offset:offset + 4])[0]
        offset += 4

        dims = []
        for _ in range(num_dims):
            dim = struct.unpack(context.endianness + 'I', data[offset:offset + 4])[0]
            dims.append(dim)
            offset += 4

        # Leer elementos
        elements = []
        total_elements = np.prod(dims)
        for _ in range(total_elements):
            elem = self.element_type()
            value, consumed = elem.deserialize(data[offset:], context)
            elem.value = value
            elements.append(elem)
            offset += consumed

        return elements, offset

    def get_type_descriptor(self) -> TypeDescriptor:
        elem_descriptor = self.element_type().get_type_descriptor()
        return TypeDescriptor(TypeDescriptorID.ARRAY, sub_types=[elem_descriptor])


class LVCluster(LVType):
    """
    Cluster de LabVIEW: colección ordenada de elementos
    Usa tuplas como propusiste: (nombres, valores)
    """

    def __init__(self,
                 fields: Tuple[Tuple[str, ...], Tuple[LVType, ...]],
                 named: bool = True):
        """
        Args:
            fields: ((nombres...), (valores...))
            named: Si incluir nombres en serialización
        """
        names, values = fields
        if len(names) != len(values):
            raise ValueError("Names and values must have same length")

        self.names = names
        self.named = named
        super().__init__(values)

    def __getitem__(self, key: Union[int, str]) -> LVType:
        """Acceso por índice o nombre"""
        if isinstance(key, int):
            return self._value[key]
        elif isinstance(key, str):
            idx = self.names.index(key)
            return self._value[idx]
        raise KeyError(key)

    def serialize(self, context: SerializationContext) -> bytes:
        buffer = BytesIO()
        offset = 0

        # NO escribir número de elementos - los clusters concatenan datos directamente
        # Los datos se serializan sin header según la documentación de LabVIEW

        # Serializar cada campo con alineación
        for field in self._value:
            # Alinear si necesario
            aligned_offset = context.align_offset(offset)
            """if aligned_offset != offset:
                buffer.write(b'\x00' * (aligned_offset - offset))
                offset = aligned_offset"""

            field_data = field.serialize(context)
            #print(f"{field}#{field_data.hex()}")
            buffer.write(field_data)
            offset += len(field_data)

        return buffer.getvalue()

    def deserialize(self, data: bytes, context: SerializationContext) -> Tuple[Tuple, int]:
        offset = 0

        # Leer número de elementos
        num_fields = struct.unpack(context.endianness + 'I', data[offset:offset + 4])[0]
        offset += 4

        # Deserializar campos
        values = []
        for i in range(num_fields):
            # Alinear
            offset = context.align_offset(offset)

            # Necesitamos saber el tipo (esto requiere Type Descriptor previo)
            # Por simplicidad, asumimos que ya conocemos la estructura
            field_type = type(self._value[i])
            field = field_type()
            value, consumed = field.deserialize(data[offset:], context)
            field.value = value
            values.append(field)
            offset += consumed

        return tuple(values), offset

    def get_type_descriptor(self) -> TypeDescriptor:
        sub_descriptors = [field.get_type_descriptor() for field in self._value]
        return TypeDescriptor(
            TypeDescriptorID.CLUSTER,
            properties={'num_elements': len(self._value)},
            sub_types=sub_descriptors
        )
