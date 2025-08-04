---
file_format: mystnb
kernelspec:
  name: python3
---

# Complex types in Tierkreis Python workers

In general Tierkreis allows a task to write arbitrary bytes to its output files.
This allows Tierkreis graphs to more easily amalgamate tasks that do not share a common set of type definitions.
(For example a command line tool that defines its own serialization format.)

However workers written using the Tierkreis Python library should use only a specific subset of all the possible classes that the Python language can produce.

This page lists the main types a worker author can use (as inputs or outputs) in their functions.

```{warning}
This page only talks about the types describing a single input or output.
Therefore it does not talk about the `portmapping` decorator used by graph builder code to group together multiple outputs.
Now each of the attributes of a port mapping is itself a single output and so the remarks in this page do apply to the attributes individually.
```

## JSON style types

Any type satisfying the following recursive definition is allowed as an input or output.

```{code-cell}
type Jsonable = (
    bool
    | int
    | float
    | str
    | NoneType
    | list[Jsonable]
    | Sequence[Jsonable]
    | tuple[Jsonable, ...]
    | dict[str, Jsonable]
    | Mapping[str, Jsonable]
)
```

After the stub generation process is run these type appear in graph builder code wrapped in `TKR`.
E.g. `TKR[int]`, `TKR[str]`, `TKR[tuple[dict[str, list[int]], int]]`.

## Struct using NamedTuple

Given a sequence `T_0`, `T_1`, ..., `T_n` of allowed types then a `NamedTuple` wrapping `tuple[T_0, T_1, ..., T_n]` is allowed as a type.
For example

```{code-cell}
from typing import NamedTuple

class MyStruct(NamedTuple):
    a: int
    b: str
    c: tuple[dict[str, list[int]], int]
```

The stub generation process will duplicate this type into the stubs file and it can then be used in graph builder code as `TKR[MyStruct]`.

```{tip}
The class generated in the stubs file will additionally inherit from `Protocol`.
Therefore if a struct is used as an input to a task then the graph builder code will accept any class with the appropriate fields.
This makes it easier to pass data between workers that contain similar class definitions but where there is not shared model library between the workers.
For nominal typing please use `BaseModel`, `DictConvertible` or `ListConvertible` as below.
```

## bytes

The Python type `bytes` is allowed as an input or output.
The exact behavior will depend on whether the bytes are at the 'top level' (e.g. the type of a whole output is `bytes`) or whether the bytes are nested within an output.

If the type of an output is `bytes` then no processing will be applied.
This is to enable smooth interop with tasks not produced by the Tierkreis Python library, which might be using an arbitrary serialization format.

If the bytes are nested inside an output (e.g. an output is of type `dict[str, bytes]`) then a custom JSON encoder is used.
The bytes `o` will appear nested in a JSON object as:

```python
{"__tkr_bytes__": True, "bytes": b64encode(o).decode()}
```

The bytes type is indicated by `TKR[bytes]` in graph builder code.

## DictConvertible and ListConvertible

In some cases we want to use complex classes that we nevertheless know how to serialize and deserialize.
In this case we can use the `DictConvertible` and `ListConvertible` protocols.
Specifically, any Python class that implements `to_dict` and `from_dict` methods are allowed.

```{code-cell}
from typing import Protocol, runtime_checkable

@runtime_checkable
class DictConvertible(Protocol):
    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, arg: dict, /) -> "Self": ...
```

similarly for classes that implement `to_list` and `from_list`

```{code-cell}

@runtime_checkable
class ListConvertible(Protocol):
    def to_list(self) -> list: ...
    @classmethod
    def from_list(cls, arg: list, /) -> "Self": ...
```

```{caution}
The Tierkreis Python library will attempt to serialize the resulting `dict` or `list` as JSON.
The worker author should ensure that this will not result in errors.
```

The stub generation process does not provide any introspection for these types but instead considers them 'opaque' and identifies them only by their fully qualified name.
For instance if one wants to use a `pytket` `Circuit` as an input or an output then the resulting type will look as follows:

```python
TKR[OpaqueType["pytket._tket.circuit.Circuit"]]
```

and a list of `Circuit`s would be typed as:

```python
TKR[list[OpaqueType["pytket._tket.circuit.Circuit"]]]
```

## Pydantic BaseModels

We can also use `pydantic.BaseModel` as an input or output.
The behavior of `BaseModel`s is very similar to `DictConvertible`.
For serialization the method `model_dump(mode="json")` will be used instead of `to_dict` and the stub generation process will create types using `OpaqueType` as above.
