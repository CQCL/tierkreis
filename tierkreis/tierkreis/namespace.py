from dataclasses import dataclass, field
from logging import getLogger
from types import NoneType
from typing import Any, Callable, get_args, get_origin
from tierkreis.controller.data.models import PModel, is_portmapping
from tierkreis.controller.data.types import Struct, is_ptype
from tierkreis.exceptions import TierkreisError
from tierkreis.idl.models import Method, Model, TypeDecl

logger = getLogger(__name__)
WorkerFunction = Callable[..., PModel]


class TierkreisWorkerError(TierkreisError):
    pass


@dataclass
class Namespace:
    name: str
    methods: dict[str, Method] = field(default_factory=lambda: {})
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
        decls = [TypeDecl(k, t) for k, t in annotations.items()]
        model = Model(portmapping_flag, t.__qualname__, [str(x) for x in args], decls)
        self.models.add(model)

    def add_function(self, func: WorkerFunction) -> None:
        name = func.__name__
        annotations = func.__annotations__
        generics: list[str] = [str(x) for x in func.__type_params__]
        ins = [TypeDecl(k, v) for k, v in annotations.items() if k != "return"]
        outs = annotations["return"]

        self.generics.update(generics)

        for _, annotation in ins:
            if not is_ptype(annotation):
                raise TierkreisError(f"Expected PType found {annotation} {annotations}")

        if not is_portmapping(outs) and not is_ptype(outs) and outs is not None:
            raise TierkreisError(f"Expected PModel found {outs}")

        method = Method(name, generics, ins, annotations["return"])
        self.methods[method.name] = method

        [self._add_model_from_type(t) for _, t in annotations.items()]
