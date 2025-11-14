"""
Type Descriptors - Base del sistema de tipos de LabVIEW
"""
from enum import IntEnum
from typing import Any, Dict, List, Optional
from io import BytesIO
import struct


class TypeDescriptorID(IntEnum):
    """Type Descriptor IDs según LBTypeDescriptor.txt"""
    VOID = 0x00
    INT8 = 0x01
    INT16 = 0x02
    INT32 = 0x03
    INT64 = 0x04
    UINT8 = 0x05
    UINT16 = 0x06
    UINT32 = 0x07
    UINT64 = 0x08
    FLOAT32 = 0x09  # SGL
    FLOAT64 = 0x0A  # DBL
    FLOATEXT = 0x0B  # EXT
    COMPLEX64 = 0x0C  # CSG
    COMPLEX128 = 0x0D  # CDB
    COMPLEXEXT = 0x0E  # CXT
    ENUM_U8 = 0x15
    ENUM_U16 = 0x16
    ENUM_U32 = 0x17
    BOOL_16BIT = 0x20  # Raramente usado
    BOOL_8BIT = 0x21  # LVBoolean estándar
    STRING = 0x30
    PATH = 0x32
    PICTURE = 0x33
    ARRAY = 0x40
    CLUSTER = 0x50
    VARIANT = 0x53
    WAVEFORM = 0x54
    FIXED_POINT = 0x5F
    REFNUM = 0x70


class TypeDescriptor:
    """
    Representa un Type Descriptor de LabVIEW.
    Fundamental para serialización correcta.
    """

    def __init__(self, td_id: TypeDescriptorID,
                 properties: Optional[Dict[str, Any]] = None,
                 sub_types: Optional[List['TypeDescriptor']] = None):
        self.td_id = td_id
        self.properties = properties or {}
        self.sub_types = sub_types or []

    def to_bytes(self) -> bytes:
        """Serializa el Type Descriptor"""
        # Implementación según formato flattened de LabVIEW
        buffer = BytesIO()
        buffer.write(struct.pack('<I', self.td_id))
        # ... propiedades y sub_types
        return buffer.getvalue()

    @classmethod
    def from_bytes(cls, data: bytes) -> 'TypeDescriptor':
        """Deserializa un Type Descriptor desde bytes"""
        buffer = BytesIO(data)
        
        # Leer ID del tipo
        td_id_value = struct.unpack('<I', buffer.read(4))[0]
        td_id = TypeDescriptorID(td_id_value)
        
        properties = {}
        sub_types = []
        
        # Leer propiedades y sub-tipos según el tipo
        if td_id == TypeDescriptorID.ARRAY:
            # Leer descriptor del elemento
            elem_data = buffer.read()  # Simplificado
            if elem_data:
                sub_types.append(cls.from_bytes(elem_data))
        
        elif td_id == TypeDescriptorID.CLUSTER:
            # Leer número de elementos
            num_elements = struct.unpack('<I', buffer.read(4))[0]
            properties['num_elements'] = num_elements
            
            # Leer descriptores de cada elemento
            for _ in range(num_elements):
                elem_data = buffer.read()  # Simplificado
                if elem_data:
                    sub_types.append(cls.from_bytes(elem_data))
        
        return cls(td_id, properties, sub_types)
