from dataclasses import dataclass, field
from inspect import isclass
from logging import getLogger
from types import NoneType
from typing import Any, Callable
from tierkreis.controller.data.models import PModel, PNamedModel, is_portmapping
from tierkreis.controller.data.types import PType, Struct, is_ptype
from tierkreis.exceptions import TierkreisError

logger = getLogger(__name__)
WorkerFunction = Callable[..., PModel]


class TierkreisWorkerError(TierkreisError):
    pass


@dataclass
class FunctionSpec:
    name: str
    namespace: str
    ins: dict[str, type[PType]]
    generics: list[str]
    outs: type[PModel] = NoneType

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
    structs: set[type[Struct]] = field(default_factory=lambda: set())
    output_models: set[type[PNamedModel]] = field(default_factory=lambda: set())

    def _add_struct(self, annotation: Any) -> None:
        if is_portmapping(annotation):
            return

        if not (isclass(annotation) and issubclass(annotation, Struct)):
            return

        self.structs.add(annotation)

    def _add_function_spec(self, fn: FunctionSpec) -> None:
        self.functions[fn.name] = fn
        self.generics.update(fn.generics)

        [self._add_struct(v) for v in fn.ins.values()]

        if is_portmapping(fn.outs):
            self.output_models.add(fn.outs)
        else:
            self._add_struct(fn.outs)

    def add_function(self, func: WorkerFunction) -> None:
        name = func.__name__
        annotations = func.__annotations__
        generics: list[str] = [str(x) for x in func.__type_params__]
        fn = FunctionSpec(name=name, namespace=self.name, ins={}, generics=generics)

        try:
            fn.add_inputs({k: v for k, v in annotations.items() if k != "return"})
            fn.add_outputs(annotations["return"])
        except TierkreisError as exc:
            logger.error(
                f"Error adding function {name} to {self.name} namespace.", exc_info=exc
            )

        self._add_function_spec(fn)
