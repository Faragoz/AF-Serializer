from protobuf.types import ClusterData  # Asumiendo que importas el mensaje generado

# Crear objeto Python
data = {"name": "sensor", "value": 42, "array": [1.0, 2.0, 3.0]}

# Serializar a Protobuf
cluster = ClusterData(**data)
serialized = cluster.SerializeToString()  # Bytes para enviar vía TCP

# Deserializar
received = ClusterData()
received.ParseFromString(serialized)
print(received.name)  # "sensor"