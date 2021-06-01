import tierkreis.core.protos.tierkreis.graph as pg
from typing import Union, Dict, Tuple, List
import betterproto

Value = Union[int, bool, pg.Graph, Tuple, List]

def encode_values(values: Dict[str, Value]) -> Dict[str, pg.Value]:
    """
    Encode a dict of python values into their protobuf representations.
    """
    return { name: encode_value(value) for [name, value] in values.items() }

def encode_value(value: Value) -> pg.Value:
    """
    Encode a python value into its protobuf representation.
    """
    if isinstance(value, pg.Graph):
        return value
    elif isinstance(value, int):
        return pg.Value(integer = value)
    elif isinstance(value, bool):
        return pg.Value(boolean = value)
    elif isinstance(value, Tuple):
        first = encode_value(value[0])
        second = encode_value(value[1])
        pair = pg.PairValue(first = first, second = second)
        return pg.Value(pair = pair)
    elif isinstance(value, list):
        elements = [encode_value(item) for item in value]
        array = pg.ArrayValue(array = elements)
        return pg.Value(array = array)
    # TODO: Circuit
    else:
        raise ValueError(f"Value can not be encoded: {value}")

def decode_values(values: Dict[str, pg.Value]) -> Dict[str, Value]:
    """
    Decode a dict of python values from their protobuf representations.
    """
    return { name: decode_value(value) for [name, value] in values.items() }

def decode_value(value: pg.Value) -> Value:
    """
    Decode a value from its protobuf representation.
    """
    [name, value] = betterproto.which_one_of(value, "value")

    if name == "graph":
        return value
    elif name == "integer":
        return value
    elif name == "boolean":
        return value
    elif name == "pair":
        first = decode_value(value.first)
        second = decode_value(value.second)
        return Tuple(first, second)
    elif name == "array":
        return [decode_value(element) for element in value.array]
    # TODO: Circuit
    else:
        raise ValueError(f"Unknown value type: {name}")
