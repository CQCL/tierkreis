from dataclasses import asdict, dataclass, is_dataclass, make_dataclass
import json
import tierkreis.core.protos.tierkreis.graph as pg
from typing import Optional, Union, Dict, Tuple, List, cast, Type, TypeVar
import betterproto
from pytket.circuit import Circuit  # type: ignore


Value = Union[
    int,
    bool,
    str,
    float,
    pg.Graph,
    Tuple["Value", "Value"],
    List["Value"],
    Dict["Value", "Value"],
]
PyValMap = Dict[str, Value]


class TKStructTypeError(Exception):
    pass


@dataclass(eq=False, frozen=True)
class TKStruct:
    def __eq__(self, o: object) -> bool:
        if not isinstance(o, TKStruct):
            return False
        return asdict(self) == asdict(o)


# map for simple types
valtype_map = {
    int: "integer",
    bool: "boolean",
    str: "str_",
    float: "flt",
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
    elif type(value) in valtype_map:
        return pg.Value(**{valtype_map[type(value)]: value})
    elif isinstance(value, Tuple):
        first = encode_value(value[0])
        second = encode_value(value[1])
        pair = pg.PairValue(first=first, second=second)
        return pg.Value(pair=pair)
    elif isinstance(value, list):
        elements = [encode_value(item) for item in value]
        array = pg.ArrayValue(array=elements)
        return pg.Value(array=array)
    elif isinstance(value, Dict):
        pgmap = pg.MapValue(
            [
                pg.PairValue(first=encode_value(k), second=encode_value(v))
                for k, v in value.items()
            ]
        )
        return pg.Value(map=pgmap)
    elif isinstance(value, Circuit):
        return pg.Value(circuit=json.dumps(cast(Circuit, value).to_dict()))
    elif isinstance(value, TKStruct):
        # TODO preserve class name as alias for structural type
        pgstruc = pg.StructValue(
            map={
                field: encode_value(value.__getattribute__(field))
                for field in value.__annotations__.keys()
            },
        )
        return pg.Value(struct=pgstruc)
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
    elif name == "str_":
        return cast(str, out_value)
    elif name == "flt":
        return cast(float, out_value)
    elif name == "pair":
        pair = cast(pg.PairValue, out_value)
        first = decode_value(pair.first)
        second = decode_value(pair.second)
        return (first, second)
    elif name == "array":
        return [
            decode_value(element) for element in cast(pg.ArrayValue, out_value).array
        ]
    elif name == "map":
        return {
            decode_value(pair.first): decode_value(pair.second)
            for pair in cast(pg.MapValue, out_value).pairs
        }
    elif name == "circuit":
        return Circuit.from_dict(json.loads(cast(str, out_value)))
    elif name == "struct":
        pgstruct = cast(pg.StructValue, out_value)
        decoded_fields = decode_values(pgstruct.map)
        # TODO when original struct name is preserved as an alias name
        # use that as the name of the dataclass here.
        cls = make_dataclass(
            "TKStruct",
            fields=[(key, type(val)) for key, val in decoded_fields.items()],
            bases=(TKStruct,),
            eq=False,
        )
        return cls(**decode_values(pgstruct.map))
    else:
        raise ValueError(f"Unknown value type: {name}")


def from_python_type(typ: Type) -> pg.Type:
    if typ == int:
        return pg.Type(int=pg.Empty())
    elif typ == bool:
        return pg.Type(bool=pg.Empty())
    elif typ == str:
        return pg.Type(str_=pg.Empty())
    elif typ == Circuit:
        return pg.Type(circuit=pg.Empty())
    elif typ == float:
        return pg.Type(flt=pg.Empty())
    elif hasattr(typ, "__name__") and typ.__name__ == "ProtoGraphBuilder":
        inputs = pg.RowType(
            content={
                port_name: from_python_type(port_type)
                for port_name, port_type in typ.inputs.items()
            }
        )
        outputs = pg.RowType(
            content={
                port_name: from_python_type(port_type)
                for port_name, port_type in typ.outputs.items()
            }
        )
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
        elif typ._name == "Dict":
            assert len(typ.__args__) == 2
            first = from_python_type(typ.__args__[0])
            second = from_python_type(typ.__args__[1])
            pair = pg.PairType(first=first, second=second)
            return pg.Type(
                map=pair,
            )
    else:
        pass

    raise ValueError(f"{typ} is not supported for conversion.")
