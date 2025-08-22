from dataclasses import dataclass, field
from logging import getLogger
from typing import Callable, get_args, get_origin
from tierkreis.controller.data.models import PModel, is_portmapping
from tierkreis.controller.data.types import Struct, is_ptype
from tierkreis.exceptions import TierkreisError
from tierkreis.idl.models import GenericType, Method, Model, TypeDecl
from tierkreis.idl.python import generictype_from_type

logger = getLogger(__name__)
WorkerFunction = Callable[..., PModel]


@dataclass
class Namespace:
    name: str
    methods: list[Method] = field(default_factory=lambda: [])
    generics: set[str] = field(default_factory=lambda: set())
    models: set[Model] = field(default_factory=lambda: set())

    def _add_model_from_type(self, t: type) -> None:
        args = get_args(t)
        origin = get_origin(t)

        if is_ptype(t) and not isinstance(t, Struct) and not isinstance(origin, Struct):
            return

        if origin is None:
            origin = t

        annotations = origin.__annotations__
        portmapping_flag = True if is_portmapping(origin) else False
        decls = [TypeDecl(k, generictype_from_type(t)) for k, t in annotations.items()]
        model = Model(portmapping_flag, GenericType(t.__qualname__, args), decls)
        self.models.add(model)

    def add_function(self, func: WorkerFunction) -> None:
        name = func.__name__
        annotations = func.__annotations__
        generics: list[str] = [str(x) for x in func.__type_params__]
        in_annotations = {k: v for k, v in annotations.items() if k != "return"}
        ins = [TypeDecl(k, generictype_from_type(t)) for k, t in in_annotations.items()]
        out = annotations["return"]

        self.generics.update(generics)

        for _, annotation in in_annotations.items():
            if not is_ptype(annotation):
                raise TierkreisError(f"Expected PType found {annotation} {annotations}")

        if not is_portmapping(out) and not is_ptype(out) and out is not None:
            raise TierkreisError(f"Expected PModel found {out}")

        method = Method(
            GenericType(name, generics),
            ins,
            generictype_from_type(out),
            is_portmapping(out),
        )
        self.methods.append(method)
        [self._add_model_from_type(t) for t in annotations.values()]
