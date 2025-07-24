from dataclasses import dataclass, field
from inspect import get_annotations
from logging import getLogger
from types import NoneType
from typing import Any, Callable
from tierkreis.controller.data.models import (
    PModel,
    PNamedModel,
    is_pnamedmodel,
    is_portmapping,
)
from tierkreis.controller.data.types import PType, is_ptype
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
    outs: type[PModel]
    generics: list[str]

    def add_inputs(self, annotations: dict[str, Any]) -> None:
        for name, annotation in annotations.items():
            if not is_ptype(annotation):
                raise TierkreisError(f"Expected PType found {annotation} {annotations}")
            self.ins[name] = annotation

    def add_outputs(self, annotation: type | None) -> None:
        if annotation is None:
            self.outs = NoneType
            return
        elif is_portmapping(annotation):
            self.outs = annotation
        elif not is_ptype(annotation):
            raise TierkreisError(f"Expected PModel found {annotation}")
        else:
            self.outs = annotation


@dataclass
class Namespace:
    name: str
    functions: dict[str, FunctionSpec] = field(default_factory=lambda: {})
    generics: set[str] = field(default_factory=lambda: set())
    input_models: set[type[PNamedModel]] = field(default_factory=lambda: set())
    output_models: set[type[PNamedModel]] = field(default_factory=lambda: set())

    def _add_input_model(self, annotation: Any) -> None:
        if is_pnamedmodel(annotation):
            sub_annotations = get_annotations(annotation)
            [
                self._add_input_model(sub_annotation)
                for sub_annotation in sub_annotations
            ]

            self.input_models.add(annotation)

    def add_from_annotations(self, func: WorkerFunction) -> None:
        name = func.__name__
        annotations = func.__annotations__
        try:
            generics: list[str] = [str(x) for x in func.__type_params__]
            fn = FunctionSpec(
                name=name, namespace=self.name, ins={}, outs=NoneType, generics=generics
            )

            [self._add_input_model(v) for k, v in annotations.items() if k != "return"]
            fn.add_inputs({k: v for k, v in annotations.items() if k != "return"})

            if is_portmapping(annotations["return"]):
                self.output_models.add(annotations["return"])
            elif is_pnamedmodel(annotations["return"]):
                self.input_models.add(annotations["return"])
            fn.add_outputs(annotations["return"])

            self.functions[fn.name] = fn
            self.generics.update(fn.generics)
        except TierkreisError as exc:
            logger.error(
                f"Error adding function {name} to {self.name} namespace.", exc_info=exc
            )
