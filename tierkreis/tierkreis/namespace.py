from dataclasses import dataclass, field
from logging import getLogger
from pathlib import Path
from typing import Callable, Self, get_origin
from tierkreis.controller.data.models import PModel, is_portmapping
from tierkreis.controller.data.types import Struct, is_ptype
from tierkreis.exceptions import TierkreisError
from tierkreis.idl.spec import spec
from tierkreis.idl.models import GenericType, Interface, Method, Model, TypedArg

logger = getLogger(__name__)
WorkerFunction = Callable[..., PModel]


@dataclass
class Namespace:
    name: str
    methods: list[Method] = field(default_factory=lambda: [])
    models: set[Model] = field(default_factory=lambda: set())

    def _add_model_from_type(self, t: type) -> None:
        origin = get_origin(t)

        if is_ptype(t) and not isinstance(t, Struct) and not isinstance(origin, Struct):
            return

        if origin is None:
            origin = t

        annotations = origin.__annotations__
        portmapping_flag = True if is_portmapping(origin) else False
        decls = [TypedArg(k, GenericType.from_type(x)) for k, x in annotations.items()]
        model = Model(portmapping_flag, GenericType.from_type(t), decls)
        self.models.add(model)

    def add_function(self, func: WorkerFunction) -> None:
        name = func.__name__
        annotations = func.__annotations__
        generics: list[str] = [str(x) for x in func.__type_params__]
        in_annotations = {k: v for k, v in annotations.items() if k != "return"}
        ins = [TypedArg(k, GenericType.from_type(t)) for k, t in in_annotations.items()]
        out = annotations["return"]

        for _, annotation in in_annotations.items():
            if not is_ptype(annotation):
                raise TierkreisError(f"Expected PType found {annotation} {annotations}")

        if not is_portmapping(out) and not is_ptype(out) and out is not None:
            raise TierkreisError(f"Expected PModel found {out}")

        method = Method(
            GenericType(name, generics),
            ins,
            GenericType.from_type(out),
            is_portmapping(out),
        )
        self.methods.append(method)
        [self._add_model_from_type(t) for t in annotations.values()]

    @classmethod
    def from_spec_file(cls, path: Path) -> "Namespace":
        with open(path) as fh:
            namespace_spec = spec(fh.read())
            return cls._from_spec(namespace_spec[0])

    @classmethod
    def _from_spec(cls, args: tuple[list[Model], Interface]) -> "Self":
        models = args[0]
        interface = args[1]
        namespace = cls(interface.name, models=set(models))
        for f in interface.methods:
            model = next((x for x in models if x.t == f.return_type), None)
            if model is not None:
                f.return_type_is_portmapping = model.is_portmapping
            namespace.methods.append(f)

        return namespace
