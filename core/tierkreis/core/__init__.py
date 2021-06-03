import json
import tierkreis.core.protos.tierkreis.graph as pg
from typing import Optional, Union, Dict, Tuple, List, cast, Type
import betterproto
from pytket.circuit import Circuit  # type: ignore

Value = Union[int, bool, pg.Graph, Tuple, List]
PyValMap = Dict[str, Value]

# map for simple types
valtype_map = {
    int: "integer",
    bool: "boolean",
}


class GraphIOType(Type):
    pass


fixed_type_map = {
    int: pg.Type.TYPE_INT,
    bool: pg.Type.TYPE_BOOL,
    Circuit: pg.Type.TYPE_CIRCUIT,
}


def encode_values(values: PyValMap) -> Dict[str, pg.Value]:
    """
    Encode a dict of python values into their protobuf representations.
    """
    return {name: encode_value(value) for name, value in values.items()}


def encode_value(value: Value) -> pg.Value:
    """
    Encode a python value into its protobuf representation.
    """
    if isinstance(value, pg.Graph):
        return pg.Value(graph=value)
    elif isinstance(value, bool):
        return pg.Value(boolean=value)
    elif isinstance(value, int):
        return pg.Value(integer=value)
    elif isinstance(value, Tuple):
        first = encode_value(value[0])
        second = encode_value(value[1])
        pair = pg.PairValue(first=first, second=second)
        return pg.Value(pair=pair)
    elif isinstance(value, list):
        elements = [encode_value(item) for item in value]
        array = pg.ArrayValue(array=elements)
        return pg.Value(array=array)
    elif isinstance(value, Circuit):
        return pg.Value(circuit=json.dumps(value.to_dict()))
    else:
        raise ValueError(f"Value can not be encoded: {value}")


def decode_values(values: Dict[str, pg.Value]) -> PyValMap:
    """
    Decode a dict of python values from their protobuf representations.
    """
    return {name: decode_value(value) for name, value in values.items()}


def decode_value(value: pg.Value) -> Value:
    """
    Decode a value from its protobuf representation.
    """
    name, out_value = betterproto.which_one_of(value, "value")

    if name == "graph":
        return cast(pg.Graph, out_value)
    elif name == "integer":
        return cast(int, out_value)
    elif name == "boolean":
        return cast(bool, out_value)
    elif name == "pair":
        pair = cast(pg.PairValue, out_value)
        first = decode_value(out_value.first)
        second = decode_value(out_value.second)
        return (first, second)
    elif name == "array":
        return [
            decode_value(element) for element in cast(pg.ArrayValue, out_value).array
        ]
    elif name == "circuit":
        return Circuit.from_dict(json.loads(cast(str, out_value)))
    else:
        raise ValueError(f"Unknown value type: {name}")


def gen_typedata(pytyp: Type, name: Optional[str] = None) -> pg.TypeDataWithPort:
    out = pg.TypeDataWithPort()
    if name:
        out.port = name
    out.type_data = from_python_type(pytyp)
    return out


def from_python_type(typ: Type) -> pg.TypeData:
    typdat = pg.TypeData()
    if typ in fixed_type_map:
        typdat.type = fixed_type_map[typ]

    elif hasattr(typ, "__name__"):
        if typ.__name__ == "ProtoGraphBuilder":
            typdat.type = pg.Type.TYPE_GRAPH
            for incoming, proto in zip(
                (typ.inputs.items(), typ.ouputs.items()),
                (typdat.input_types, typdat.output_types),
            ):
                proto.extend([gen_typedata(pytyp, name) for name, pytyp in incoming])

    elif hasattr(typ, "_name"):
        if typ._name == "Tuple":
            typdat.type = pg.Type.TYPE_PAIR
            assert len(typdat.__args__) == 2
            typdat.input_types.extend((gen_typedata(arg) for arg in typ.__args__))
        elif typ._name == "List":
            typdat.type = pg.Type.TYPE_ARRAY
            typdat.input_types.append(gen_typedata(typ.__args__[0]))

    if typdat.type == 0 and typ != int:
        raise ValueError(f"{typ} is not supported for conversion.")

    return typdat
