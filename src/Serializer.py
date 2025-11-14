from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple, List, Optional, Union
from enum import IntEnum
import numpy as np
from io import BytesIO
import struct


# ============================================================================
# LAYER 1: Type Descriptors (Base del sistema de tipos de LabVIEW)
# ============================================================================

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
        """Deserializa desde bytes"""
        # Implementación inversa
        pass


# ============================================================================
# LAYER 2: Serialization Strategy (Patrón Strategy)
# ============================================================================

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


# ============================================================================
# LAYER 3: Basic Types (Tipos básicos LabVIEW)
# ============================================================================

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


# ============================================================================
# LAYER 4: Compound Types (Tipos compuestos)
# ============================================================================

class LVArray(LVType):
    """
    Array de LabVIEW: dimensiones + datos
    Formato: int32 (num_dims) + int32[] (dims) + elementos
    """

    def __init__(self, elements: List[LVType], element_type: type):
        self.element_type = element_type
        super().__init__(elements)

    def serialize(self, context: SerializationContext) -> bytes:
        buffer = BytesIO()

        # Número de dimensiones (1D por simplicidad inicial)
        buffer.write(struct.pack(context.endianness + 'I', 1))

        # Tamaño de la dimensión
        buffer.write(struct.pack(context.endianness + 'I', len(self._value)))

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

        # Número de elementos
        buffer.write(struct.pack(context.endianness + 'I', len(self._value)))
        offset += 4

        # Serializar cada campo con alineación
        for field in self._value:
            # Alinear si necesario
            aligned_offset = context.align_offset(offset)
            if aligned_offset != offset:
                buffer.write(b'\x00' * (aligned_offset - offset))
                offset = aligned_offset

            field_data = field.serialize(context)
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


# ============================================================================
# LAYER 5: LabVIEW Objects (Objetos con herencia)
# ============================================================================

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
        # Implementación específica del formato de LVObjects.txt
        pass


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
        class_name = self.__class__.__name__

        # Obtener clase padre si existe
        parent_meta = None
        bases = self.__class__.__bases__
        if bases and bases[0] != LVObject:
            # Instanciar padre temporalmente para obtener metadata
            parent = bases[0]()
            parent_meta = parent._metadata

        # Buscar atributos de versión
        version = getattr(self.__class__, '__lv_version__', (1, 0, 0, 0))
        library = getattr(self.__class__, '__lv_library__', "")

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


# ============================================================================
# LAYER 6: Variant Support
# ============================================================================

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
        # Implementar mapeo inverso
        pass

    def get_type_descriptor(self) -> TypeDescriptor:
        return TypeDescriptor(TypeDescriptorID.VARIANT)


# ============================================================================
# LAYER 7: High-Level API (API Conveniente)
# ============================================================================

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
        """Convierte tipos Python a LVType automáticamente"""
        if isinstance(obj, LVType):
            return obj
        elif isinstance(obj, bool):
            return LVBoolean(obj)
        elif isinstance(obj, int):
            return LVNumeric(obj, np.int32)
        elif isinstance(obj, float):
            return LVNumeric(obj, np.float64)
        elif isinstance(obj, str):
            return LVString(obj)
        elif isinstance(obj, (list, tuple)):
            # Convertir a LVArray
            if not obj:
                raise ValueError("Cannot infer array type from empty list")
            elem_type = type(self._to_lv_type(obj[0]))
            elements = [self._to_lv_type(x) for x in obj]
            return LVArray(elements, elem_type)
        else:
            raise TypeError(f"Cannot convert {type(obj)} to LVType")

    def _python_to_lv_type(self, python_type: type) -> type:
        """Mapea tipos Python a clases LVType"""
        mapping = {
            bool: LVBoolean,
            int: lambda: LVNumeric(0, np.int32),
            float: lambda: LVNumeric(0.0, np.float64),
            str: LVString,
        }
        return mapping.get(python_type, LVType)


# ============================================================================
# EJEMPLOS DE USO
# ============================================================================

# Ejemplo 1: Tipos básicos
def example_basic_types():
    serializer = LVSerializer()

    # Numeric
    num = LVNumeric(42, np.int32)
    data = serializer.serialize(num)
    print(f"Serialized int32: {data.hex()}")

    # String
    text = LVString("Hello LabVIEW")
    data = serializer.serialize(text)
    print(f"Serialized string: {data.hex()}")

    # Boolean
    flag = LVBoolean(True)
    data = serializer.serialize(flag)
    print(f"Serialized boolean: {data.hex()}")


# Ejemplo 2: Cluster
def example_cluster():
    # Crear cluster con nombres y valores
    names = ("x", "y", "label")
    values = (
        LVNumeric(10.5, np.float64),
        LVNumeric(20.3, np.float64),
        LVString("Point A")
    )

    cluster = LVCluster((names, values))

    # Acceso por nombre
    print(f"x value: {cluster['x'].value}")

    # Serializar
    serializer = LVSerializer()
    data = serializer.serialize(cluster)
    print(cluster)
    print(f"Serialized cluster: {data.hex()}")


# Ejemplo 3: Objeto personalizado
class MyLVObject(LVObject):
    """Ejemplo de objeto LabVIEW personalizado"""

    __lv_version__ = (1, 2, 3, 4)
    __lv_library__ = "MyLibrary"

    def _initialize_private_data(self) -> LVCluster:
        """Define la estructura interna del objeto"""
        names = ("timestamp", "value", "status")
        values = (
            LVNumeric(0, np.uint64),  # timestamp
            LVNumeric(0.0, np.float64),  # value
            LVBoolean(False)  # status
        )
        return LVCluster((names, values))

    def set_data(self, timestamp: int, value: float, status: bool):
        """Método helper para actualizar datos"""
        self._private_data['timestamp'].value = timestamp
        self._private_data['value'].value = value
        self._private_data['status'].value = status




def example_custom_object():
    obj = MyLVObject()
    obj.set_data(1234567890, 42.5, True)

    serializer = LVSerializer()
    data = serializer.serialize(obj)
    print(f"Serialized object: {data.hex()}")
    print(f"Object metadata: {obj._metadata.class_name} v{obj._metadata.version}")


# Ejemplo 4: Herencia de objetos
class AdvancedLVObject(MyLVObject):
    """Objeto que hereda de MyLVObject"""

    __lv_version__ = (2, 0, 0, 0)

    def _initialize_private_data(self) -> LVCluster:
        """Extiende la estructura del padre"""
        # Obtener estructura del padre
        parent_cluster = super()._initialize_private_data()

        # Agregar campos adicionales
        names = parent_cluster.names + ("extra_field",)
        values = parent_cluster.value + (LVString("Extra data"),)

        return LVCluster((names, values))


# Ejemplo 5: API de alto nivel (conversión automática)
def example_high_level_api():
    serializer = LVSerializer()

    # Serializar tipos Python directamente
    data_int = serializer.serialize(42)
    data_float = serializer.serialize(3.14159)
    data_str = serializer.serialize("Hello")
    data_list = serializer.serialize([1, 2, 3, 4, 5])

    print(f"Auto-serialized int: {data_int.hex()}")
    print(f"Auto-serialized float: {data_float.hex()}")
    print(f"Auto-serialized string: {data_str.hex()}")
    print(f"Auto-serialized list: {data_list.hex()}")

if __name__ == "__main__":
    example_basic_types()
    example_cluster()
    example_custom_object()
    #example_high_level_api()