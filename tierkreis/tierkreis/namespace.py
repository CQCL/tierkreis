from dataclasses import dataclass, field
from logging import getLogger
from typing import Callable, get_args, get_origin
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.models import PModel, is_portmapping
from tierkreis.controller.data.types import Struct, is_ptype
from tierkreis.exceptions import TierkreisError
from tierkreis.idl.models import Method, Model, TypeDecl
from types import NoneType
from typing import ForwardRef, assert_never
from pydantic import BaseModel
from tierkreis.controller.data.types import (
    DictConvertible,
    ListConvertible,
    _is_generic,
    _is_list,
    _is_mapping,
    _is_tuple,
    _is_union,
)

logger = getLogger(__name__)
WorkerFunction = Callable[..., PModel]
type MethodName = str


def format_ptype(ptype: type | ForwardRef) -> str:
    if isinstance(ptype, str):
        return ptype

    if isinstance(ptype, ForwardRef):
        return f"{ptype.__forward_arg__}"

    if _is_generic(ptype):
        return str(ptype)

    if _is_union(ptype):
        args = tuple([format_ptype(x) for x in get_args(ptype)])
        return " | ".join(args)

    if _is_tuple(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"tuple[{', '.join(args)}]"

    if _is_list(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"list[{', '.join(args)}]"

    if _is_mapping(ptype):
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"dict[{', '.join(args)}]"

    origin = get_origin(ptype)
    if origin is not None:  # Custom generic
        args = [format_ptype(x) for x in get_args(ptype)]
        return f"{format_ptype(origin)}[{", ".join(args)}]"

    if issubclass(ptype, (bool, int, float, str, bytes, NoneType, Struct)):
        return ptype.__qualname__

    if issubclass(ptype, (DictConvertible, ListConvertible, BaseModel)):
        return f'OpaqueType["{ptype.__module__}.{ptype.__qualname__}"]'

    assert_never(ptype)


class TierkreisWorkerError(TierkreisError):
    pass


@dataclass
class Namespace:
    name: str
    methods: dict[str, Method] = field(default_factory=lambda: {})
    types: dict[MethodName, dict[PortID, type]] = field(default_factory=lambda: {})
    generics: set[str] = field(default_factory=lambda: set())
    models: set[Model] = field(default_factory=lambda: set())

    def _add_model_from_type(self, t: type) -> None:
        if is_ptype(t) and not isinstance(t, Struct):
            return

        args = get_args(t)
        origin = get_origin(t)
        if origin is not None:
            t = origin

        annotations = t.__annotations__
        portmapping_flag = True if is_portmapping(t) else False
        decls = [TypeDecl(k, format_ptype(t)) for k, t in annotations.items()]
        model = Model(portmapping_flag, t.__qualname__, [str(x) for x in args], decls)
        self.models.add(model)

    def add_function(self, func: WorkerFunction) -> None:
        name = func.__name__
        annotations = func.__annotations__
        generics: list[str] = [str(x) for x in func.__type_params__]
        in_annotations = {k: v for k, v in annotations.items() if k != "return"}
        ins = [TypeDecl(k, format_ptype(v)) for k, v in in_annotations.items()]
        outs = annotations["return"]

        self.generics.update(generics)

        for k, annotation in in_annotations.items():
            if not is_ptype(annotation):
                raise TierkreisError(f"Expected PType found {annotation} {annotations}")
            existing = self.types.get(name, {})
            existing[k] = annotation
            self.types[name] = existing

        if not is_portmapping(outs) and not is_ptype(outs) and outs is not None:
            raise TierkreisError(f"Expected PModel found {outs}")
        print(outs)
        method = Method(name, generics, ins, format_ptype(outs), is_portmapping(outs))
        self.methods[method.name] = method

        [self._add_model_from_type(t) for _, t in annotations.items()]
