from typing import Any, Callable, Generic, Protocol, TypeVar

from tierkreis.controller.data.models import PModel
from tierkreis.controller.data.types import PType


WorkerInput = TypeVar("WorkerInput", bound=PType, contravariant=True)
In0 = TypeVar("In0", bound=PType, contravariant=True)
In1 = TypeVar("In1", bound=PType, contravariant=True)
In2 = TypeVar("In2", bound=PType, contravariant=True)
In3 = TypeVar("In3", bound=PType, contravariant=True)
In4 = TypeVar("In4", bound=PType, contravariant=True)


class WorkerOverArgs(Protocol, Generic[In0, In1, In2, In3, In4]):
    @property
    def __name__(self) -> str: ...
    def __call__(
        self, a: In0, b: In1, c: In2, d: In3, e: In4, /, *args: Any, **kwds: Any
    ) -> PModel: ...


# fmt: off
WorkerFunction = (
    Callable[[], PModel]
    | Callable[[In0], PModel]
    | Callable[[In0, In1], PModel]
    | Callable[[In0, In1, In2], PModel]
    | Callable[[In0, In1, In2, In3], PModel]
    | Callable[[In0, In1, In2, In3, In4], PModel]
    | WorkerOverArgs[In0, In1, In2, In3, In4]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
    # | Callable[[WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput, WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput,WorkerInput], PModel]
)
# fmt: on
