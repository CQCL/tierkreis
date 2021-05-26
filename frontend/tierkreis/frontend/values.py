from typing import Optional, Union, Dict, Tuple, List, IO, Type
from .graph_pb2 import (  # type: ignore
    Graph,
    TypeDataWithPort,
    ValueMap,
    Value,
    TypeData,
    Type as ProtoType,
)
import json
from pytket import Circuit

PyValues = Union[int, bool, Graph, Tuple, List, Circuit]
PyValMap = Dict[str, PyValues]

# map for simple types
valtype_map = {
    int: "integer",
    bool: "boolean",
}


class GraphIOType(Type):
    pass


fixed_type_map = {
    int: ProtoType.TYPE_INT,
    bool: ProtoType.TYPE_BOOL,
    Circuit: ProtoType.TYPE_CIRCUIT,
}


def write_value(proto_val: Value, val: PyValues):
    if type(val) in valtype_map:
        setattr(proto_val, valtype_map[type(val)], val)

    elif isinstance(val, Graph):
        proto_val.graph.CopyFrom(val)
    elif isinstance(val, Tuple):
        write_value(proto_val.pair.first, val[0])
        write_value(proto_val.pair.second, val[1])

    elif isinstance(val, List):
        for py_v in val:
            proto_v = Value()
            write_value(proto_v, py_v)
            proto_val.array.array.append(proto_v)

    elif isinstance(val, Circuit):
        proto_val.circuit = json.dumps(val.to_dict())
    else:
        raise ValueError(f"Type of value not supported for value: {val}")


def convert_oneof_value(val: Value) -> PyValues:
    type_contained = val.WhichOneof("value")
    if type_contained in valtype_map.values():
        return getattr(val, type_contained)

    elif type_contained == "pair":
        return (
            convert_oneof_value(val.pair.first),
            convert_oneof_value(val.pair.second),
        )

    elif type_contained == "array":
        return [convert_oneof_value(elem) for elem in val.array.array]
    elif type_contained == "circuit":
        return Circuit.from_dict(json.loads(val.circuit))
    else:
        raise ValueError(f"Type of value not supported for type: {type_contained}")


def valmap_to_proto(valmap: PyValMap, proto_map: ValueMap):
    for key, val in valmap.items():
        write_value(proto_map.map[key], val)


def proto_to_valmap(proto_map: ValueMap) -> PyValMap:
    return {key: convert_oneof_value(val) for key, val in proto_map.map.items()}


def write_vals_to_file(vals: PyValMap, fp: IO[bytes]):
    new_valmap = ValueMap()
    valmap_to_proto(vals, new_valmap)
    fp.write(new_valmap.SerializeToString())


def read_vals_from_file(fp: IO[bytes]) -> PyValMap:
    new_valmap = ValueMap()
    new_valmap.ParseFromString(fp.read())
    return proto_to_valmap(new_valmap)


def gen_typedata(pytyp: Type, name: Optional[str] = None) -> TypeDataWithPort:
    out = TypeDataWithPort()
    if name:
        out.port = name
    out.type_data.CopyFrom(from_python_type(pytyp))
    return out


def from_python_type(typ: Type) -> TypeData:
    typdat = TypeData()
    if typ in fixed_type_map:
        typdat.type = fixed_type_map[typ]

    elif hasattr(typ, "__name__"):
        if typ.__name__ == "ProtoGraphBuilder":
            typdat.type = ProtoType.TYPE_GRAPH
            for incoming, proto in zip(
                (typ.inputs.items(), typ.ouputs.items()),
                (typdat.input_types, typdat.output_types),
            ):
                proto.extend([gen_typedata(pytyp, name) for name, pytyp in incoming])

    elif hasattr(typ, "_name"):
        if typ._name == "Tuple":
            typdat.type = ProtoType.TYPE_PAIR
            assert len(typdat.__args__) == 2
            typdat.input_types.extend((gen_typedata(arg) for arg in typ.__args__))
        elif typ._name == "List":
            typdat.type = ProtoType.TYPE_ARRAY
            typdat.input_types.append(gen_typedata(typ.__args__[0]))

    if typdat.type == 0 and typ != int:
        raise ValueError(f"{typ} is not supported for conversion.")

    return typdat
