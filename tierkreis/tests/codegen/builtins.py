from abc import ABC, abstractmethod
from pydantic import BaseModel

from tierkreis.controller.data.core import TypedValueRef


class Value_bool_(BaseModel):
    value: TypedValueRef[bool]


class Value_int_(BaseModel):
    value: TypedValueRef[int]


class Value_str_(BaseModel):
    value: TypedValueRef[str]


class builtins(ABC):
    @staticmethod
    @abstractmethod
    def iadd(a: TypedValueRef[int], b: TypedValueRef[int]) -> TypedValueRef[int]: ...

    @staticmethod
    @abstractmethod
    def itimes(a: TypedValueRef[int], b: TypedValueRef[int]) -> TypedValueRef[int]: ...

    @staticmethod
    @abstractmethod
    def igt(a: TypedValueRef[int], b: TypedValueRef[int]) -> TypedValueRef[bool]: ...

    @staticmethod
    @abstractmethod
    def impl_and(
        a: TypedValueRef[bool], b: TypedValueRef[bool]
    ) -> TypedValueRef[bool]: ...

    @staticmethod
    @abstractmethod
    def str_eq(a: TypedValueRef[str], b: TypedValueRef[str]) -> TypedValueRef[bool]: ...

    @staticmethod
    @abstractmethod
    def str_neq(
        a: TypedValueRef[str], b: TypedValueRef[str]
    ) -> TypedValueRef[bool]: ...

    @staticmethod
    @abstractmethod
    def concat(
        lhs: TypedValueRef[str], rhs: TypedValueRef[str]
    ) -> TypedValueRef[str]: ...
