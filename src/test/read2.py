# -*- coding: utf-8 -*-

""" LabVIEW Class System - Object-Oriented Serialization

    Sistema de herencia de clases que replica el comportamiento de LabVIEW.
    Permite serialización/deserialización automática basada en la jerarquía de clases.
"""

import struct
import io
from typing import Any, List, Union, Tuple, Optional, Type
from dataclasses import dataclass, fields
from abc import ABC, abstractmethod

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None


# ==================== BASE SYSTEM ====================

@dataclass
class LVClassVersion:
    """Version number for a LabVIEW class (W.X.Y.Z format)"""
    major: int = 0
    minor: int = 0
    patch: int = 0
    build: int = 0

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}.{self.build}"


class LVObject(ABC):
    """
    Base class for all LabVIEW-compatible objects.
    Similar to LabVIEW Object - the root of all classes.
    """

    # Class metadata (override in subclasses)
    _lv_library: str = ""
    _lv_class: str = "LabVIEW Object"
    _lv_version: LVClassVersion = LVClassVersion(0, 0, 0, 0)

    def __init__(self):
        """Initialize LabVIEW object"""
        pass

    @classmethod
    def get_qualified_name(cls) -> str:
        """Get fully qualified class name for LabVIEW"""
        if cls._lv_library:
            return f"{cls._lv_library}\\{cls._lv_class}"
        return cls._lv_class

    @classmethod
    def get_hierarchy(cls) -> List[Type['LVObject']]:
        """Get class hierarchy from oldest ancestor to this class"""
        hierarchy = []
        for base in reversed(cls.__mro__):
            if base is LVObject or (issubclass(base, LVObject) and base is not LVObject):
                hierarchy.append(base)
        return hierarchy

    @classmethod
    def get_num_levels(cls) -> int:
        """Get number of hierarchy levels (excluding LVObject root)"""
        hierarchy = cls.get_hierarchy()
        # Exclude LVObject itself if it's in the hierarchy
        return len([c for c in hierarchy if c is not LVObject])

    def get_private_data(self) -> Optional[Tuple]:
        """
        Get private data for this class level only.
        Override in subclasses to return a tuple of the private data.
        Return None for default/empty data.
        """
        return None

    def set_private_data(self, data: Any):
        """
        Set private data for this class level.
        Override in subclasses to unpack the data tuple.
        """
        pass

    def to_bytes(self) -> bytes:
        """Serialize this object to LabVIEW format"""
        serializer = LVSerializer()
        return serializer.serialize_object(self)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'LVObject':
        """Deserialize object from LabVIEW format"""
        serializer = LVSerializer()
        return serializer.deserialize_object(data, cls)


# ==================== SERIALIZER ====================

class LVSerializer:
    """Serializer for LVObject hierarchy"""

    def __init__(self, endian='big'):
        self.endian = '>' if endian == 'big' else '<'

    def serialize_object(self, obj: LVObject) -> bytes:
        """Serialize LVObject to LabVIEW binary format"""
        buffer = io.BytesIO()

        # Get hierarchy
        hierarchy = obj.__class__.get_hierarchy()
        num_levels = len([c for c in hierarchy if c is not LVObject])

        # 1. NumLevels (BIG ENDIAN)
        buffer.write(struct.pack('>I', num_levels))

        if num_levels == 0:
            return buffer.getvalue()

        # 2. ClassName
        class_name = obj.__class__.get_qualified_name()
        self._write_classname(buffer, class_name)

        # 3. VersionList (BIG ENDIAN, oldest to newest)
        for cls in hierarchy:
            if cls is LVObject:
                continue
            version = cls._lv_version
            buffer.write(struct.pack('>H', version.major))
            buffer.write(struct.pack('>H', version.minor))
            buffer.write(struct.pack('>H', version.patch))
            buffer.write(struct.pack('>H', version.build))

        # 4. ClusterData (BIG ENDIAN, oldest to newest)
        for cls in hierarchy:
            if cls is LVObject:
                continue

            # Get private data for this level
            if cls == obj.__class__:
                # For the actual class, get instance data
                data = obj.get_private_data()
            else:
                # For parent classes, check if they have default data
                # Create a temporary instance to get default data
                try:
                    temp_obj = cls()
                    data = temp_obj.get_private_data()
                except:
                    data = None

            if data is None:
                buffer.write(struct.pack('>I', 0))
            else:
                # Serialize the cluster data
                cluster_bytes = self._serialize_cluster(data)
                buffer.write(struct.pack('>I', len(cluster_bytes)))
                buffer.write(cluster_bytes)

        return buffer.getvalue()

    def deserialize_object(self, data: bytes, target_class: Type[LVObject]) -> LVObject:
        """Deserialize LabVIEW binary format to LVObject"""
        buffer = io.BytesIO(data)

        # 1. NumLevels
        num_levels = struct.unpack('>I', buffer.read(4))[0]

        if num_levels == 0:
            return target_class()

        # 2. ClassName
        class_name = self._read_classname(buffer)

        # 3. VersionList
        versions = []
        for _ in range(num_levels):
            major = struct.unpack('>H', buffer.read(2))[0]
            minor = struct.unpack('>H', buffer.read(2))[0]
            patch = struct.unpack('>H', buffer.read(2))[0]
            build = struct.unpack('>H', buffer.read(2))[0]
            versions.append(LVClassVersion(major, minor, patch, build))

        # 4. ClusterData
        cluster_data_list = []
        for _ in range(num_levels):
            data_length = struct.unpack('>I', buffer.read(4))[0]
            if data_length == 0:
                cluster_data_list.append(None)
            else:
                cluster_data = buffer.read(data_length)
                cluster_data_list.append(cluster_data)

        # Create instance and set data
        obj = target_class()

        # Get hierarchy
        hierarchy = target_class.get_hierarchy()
        hierarchy = [c for c in hierarchy if c is not LVObject]

        # Set data for the actual class (last in hierarchy)
        if cluster_data_list[-1] is not None:
            # Get template from class
            template_obj = target_class()
            template = template_obj.get_private_data()

            if template is not None:
                # Deserialize cluster
                deserialized_data = self._deserialize_cluster(cluster_data_list[-1], template)
                obj.set_private_data(deserialized_data)

        return obj

    def _serialize_cluster(self, data: Tuple) -> bytes:
        """Serialize a cluster (tuple) to bytes"""
        buffer = io.BytesIO()
        old_endian = self.endian
        self.endian = '>'  # Clusters use BIG ENDIAN

        for i, value in enumerate(data):
            self._serialize_value(buffer, value, in_cluster=True)

        self.endian = old_endian
        return buffer.getvalue()

    def _deserialize_cluster(self, data: bytes, template: Tuple) -> Tuple:
        """Deserialize a cluster using template"""
        buffer = io.BytesIO(data)
        old_endian = self.endian
        self.endian = '>'  # Clusters use BIG ENDIAN

        result = []
        for elem in template:
            value = self._deserialize_value(buffer, elem, in_cluster=True)
            result.append(value)

        self.endian = old_endian
        return tuple(result)

    def _serialize_value(self, buffer: io.BytesIO, value: Any, in_cluster: bool = False):
        """Serialize a single value"""
        # Numpy types
        if HAS_NUMPY and hasattr(value, 'dtype'):
            self._serialize_numpy(buffer, value)
            return

        # Basic types
        if isinstance(value, bool):
            buffer.write(struct.pack(f'{self.endian}B', 1 if value else 0))
        elif isinstance(value, int):
            if -2147483648 <= value <= 2147483647:
                buffer.write(struct.pack(f'{self.endian}i', value))
            else:
                buffer.write(struct.pack(f'{self.endian}q', value))
        elif isinstance(value, float):
            buffer.write(struct.pack(f'{self.endian}d', value))
        elif isinstance(value, (str, bytes)):
            if isinstance(value, str):
                value = value.encode('utf-8')
            buffer.write(struct.pack(f'{self.endian}I', len(value)))
            buffer.write(value)
            # Add padding in clusters
            if in_cluster:
                total_len = 4 + len(value)
                padding = (4 - (total_len % 4)) % 4
                if padding > 0:
                    buffer.write(b'\x00' * padding)
        elif isinstance(value, (list, tuple)):
            # Array
            buffer.write(struct.pack(f'{self.endian}I', len(value)))
            for elem in value:
                self._serialize_value(buffer, elem, in_cluster)
        else:
            raise ValueError(f"Unsupported type: {type(value)}")

    def _deserialize_value(self, buffer: io.BytesIO, template: Any, in_cluster: bool = False) -> Any:
        """Deserialize a single value using template"""
        # Numpy types
        if HAS_NUMPY and hasattr(template, 'dtype'):
            return self._deserialize_numpy(buffer, template)

        if isinstance(template, bool):
            return struct.unpack(f'{self.endian}B', buffer.read(1))[0] != 0
        elif isinstance(template, int):
            if -2147483648 <= template <= 2147483647 or template == 0:
                return struct.unpack(f'{self.endian}i', buffer.read(4))[0]
            else:
                return struct.unpack(f'{self.endian}q', buffer.read(8))[0]
        elif isinstance(template, float):
            return struct.unpack(f'{self.endian}d', buffer.read(8))[0]
        elif isinstance(template, (str, bytes)):
            length = struct.unpack(f'{self.endian}I', buffer.read(4))[0]
            data = buffer.read(length)
            result = data.decode('utf-8') if isinstance(template, str) else data
            # Skip padding in clusters
            if in_cluster:
                total_len = 4 + length
                padding = (4 - (total_len % 4)) % 4
                if padding > 0:
                    buffer.read(padding)
            return result
        elif isinstance(template, (list, tuple)):
            length = struct.unpack(f'{self.endian}I', buffer.read(4))[0]
            result = []
            elem_template = template[0] if template else 0
            for _ in range(length):
                result.append(self._deserialize_value(buffer, elem_template, in_cluster))
            return result if isinstance(template, list) else tuple(result)
        else:
            raise ValueError(f"Unsupported template type: {type(template)}")

    def _serialize_numpy(self, buffer: io.BytesIO, value):
        """Serialize numpy value"""
        dtype = value.dtype
        val = value.item() if hasattr(value, 'item') else value

        type_map = {
            np.int8: 'b', np.int16: 'h', np.int32: 'i', np.int64: 'q',
            np.uint8: 'B', np.uint16: 'H', np.uint32: 'I', np.uint64: 'Q',
            np.float32: 'f', np.float64: 'd'
        }

        if dtype in type_map:
            buffer.write(struct.pack(f'{self.endian}{type_map[dtype]}', val))
        else:
            raise ValueError(f"Unsupported numpy dtype: {dtype}")

    def _deserialize_numpy(self, buffer: io.BytesIO, template):
        """Deserialize numpy value"""
        dtype = template.dtype

        type_map = {
            np.int8: ('b', 1), np.int16: ('h', 2), np.int32: ('i', 4), np.int64: ('q', 8),
            np.uint8: ('B', 1), np.uint16: ('H', 2), np.uint32: ('I', 4), np.uint64: ('Q', 8),
            np.float32: ('f', 4), np.float64: ('d', 8)
        }

        if dtype in type_map:
            fmt, size = type_map[dtype]
            value = struct.unpack(f'{self.endian}{fmt}', buffer.read(size))[0]
            return dtype.type(value)
        else:
            raise ValueError(f"Unsupported numpy dtype: {dtype}")

    def _write_classname(self, buffer: io.BytesIO, class_name: str):
        """Write class name in Pascal string format"""
        parts = class_name.replace('\\', '/').split('/')

        classname_buffer = io.BytesIO()
        for part in parts:
            part_bytes = part.encode('utf-8')
            classname_buffer.write(struct.pack('B', len(part_bytes)))
            classname_buffer.write(part_bytes)
        classname_buffer.write(b'\x00')

        classname_data = classname_buffer.getvalue()
        total_length = len(classname_data)

        buffer.write(struct.pack('B', total_length))
        buffer.write(classname_data)

        padding = (4 - ((total_length + 1) % 4)) % 4
        buffer.write(b'\x00' * padding)

    def _read_classname(self, buffer: io.BytesIO) -> str:
        """Read class name from Pascal string format"""
        total_length = struct.unpack('B', buffer.read(1))[0]
        start_pos = buffer.tell()

        parts = []
        while True:
            str_len = struct.unpack('B', buffer.read(1))[0]
            if str_len == 0:
                break
            part = buffer.read(str_len).decode('utf-8')
            parts.append(part)

        current_pos = buffer.tell()
        bytes_read = current_pos - start_pos
        padding = (4 - ((bytes_read + 1) % 4)) % 4
        buffer.read(padding)

        return '\\'.join(parts)


# ==================== EJEMPLO DE USO ====================

# Definir jerarquía de clases

class Actor(LVObject):
    """Clase Actor - equivalente a Actor.lvclass en LabVIEW"""
    _lv_library = "Actor Framework.lvlib"
    _lv_class = "Actor.lvclass"
    _lv_version = LVClassVersion(1, 0, 0, 7)

    def __init__(self):
        super().__init__()

    def get_private_data(self) -> Optional[Tuple]:
        # Actor no tiene datos privados (usa default)
        return None


class EchoGeneralMsg(Actor):
    """Clase personalizada que hereda de Actor"""
    _lv_library = "Commander.lvlib"
    _lv_class = "echo general Msg.lvclass"
    _lv_version = LVClassVersion(1, 0, 0, 0)

    def __init__(self, message: str = "", flag: int = 0):
        super().__init__()
        self.message = message
        self.flag = flag

    def get_private_data(self) -> Optional[Tuple]:
        """Retorna los datos privados de esta clase"""
        return (self.message, self.flag)

    def set_private_data(self, data: Tuple):
        """Establece los datos privados desde una tupla"""
        self.message, self.flag = data


# Otro ejemplo: tres niveles de herencia

class MyBaseClass(LVObject):
    """Clase base personalizada"""
    _lv_library = "MyLib.lvlib"
    _lv_class = "BaseClass.lvclass"
    _lv_version = LVClassVersion(1, 0, 0, 0)

    def __init__(self, base_value: int = 0):
        super().__init__()
        self.base_value = base_value

    def get_private_data(self) -> Optional[Tuple]:
        return (self.base_value,)

    def set_private_data(self, data: Tuple):
        self.base_value = data[0]


class MyMiddleClass(MyBaseClass):
    """Clase intermedia"""
    _lv_library = "MyLib.lvlib"
    _lv_class = "MiddleClass.lvclass"
    _lv_version = LVClassVersion(1, 0, 0, 1)

    def __init__(self, base_value: int = 0, middle_name: str = ""):
        super().__init__(base_value)
        self.middle_name = middle_name

    def get_private_data(self) -> Optional[Tuple]:
        return (self.middle_name,)

    def set_private_data(self, data: Tuple):
        super().set_private_data(data)  # Won't work for parent, but shows concept
        # In reality, only this level's data is set
        self.middle_name = data[0]


class MyChildClass(MyMiddleClass):
    """Clase hija final"""
    _lv_library = "MyLib.lvlib"
    _lv_class = "ChildClass.lvclass"
    _lv_version = LVClassVersion(1, 0, 0, 2)

    def __init__(self, base_value: int = 0, middle_name: str = "", child_data: List[int] = None):
        super().__init__(base_value, middle_name)
        self.child_data = child_data if child_data is not None else []

    def get_private_data(self) -> Optional[Tuple]:
        return (self.child_data,)

    def set_private_data(self, data: Tuple):
        self.child_data = data[0]


# ==================== TESTS ====================

if __name__ == "__main__":
    print("=== LABVIEW OBJECT-ORIENTED SERIALIZATION ===\n")

    # Test 1: EchoGeneralMsg
    print("1. ECHO GENERAL MSG (Actor hierarchy)")
    msg = EchoGeneralMsg("Testing", 1)

    print(f"   Object: {msg}")
    print(f"   Hierarchy: {[c.__name__ for c in msg.__class__.get_hierarchy()]}")
    print(f"   Num Levels: {msg.__class__.get_num_levels()}")
    print(f"   Qualified Name: {msg.__class__.get_qualified_name()}")
    print(f"   Private Data: {msg.get_private_data()}")

    # Serialize
    serialized = msg.to_bytes()
    print(f"\n   Serialized: {serialized.hex()}")

    expected = "000000022a0f436f6d6d616e6465722e6c766c6962186563686f2067656e6572616c204d73672e6c76636c617373000000010000000500000001000000070000000000000000000d0000000754657374696e670001"
    print(f"   Expected:   {expected}")
    print(f"   Match: {serialized.hex() == expected}\n")

    # Deserialize
    msg2 = EchoGeneralMsg.from_bytes(serialized)
    print(f"   Deserialized:")
    print(f"   Message: {msg2.message}")
    print(f"   Flag: {msg2.flag}")
    print(f"   Match: {msg.message == msg2.message and msg.flag == msg2.flag}\n")

    # Test 2: Jerarquía de 3 niveles
    print("2. THREE-LEVEL HIERARCHY")
    child = MyChildClass(base_value=42, middle_name="Middle", child_data=[1, 2, 3])

    print(f"   Object: {child}")
    print(f"   Hierarchy: {[c.__name__ for c in child.__class__.get_hierarchy()]}")
    print(f"   Num Levels: {child.__class__.get_num_levels()}")

    # Serialize
    serialized = child.to_bytes()
    print(f"\n   Serialized: {serialized.hex()}")

    # Deserialize
    child2 = MyChildClass.from_bytes(serialized)
    print(f"\n   Deserialized:")
    print(f"   Child Data: {child2.child_data}")
    print(f"   Match: {child.child_data == child2.child_data}\n")

    print("=== USAGE SUMMARY ===")
    print("1. Define your class hierarchy:")
    print("   class MyClass(ParentClass):")
    print("       _lv_library = 'MyLib.lvlib'")
    print("       _lv_class = 'MyClass.lvclass'")
    print("       _lv_version = LVClassVersion(1, 0, 0, 0)")
    print("")
    print("2. Implement get_private_data() and set_private_data()")
    print("")
    print("3. Use:")
    print("   obj = MyClass()")
    print("   data = obj.to_bytes()  # Serialize")
    print("   obj2 = MyClass.from_bytes(data)  # Deserialize")
