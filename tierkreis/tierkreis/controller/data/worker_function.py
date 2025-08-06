from typing import Callable, TypeVar

from tierkreis.controller.data.types import PType


_T0 = TypeVar("_T0", bound=PType, contravariant=True)
_T1 = TypeVar("_T1", bound=PType, contravariant=True)
_T2 = TypeVar("_T2", bound=PType, contravariant=True)
_T3 = TypeVar("_T3", bound=PType, contravariant=True)
_T4 = TypeVar("_T4", bound=PType, contravariant=True)
_T5 = TypeVar("_T5", bound=PType, contravariant=True)
_T6 = TypeVar("_T6", bound=PType, contravariant=True)
_T7 = TypeVar("_T7", bound=PType, contravariant=True)
_T8 = TypeVar("_T8", bound=PType, contravariant=True)
_T9 = TypeVar("_T9", bound=PType, contravariant=True)
_T10 = TypeVar("_T10", bound=PType, contravariant=True)
_T11 = TypeVar("_T11", bound=PType, contravariant=True)


WorkerFunction = (
    Callable[[], PType]
    | Callable[[_T0], PType]
    | Callable[[_T0, _T1], PType]
    | Callable[[_T0, _T1, _T2], PType]
    | Callable[[_T0, _T1, _T2, _T3], PType]
    | Callable[[_T0, _T1, _T2, _T3, _T4], PType]
    | Callable[[_T0, _T1, _T2, _T3, _T4, _T5], PType]
    | Callable[[_T0, _T1, _T2, _T3, _T4, _T5, _T6], PType]
    | Callable[[_T0, _T1, _T2, _T3, _T4, _T5, _T6, _T7], PType]
    | Callable[[_T0, _T1, _T2, _T3, _T4, _T5, _T6, _T7, _T8], PType]
    | Callable[[_T0, _T1, _T2, _T3, _T4, _T5, _T6, _T7, _T8, _T9], PType]
    | Callable[[_T0, _T1, _T2, _T3, _T4, _T5, _T6, _T7, _T8, _T9, _T10], PType]
    | Callable[[_T0, _T1, _T2, _T3, _T4, _T5, _T6, _T7, _T8, _T9, _T10, _T11], PType]
)
