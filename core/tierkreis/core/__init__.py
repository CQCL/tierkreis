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


def from_python_type(typ: Type) -> pg.Type:
    if typ == int:
        return pg.Type(int = pg.Empty())
    elif typ == bool:
        return pg.Type(bool = pg.Empty())
    elif typ == Circuit:
        return pg.Type(circuit = pg.Empty())
    elif hasattr(typ, "__name__") and typ.__name__ == "ProtoGraphBuilder":
        inputs = pg.RowType(content={
            port_name: from_python_type(port_type)
            for port_name, port_type in typ.inputs.items()
        })
        outputs = pg.RowType(content={
            port_name: from_python_type(port_type)
            for port_name, port_type in typ.outputs.items()
        })
        graph_type = pg.GraphType(inputs=inputs, outputs=outputs)
        return pg.Type(graph=graph_type)

    elif hasattr(typ, "_name"):
        if typ._name == "Tuple":
            assert len(typ.__args__) == 2
            first = from_python_type(typ.__args__[0])
            second = from_python_type(typ.__args__[1])
            pair = pg.PairType(first=first, second=second)
            return pg.Type(pair=pair)
        elif typ._name == "List":
            assert len(typ.__args__) == 1
            element = from_python_type(typ.__args__[0])
            return pg.Type(array=element)
    else:
        pass

    raise ValueError(f"{typ} is not supported for conversion.")
