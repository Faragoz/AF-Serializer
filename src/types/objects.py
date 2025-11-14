"""
LabVIEW Objects - Objetos con herencia
"""
from typing import Tuple, Optional, Any
from abc import abstractmethod
from io import BytesIO
import struct

from ..descriptors import TypeDescriptor, TypeDescriptorID
from ..serialization import SerializationContext
from .basic import LVType
from .compound import LVCluster


class LVObjectMetadata:
    """Metadatos de un objeto LabVIEW"""

    def __init__(self,
                 library: str = "",
                 class_name: str = "",
                 version: Tuple[int, int, int, int] = (1, 0, 0, 0),
                 parent: Optional['LVObjectMetadata'] = None):
        self.library = library
        self.class_name = class_name
        self.version = version
        self.parent = parent

    def serialize(self, context: SerializationContext) -> bytes:
        """Serializa metadatos según formato de LVObjects"""
        buffer = BytesIO()
        
        # Serializar nombre de librería
        lib_bytes = self.library.encode('utf-8')
        buffer.write(struct.pack(context.endianness + 'I', len(lib_bytes)))
        buffer.write(lib_bytes)
        
        # Serializar nombre de clase
        class_bytes = self.class_name.encode('utf-8')
        buffer.write(struct.pack(context.endianness + 'I', len(class_bytes)))
        buffer.write(class_bytes)
        
        # Serializar versión (4 componentes uint16)
        for component in self.version:
            buffer.write(struct.pack(context.endianness + 'H', component))
        
        # Si tiene padre, serializar recursivamente
        if self.parent:
            parent_data = self.parent.serialize(context)
            buffer.write(struct.pack(context.endianness + 'I', len(parent_data)))
            buffer.write(parent_data)
        else:
            buffer.write(struct.pack(context.endianness + 'I', 0))
        
        return buffer.getvalue()


class LVObject(LVType):
    """
    Objeto base de LabVIEW.

    Estructura:
    - Metadata (library, class, version)
    - Parent data (si aplica)
    - Private data (cluster)
    """

    def __init__(self):
        # Auto-detectar metadatos desde la clase Python
        self._metadata = self._extract_metadata()
        self._private_data = self._initialize_private_data()
        super().__init__(self._private_data)

    def _extract_metadata(self) -> LVObjectMetadata:
        """Extrae metadatos automáticamente desde la clase Python"""
        class_name = self.__class__.__name__.replace("_", " ") + ".lvclass"

        # Obtener clase padre si existe
        parent_meta = None
        bases = self.__class__.__bases__
        if bases and bases[0] != LVObject:
            # Instanciar padre temporalmente para obtener metadata
            parent = bases[0]()
            parent_meta = parent._metadata

        # Buscar atributos de versión
        version = getattr(self.__class__, '__lv_version__', (1, 0, 0, 0))
        library = getattr(self.__class__, '__lv_library__', "") + ".lvlib"

        return LVObjectMetadata(
            library=library,
            class_name=class_name,
            version=version,
            parent=parent_meta
        )

    @abstractmethod
    def _initialize_private_data(self) -> LVCluster:
        """
        Define la estructura de private data.
        Debe retornar un LVCluster con los campos del objeto.
        """
        pass

    def serialize(self, context: SerializationContext) -> bytes:
        buffer = BytesIO()

        # Metadata
        buffer.write(self._metadata.serialize(context))

        # Parent data (si existe)
        if self._metadata.parent:
            # Serializar datos del padre
            pass

        # Private data
        buffer.write(self._private_data.serialize(context))

        return buffer.getvalue()

    # TODO: Logica de deserialización completa
    def deserialize(self, data: bytes, context: SerializationContext) -> Tuple[Any, int]:
        pass

    def get_type_descriptor(self) -> TypeDescriptor:
        return TypeDescriptor(
            TypeDescriptorID.CLUSTER,  # Los objetos son clusters especiales
            properties={
                'class': self._metadata.class_name,
                'library': self._metadata.library
            },
            sub_types=[self._private_data.get_type_descriptor()]
        )
