# -*- coding: utf-8 -*-

""" LabView Data Serialization - Numpy Integration

    Flatten to string and unflatten from string compatible with LabVIEW.
    Uses numpy types for precise type control, auto-detection otherwise.
"""

import struct
import io
from typing import Any, List, Union

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None


class LVSerializer:
    """
    LabVIEW data serializer/deserializer - Numpy integration.

    Auto-detects types from Python values:
    - 42 -> I32
    - 3.14 -> DBL
    - "text" -> String
    - [1, 2, 3] -> Array of I32
    - (42, 3.14, "test") -> Cluster(I32, DBL, String)

    Use numpy types for precise control:
    - np.int16(42) -> I16
    - np.int8(42) -> I8
    - np.float32(3.14) -> SGL
    - np.uint16(42) -> U16
    """

    def __init__(self, endian='big'):
        """
        Initialize serializer.

        Args:
            endian: Byte order ('big' for LabVIEW standard)
        """
        self.endian = '>' if endian == 'big' else '<'
        if not HAS_NUMPY:
            print("Warning: numpy not available. Numpy type support disabled.")

    # ==================== FLATTEN ====================

    def flatten(self, value: Any) -> bytes:
        """
        Flatten Python value to LabVIEW binary format.

        Args:
            value: Python value to flatten

        Returns:
            Flattened bytes (LabVIEW compatible)
        """
        buffer = io.BytesIO()
        self._flatten_value(buffer, value)
        return buffer.getvalue()

    def _flatten_value(self, buffer: io.BytesIO, value: Any):
        """Flatten a value with numpy type detection"""

        # Numpy types (precise control)
        if HAS_NUMPY and hasattr(value, 'dtype'):
            dtype = value.dtype

            if dtype == np.int8:
                buffer.write(struct.pack(f'{self.endian}b', value.item() if hasattr(value, 'item') else int(value)))
            elif dtype == np.int16:
                buffer.write(struct.pack(f'{self.endian}h', value.item() if hasattr(value, 'item') else int(value)))
            elif dtype == np.int32:
                buffer.write(struct.pack(f'{self.endian}i', value.item() if hasattr(value, 'item') else int(value)))
            elif dtype == np.int64:
                buffer.write(struct.pack(f'{self.endian}q', value.item() if hasattr(value, 'item') else int(value)))
            elif dtype == np.uint8:
                buffer.write(struct.pack(f'{self.endian}B', value.item() if hasattr(value, 'item') else int(value)))
            elif dtype == np.uint16:
                buffer.write(struct.pack(f'{self.endian}H', value.item() if hasattr(value, 'item') else int(value)))
            elif dtype == np.uint32:
                buffer.write(struct.pack(f'{self.endian}I', value.item() if hasattr(value, 'item') else int(value)))
            elif dtype == np.uint64:
                buffer.write(struct.pack(f'{self.endian}Q', value.item() if hasattr(value, 'item') else int(value)))
            elif dtype == np.float32:
                buffer.write(struct.pack(f'{self.endian}f', value.item() if hasattr(value, 'item') else float(value)))
            elif dtype == np.float64:
                buffer.write(struct.pack(f'{self.endian}d', value.item() if hasattr(value, 'item') else float(value)))
            else:
                raise ValueError(f"Unsupported numpy dtype: {dtype}")
            return

        # Auto-detected types
        elif isinstance(value, bool):
            buffer.write(struct.pack(f'{self.endian}B', 1 if value else 0))
        elif isinstance(value, int):
            # Default to I32 for most integers
            if -2147483648 <= value <= 2147483647:
                buffer.write(struct.pack(f'{self.endian}i', value))
            else:
                buffer.write(struct.pack(f'{self.endian}q', value))
        elif isinstance(value, float):
            buffer.write(struct.pack(f'{self.endian}d', value))
        elif isinstance(value, (str, bytes)):
            val = value
            if isinstance(val, str):
                val = val.encode('utf-8')
            buffer.write(struct.pack(f'{self.endian}I', len(val)))
            buffer.write(val)
        elif isinstance(value, (list, tuple)):
            if not value:
                # Empty list -> Array of I32 with 0 elements
                buffer.write(struct.pack(f'{self.endian}I', 0))
            elif self._is_homogeneous_list(value):
                # Homogeneous -> Array
                buffer.write(struct.pack(f'{self.endian}I', len(value)))
                for elem in value:
                    self._flatten_value(buffer, elem)
            else:
                # Heterogeneous tuple -> Cluster
                for elem in value:
                    self._flatten_value(buffer, elem)
        else:
            raise ValueError(f"Unsupported type: {type(value)}")

    def _is_homogeneous_list(self, value: Union[list, tuple]) -> bool:
        """Check if all elements in list/tuple are of the same type structure"""
        if not value:
            return True

        first_type = type(value[0])

        # For tuples/lists, check deeper structure
        if isinstance(value[0], (tuple, list)):
            first_len = len(value[0])
            first_types = [type(x) for x in value[0]]
            for item in value[1:]:
                if not isinstance(item, (tuple, list)):
                    return False
                if len(item) != first_len:
                    return False
                if [type(x) for x in item] != first_types:
                    return False
            return True

        # For primitive types
        for item in value[1:]:
            if type(item) != first_type:
                return False
        return True

    # ==================== UNFLATTEN ====================

    def unflatten(self, data: Union[bytes, io.BytesIO], template: Any) -> Any:
        """
        Unflatten LabVIEW binary format to Python value.

        Args:
            data: Binary data
            template: A Python value with the same structure as expected output.
                     Can be numpy types or regular Python types.

        Returns:
            Python value

        Examples:
            unflatten(data, 0) -> reads I32
            unflatten(data, np.int16(0)) -> reads I16 (forced)
            unflatten(data, 0.0) -> reads DBL
            unflatten(data, "") -> reads String
            unflatten(data, [0]) -> reads Array of I32
            unflatten(data, (0, 0.0, "")) -> reads Cluster(I32, DBL, String)
        """
        if isinstance(data, bytes):
            buffer = io.BytesIO(data)
        else:
            buffer = data

        return self._unflatten_value(buffer, template)

    def _unflatten_value(self, buffer: io.BytesIO, template: Any) -> Any:
        """Unflatten a value based on template structure"""

        # Numpy type templates
        if HAS_NUMPY and hasattr(template, 'dtype'):
            dtype = template.dtype

            if dtype == np.int8:
                return np.int8(struct.unpack(f'{self.endian}b', buffer.read(1))[0])
            elif dtype == np.int16:
                return np.int16(struct.unpack(f'{self.endian}h', buffer.read(2))[0])
            elif dtype == np.int32:
                return np.int32(struct.unpack(f'{self.endian}i', buffer.read(4))[0])
            elif dtype == np.int64:
                return np.int64(struct.unpack(f'{self.endian}q', buffer.read(8))[0])
            elif dtype == np.uint8:
                return np.uint8(struct.unpack(f'{self.endian}B', buffer.read(1))[0])
            elif dtype == np.uint16:
                return np.uint16(struct.unpack(f'{self.endian}H', buffer.read(2))[0])
            elif dtype == np.uint32:
                return np.uint32(struct.unpack(f'{self.endian}I', buffer.read(4))[0])
            elif dtype == np.uint64:
                return np.uint64(struct.unpack(f'{self.endian}Q', buffer.read(8))[0])
            elif dtype == np.float32:
                return np.float32(struct.unpack(f'{self.endian}f', buffer.read(4))[0])
            elif dtype == np.float64:
                return np.float64(struct.unpack(f'{self.endian}d', buffer.read(8))[0])
            else:
                raise ValueError(f"Unsupported numpy dtype: {dtype}")

        # Auto-detected templates
        elif isinstance(template, bool):
            return struct.unpack(f'{self.endian}B', buffer.read(1))[0] != 0
        elif isinstance(template, int):
            # Default to I32
            if -2147483648 <= template <= 2147483647 or template == 0:
                return struct.unpack(f'{self.endian}i', buffer.read(4))[0]
            else:
                return struct.unpack(f'{self.endian}q', buffer.read(8))[0]
        elif isinstance(template, float):
            return struct.unpack(f'{self.endian}d', buffer.read(8))[0]
        elif isinstance(template, (str, bytes)):
            length = struct.unpack(f'{self.endian}I', buffer.read(4))[0]
            data = buffer.read(length)
            return data.decode('utf-8') if isinstance(template, str) else data
        elif isinstance(template, (list, tuple)):
            if not template:
                # Empty template -> read as empty array
                length = struct.unpack(f'{self.endian}I', buffer.read(4))[0]
                return []
            elif len(template) == 1:
                # Single element template -> Array
                length = struct.unpack(f'{self.endian}I', buffer.read(4))[0]
                result = []
                for _ in range(length):
                    result.append(self._unflatten_value(buffer, template[0]))
                return result if isinstance(template, list) else tuple(result)
            else:
                # Multiple elements -> Cluster
                result = []
                for elem_template in template:
                    result.append(self._unflatten_value(buffer, elem_template))
                return result if isinstance(template, list) else tuple(result)
        else:
            raise ValueError(f"Unsupported template type: {type(template)}")


# ==================== EJEMPLOS DE USO ====================

if __name__ == "__main__":
    serializer = LVSerializer()

    print("=== LABVIEW AUTO-DETECTION WITH TEMPLATES ===\n")

    # Ejemplo 1: Integer
    print("1. INTEGER (I32)")
    value = 42
    flattened = serializer.flatten(value)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")
    print(f"   Expected:  0000002a")

    # Unflatten usando template (cualquier int sirve como template)
    unflattened = serializer.unflatten(flattened, 0)
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {value == unflattened}\n")

    # Ejemplo 2: Float
    print("2. FLOAT (DBL)")
    value = 3.14
    flattened = serializer.flatten(value)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")

    # Template: cualquier float
    unflattened = serializer.unflatten(flattened, 0.0)
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {abs(value - unflattened) < 0.0001}\n")

    # Ejemplo 3: String
    print("3. STRING")
    value = "test"
    flattened = serializer.flatten(value)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")
    print(f"   Expected:  0000000474657374")

    # Template: cualquier string
    unflattened = serializer.unflatten(flattened, "")
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {value == unflattened}\n")

    # Ejemplo 4: Array de enteros
    print("4. ARRAY OF I32")
    value = [1, 2, 3, 4, 5]
    flattened = serializer.flatten(value)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")

    # Template: lista con un elemento del tipo esperado
    unflattened = serializer.unflatten(flattened, [0])
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {value == unflattened}\n")

    # Ejemplo 5: Cluster (I32, DBL, String) - USANDO TUPLA
    print("5. CLUSTER (I32, DBL, String) - TUPLE")
    value = (42, 3.14, "test")
    flattened = serializer.flatten(value)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")
    print(f"   Expected:  0000002a40091eb851eb851f0000000474657374")

    # Template: tupla con tipos esperados (valores no importan)
    unflattened = serializer.unflatten(flattened, (0, 0.0, ""))
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {value == unflattened}\n")

    # Ejemplo 6: Array de Clusters
    print("6. ARRAY OF CLUSTERS")
    value = [
        (1, "first"),
        (2, "second"),
        (3, "third")
    ]
    flattened = serializer.flatten(value)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")

    # Template: lista con UN elemento que es un cluster
    unflattened = serializer.unflatten(flattened, [(0, "")])
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {value == unflattened}\n")

    # Ejemplo 7: Nested complex structure
    print("7. COMPLEX NESTED STRUCTURE")
    value = [
        (1, 2.5, ["a", "b"]),
        (2, 3.7, ["c", "d", "e"]),
    ]
    flattened = serializer.flatten(value)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")

    # Template: estructura con un elemento de cada tipo
    template = [(0, 0.0, [""])]
    unflattened = serializer.unflatten(flattened, template)
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {value == unflattened}\n")

    # Ejemplo 8: Verificación con valor esperado
    print("8. VERIFICATION - Cluster from expected")
    expected_hex = "0000002a40091eb851eb851f0000000474657374"
    expected_bytes = bytes.fromhex(expected_hex)

    # Unflatten usando template
    result = serializer.unflatten(expected_bytes, (0, 0.0, ""))
    print(f"   Input hex: {expected_hex}")
    print(f"   Unflattened: {result}")

    # Flatten again
    reflattened = serializer.flatten(result)
    print(f"   Re-flattened: {reflattened.hex()}")
    print(f"   Match: {expected_hex == reflattened.hex()}\n")

    # Ejemplo 9: Comparación con formato anterior
    print("9. COMPARISON - Dict vs Tuple")

    # Opción A: Tupla (más simple)
    value_tuple = (42, 3.14, "test")
    flat_tuple = serializer.flatten(value_tuple)
    print(f"   Tuple: {value_tuple}")
    print(f"   Flattened: {flat_tuple.hex()}")
    unflatten_tuple = serializer.unflatten(flat_tuple, (0, 0.0, ""))
    print(f"   Unflattened: {unflatten_tuple}")

    print(f"\n   Both produce same binary: {flat_tuple.hex()}\n")

    # Ejemplo 10: Boolean
    print("10. BOOLEAN")
    value = True
    flattened = serializer.flatten(value)
    print(f"   Original: {value}")
    print(f"   Flattened: {flattened.hex()}")

    unflattened = serializer.unflatten(flattened, False)
    print(f"   Unflattened: {unflattened}")
    print(f"   Match: {value == unflattened}\n")

    value = ("Hello World!", np.uint16(0))
    flattened = serializer.flatten(value)
    print(flattened.hex())

    data = bytes.fromhex("0000 0008 5465 7374 696E 6767 0001")
    print(data.hex())
    unflattened = serializer.unflatten(data, value)
    print(unflattened)