# Inputs/outputs are serialized protobufs
# (InferGraphTypesRequest and InferGraphTypesResponse)
def infer_graph_types(req: bytes) -> bytes: ...

# Outputs are serialized protobufs
# List of FunctionDeclaration
def builtin_namespace() -> list[bytes]: ...
