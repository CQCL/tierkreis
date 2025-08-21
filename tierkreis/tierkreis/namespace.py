from dataclasses import dataclass, field
from logging import getLogger
from types import NoneType
from typing import Any, Callable, get_args, get_origin
from tierkreis.controller.data.models import PModel, is_portmapping
from tierkreis.controller.data.types import Struct, is_ptype
from tierkreis.exceptions import TierkreisError
from tierkreis.idl.models import Model, TypeDecl

logger = getLogger(__name__)
WorkerFunction = Callable[..., PModel]


class TierkreisWorkerError(TierkreisError):
    pass


@dataclass
class FunctionSpec:
    name: str
    namespace: str
    ins: dict[str, type]
    generics: list[str]
    outs: type = NoneType

    def add_inputs(self, annotations: dict[str, Any]) -> None:
        for name, annotation in annotations.items():
            if not is_ptype(annotation):
                raise TierkreisError(f"Expected PType found {annotation} {annotations}")
            self.ins[name] = annotation

    def add_outputs(self, annotation: type | None) -> None:
        if annotation is None:
            self.outs = NoneType
        elif is_portmapping(annotation) or is_ptype(annotation):
            self.outs = annotation
        else:
            raise TierkreisError(f"Expected PModel found {annotation}")


@dataclass
class Namespace:
    name: str
    functions: dict[str, FunctionSpec] = field(default_factory=lambda: {})
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

    def _add_function_spec(self, fn: FunctionSpec) -> None:
        self.functions[fn.name] = fn
        self.generics.update(fn.generics)

    def add_function(self, func: WorkerFunction) -> None:
        name = func.__name__
        annotations = func.__annotations__
        generics: list[str] = [str(x) for x in func.__type_params__]
        fn = FunctionSpec(name=name, namespace=self.name, ins={}, generics=generics)

        [self._add_model_from_type(t) for _, t in annotations.items()]

        try:
            fn.add_inputs({k: v for k, v in annotations.items() if k != "return"})
            fn.add_outputs(annotations["return"])
        except TierkreisError as exc:
            logger.error(
                f"Error adding function {name} to {self.name} namespace.", exc_info=exc
            )

        self._add_function_spec(fn)
