"""
Serialization Strategy - Configuración y contexto de serialización
"""
from abc import ABC, abstractmethod
from typing import Any, Tuple
from .descriptors import TypeDescriptor


class SerializationContext:
    """Configuración de serialización"""

    def __init__(self,
                 endianness: str = 'big',  # LabVIEW usa big-endian para Networking
                 alignment: bool = True,  # LabVIEW alinea a 4 bytes
                 include_type_descriptors: bool = True):
        self.endianness = '<' if endianness == 'little' else '>'
        self.alignment = alignment
        self.include_type_descriptors = include_type_descriptors

    def align_offset(self, offset: int, boundary: int = 4) -> int:
        """Alinea offset según boundary de LabVIEW"""
        if not self.alignment:
            return offset
        remainder = offset % boundary
        return offset if remainder == 0 else offset + (boundary - remainder)


class ISerializable(ABC):
    """Interfaz para todos los tipos serializables"""

    @abstractmethod
    def serialize(self, context: SerializationContext) -> bytes:
        """Serializa a bytes según contexto"""
        pass

    @abstractmethod
    def deserialize(self, data: bytes, context: SerializationContext) -> Tuple[Any, int]:
        """
        Deserializa desde bytes.
        Retorna: (valor_deserializado, bytes_consumidos)
        """
        pass

    @abstractmethod
    def get_type_descriptor(self) -> TypeDescriptor:
        """Obtiene el Type Descriptor asociado"""
        pass
