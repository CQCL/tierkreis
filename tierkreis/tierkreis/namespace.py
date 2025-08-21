from dataclasses import dataclass, field
from logging import getLogger
from typing import Callable, get_args, get_origin
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.models import PModel, is_portmapping
from tierkreis.controller.data.types import Struct, is_ptype
from tierkreis.exceptions import TierkreisError
from tierkreis.idl.models import GenericType, Method, Model, TypeDecl

logger = getLogger(__name__)
WorkerFunction = Callable[..., PModel]
type MethodName = str


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
        args = get_args(t)
        origin = get_origin(t)
        if origin is not None:
            t = origin

        if is_ptype(t) and not isinstance(t, Struct):
            return

        annotations = t.__annotations__
        portmapping_flag = True if is_portmapping(t) else False
        decls = [TypeDecl.from_annotation(k, t) for k, t in annotations.items()]
        model = Model(portmapping_flag, t.__qualname__, [str(x) for x in args], decls)
        self.models.add(model)

    def add_function(self, func: WorkerFunction) -> None:
        name = func.__name__
        annotations = func.__annotations__
        generics: list[str] = [str(x) for x in func.__type_params__]
        in_annotations = {k: v for k, v in annotations.items() if k != "return"}
        ins = [TypeDecl.from_annotation(k, t) for k, t in in_annotations.items()]
        out = annotations["return"]

        self.generics.update(generics)

        for k, annotation in in_annotations.items():
            if not is_ptype(annotation):
                raise TierkreisError(f"Expected PType found {annotation} {annotations}")
            existing = self.types.get(name, {})
            existing[k] = annotation
            self.types[name] = existing

        if not is_portmapping(out) and not is_ptype(out) and out is not None:
            raise TierkreisError(f"Expected PModel found {out}")

        method = Method(
            name, generics, ins, GenericType.from_type(out), is_portmapping(out)
        )
        self.methods[method.name] = method

        [self._add_model_from_type(t) for _, t in annotations.items()]
