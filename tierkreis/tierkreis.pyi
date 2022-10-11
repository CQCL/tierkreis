# Inputs/outputs are serialized protobufs
# (InferGraphTypesRequest and InferGraphTypesResponse)
def infer_graph_types(req: bytes) -> bytes: ...

# Output is serialized protobuf
# Namespace
def builtin_namespace() -> bytes: ...
