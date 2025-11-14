# -*- coding: utf-8 -*-

""" LabView Data Serialization - Standard Format

    Flatten to string and unflatten from string compatible with LabVIEW.
    NO type markers - requires type definition for unflatten.
"""

import struct
import io
from enum import IntEnum
from typing import Any, List, Dict, Union, Tuple, Optional


class LVDataType(IntEnum):
    """LabVIEW data types"""
    INT8 = 1
    INT16 = 2
    INT32 = 3
    INT64 = 4
    UINT8 = 5
    UINT16 = 6
    UINT32 = 7
    UINT64 = 8
    FLOAT32 = 9
    FLOAT64 = 10
    BOOLEAN = 11
    STRING = 12
    ARRAY = 13
    CLUSTER = 14


class TypeDef:
    """Type definition for LabVIEW data structures"""

    def __init__(self, base_type: LVDataType, **kwargs):
        self.base_type = base_type
        self.element_type = kwargs.get('element_type')  # For arrays
        self.fields = kwargs.get('fields', [])  # For clusters: list of TypeDef


class LVSerializer:
    """
    LabVIEW data serializer/deserializer - Standard LabVIEW format.
    Compatible with LabVIEW Flatten to String / Unflatten from String.
    """

    def __init__(self, endian='big'):
        """
        Initialize serializer.

        Args:
            endian: Byte order ('big' for LabVIEW standard)
        """
        self.endian = '>' if endian == 'big' else '<'

    # ==================== FLATTEN (Python -> LabVIEW bytes) ====================

    def flatten(self, value: Any, type_def: Optional[TypeDef] = None) -> bytes:
        """
        Flatten Python value to LabVIEW binary format.

        Args:
            value: Python value to flatten
            type_def: Type definition (optional, will auto-detect if not provided)

        Returns:
            Flattened bytes (LabVIEW compatible)
        """
        # Auto-detect type if not provided
        if type_def is None:
            type_def = self._auto_detect_type(value)

        buffer = io.BytesIO()
        self._flatten_value(buffer, value, type_def)
        return buffer.getvalue()

    def _auto_detect_type(self, value: Any) -> TypeDef:
        """Auto-detect type definition from Python value"""
        if isinstance(value, bool):
            return TypeDef(LVDataType.BOOLEAN)
        elif isinstance(value, int):
            if -2147483648 <= value <= 2147483647:
                return TypeDef(LVDataType.INT32)
            else:
                return TypeDef(LVDataType.INT64)
        elif isinstance(value, float):
            return TypeDef(LVDataType.FLOAT64)
        elif isinstance(value, (str, bytes)):
            return TypeDef(LVDataType.STRING)
        elif isinstance(value, (list, tuple)):
            if not value:
                elem_type = TypeDef(LVDataType.INT32)
            else:
                elem_type = self._auto_detect_type(value[0])
            return TypeDef(LVDataType.ARRAY, element_type=elem_type)
        elif isinstance(value, dict):
            fields = []
            for key in sorted(value.keys()):
                fields.append(self._auto_detect_type(value[key]))
            return TypeDef(LVDataType.CLUSTER, fields=fields)
        else:
            raise ValueError(f"Cannot auto-detect type for: {type(value)}")

    def _flatten_value(self, buffer: io.BytesIO, value: Any, type_def: TypeDef):
        """Flatten a value based on its type definition"""
        dtype = type_def.base_type

        if dtype == LVDataType.INT8:
            buffer.write(struct.pack(f'{self.endian}b', value))
        elif dtype == LVDataType.INT16:
            buffer.write(struct.pack(f'{self.endian}h', value))
        elif dtype == LVDataType.INT32:
            buffer.write(struct.pack(f'{self.endian}i', value))
        elif dtype == LVDataType.INT64:
            buffer.write(struct.pack(f'{self.endian}q', value))
        elif dtype == LVDataType.UINT8:
            buffer.write(struct.pack(f'{self.endian}B', value))
        elif dtype == LVDataType.UINT16:
            buffer.write(struct.pack(f'{self.endian}H', value))
        elif dtype == LVDataType.UINT32:
            buffer.write(struct.pack(f'{self.endian}I', value))
        elif dtype == LVDataType.UINT64:
            buffer.write(struct.pack(f'{self.endian}Q', value))
        elif dtype == LVDataType.FLOAT32:
            buffer.write(struct.pack(f'{self.endian}f', value))
        elif dtype == LVDataType.FLOAT64:
            buffer.write(struct.pack(f'{self.endian}d', value))
        elif dtype == LVDataType.BOOLEAN:
            buffer.write(struct.pack(f'{self.endian}B', 1 if value else 0))
        elif dtype == LVDataType.STRING:
            if isinstance(value, str):
                value = value.encode('utf-8')
            buffer.write(struct.pack(f'{self.endian}I', len(value)))
            buffer.write(value)
        elif dtype == LVDataType.ARRAY:
            # Array: dimension + elements
            buffer.write(struct.pack(f'{self.endian}I', len(value)))
            for elem in value:
                self._flatten_value(buffer, elem, type_def.element_type)
        elif dtype == LVDataType.CLUSTER:
            # Cluster: just the fields in order (NO count, NO type markers)
            for i, field_type in enumerate(type_def.fields):
                if isinstance(value, dict):
                    field_value = value.get(i, value.get(str(i)))
                else:
                    field_value = value[i]
                self._flatten_value(buffer, field_value, field_type)
        else:
            raise ValueError(f"Unsupported type: {dtype}")

    # ==================== UNFLATTEN (LabVIEW bytes -> Python) ====================

    def unflatten(self, data: Union[bytes, io.BytesIO], type_def: TypeDef) -> Any:
        """
        Unflatten LabVIEW binary format to Python value.

        Args:
            data: Binary data
            type_def: Type definition (REQUIRED for unflatten)

        Returns:
            Python value
        """
        if isinstance(data, bytes):
            buffer = io.BytesIO(data)
        else:
            buffer = data

        return self._unflatten_value(buffer, type_def)

    def _unflatten_value(self, buffer: io.BytesIO, type_def: TypeDef) -> Any:
        """Unflatten a value based on its type definition"""
        dtype = type_def.base_type

        if dtype == LVDataType.INT8:
            return struct.unpack(f'{self.endian}b', buffer.read(1))[0]
        elif dtype == LVDataType.INT16:
            return struct.unpack(f'{self.endian}h', buffer.read(2))[0]
        elif dtype == LVDataType.INT32:
            return struct.unpack(f'{self.endian}i', buffer.read(4))[0]
        elif dtype == LVDataType.INT64:
            return struct.unpack(f'{self.endian}q', buffer.read(8))[0]
        elif dtype == LVDataType.UINT8:
            return struct.unpack(f'{self.endian}B', buffer.read(1))[0]
        elif dtype == LVDataType.UINT16:
            return struct.unpack(f'{self.endian}H', buffer.read(2))[0]
        elif dtype == LVDataType.UINT32:
            return struct.unpack(f'{self.endian}I', buffer.read(4))[0]
        elif dtype == LVDataType.UINT64:
            return struct.unpack(f'{self.endian}Q', buffer.read(8))[0]
        elif dtype == LVDataType.FLOAT32:
            return struct.unpack(f'{self.endian}f', buffer.read(4))[0]
        elif dtype == LVDataType.FLOAT64:
            return struct.unpack(f'{self.endian}d', buffer.read(8))[0]
        elif dtype == LVDataType.BOOLEAN:
            return struct.unpack(f'{self.endian}B', buffer.read(1))[0] != 0
        elif dtype == LVDataType.STRING:
            length = struct.unpack(f'{self.endian}I', buffer.read(4))[0]
            return buffer.read(length).decode('utf-8')
        elif dtype == LVDataType.ARRAY:
            length = struct.unpack(f'{self.endian}I', buffer.read(4))[0]
            result = []
            for _ in range(length):
                result.append(self._unflatten_value(buffer, type_def.element_type))
            return result
        elif dtype == LVDataType.CLUSTER:
            result = {}
            for i, field_type in enumerate(type_def.fields):
                result[i] = self._unflatten_value(buffer, field_type)
            return result
        else:
            raise ValueError(f"Unsupported type: {dtype}")


# ==================== EJEMPLOS DE USO ====================

if __name__ == "__main__":
    serializer = LVSerializer()

    print("=== LABVIEW STANDARD FORMAT EXAMPLES ===\n")

    # Ejemplo 1: Integer
    print("1. INTEGER (I32)")
    value = 42
    flattened = serializer.flatten(value)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")
    print(f"   Expected:  0000002a")

    # Para unflatten necesitamos el tipo
    type_def = TypeDef(LVDataType.INT32)
    unflattened = serializer.unflatten(flattened, type_def)
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {value == unflattened}\n")

    # Ejemplo 2: Float
    print("2. FLOAT (DBL)")
    value = 3.14
    flattened = serializer.flatten(value)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")

    type_def = TypeDef(LVDataType.FLOAT64)
    unflattened = serializer.unflatten(flattened, type_def)
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {abs(value - unflattened) < 0.0001}\n")

    # Ejemplo 3: String
    print("3. STRING")
    value = "test"
    flattened = serializer.flatten(value)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")
    print(f"   Expected:  0000000474657374")

    type_def = TypeDef(LVDataType.STRING)
    unflattened = serializer.unflatten(flattened, type_def)
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {value == unflattened}\n")

    # Ejemplo 4: Array de enteros
    print("4. ARRAY OF I32")
    value = [1, 2, 3, 4, 5]
    flattened = serializer.flatten(value)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")

    type_def = TypeDef(LVDataType.ARRAY, element_type=TypeDef(LVDataType.INT32))
    unflattened = serializer.unflatten(flattened, type_def)
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {value == unflattened}\n")

    # Ejemplo 5: Cluster (I32, DBL, String)
    print("5. CLUSTER (I32, DBL, String)")
    value = {0: 42, 1: 3.14, 2: "test"}

    # Definir el tipo del cluster
    cluster_type = TypeDef(LVDataType.CLUSTER, fields=[
        TypeDef(LVDataType.INT32),
        TypeDef(LVDataType.FLOAT64),
        TypeDef(LVDataType.STRING)
    ])

    flattened = serializer.flatten(value, cluster_type)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")
    print(f"   Expected:  0000002a40091eb851eb851f0000000474657374")

    unflattened = serializer.unflatten(flattened, cluster_type)
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {value[0] == unflattened[0] and value[2] == unflattened[2]}\n")

    # Ejemplo 6: Nested - Array de Clusters
    print("6. ARRAY OF CLUSTERS")
    value = [
        {0: 1, 1: "first"},
        {0: 2, 1: "second"},
        {0: 3, 1: "third"}
    ]

    cluster_elem_type = TypeDef(LVDataType.CLUSTER, fields=[
        TypeDef(LVDataType.INT32),
        TypeDef(LVDataType.STRING)
    ])
    array_type = TypeDef(LVDataType.ARRAY, element_type=cluster_elem_type)

    flattened = serializer.flatten(value, array_type)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")

    unflattened = serializer.unflatten(flattened, array_type)
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {value == unflattened}\n")

    # Ejemplo 7: Verificación con valor esperado
    print("7. VERIFICATION - Cluster from your example")
    expected_hex = "0000002a40091eb851eb851f0000000474657374"
    expected_bytes = bytes.fromhex(expected_hex)

    # Unflatten
    cluster_type = TypeDef(LVDataType.CLUSTER, fields=[
        TypeDef(LVDataType.INT32),
        TypeDef(LVDataType.FLOAT64),
        TypeDef(LVDataType.STRING)
    ])
    result = serializer.unflatten(expected_bytes, cluster_type)
    print(f"   Input hex: {expected_hex}")
    print(f"   Unflattened: {result}")

    # Flatten again
    reflattened = serializer.flatten(result, cluster_type)
    print(f"   Re-flattened: {reflattened.hex()}")
    print(f"   Match: {expected_hex == reflattened.hex()}\n")