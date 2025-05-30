from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class Value(BaseModel, Generic[T]):
    value: T
