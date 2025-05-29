from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class CAddResponse:
    a: "int"
    value: "AddResponse"


@dataclass
class AddRequest:
    a: "int"
    b: "int"


@dataclass
class AddResponse:
    value: "int"


@dataclass
class AddSRequest:
    a: "int"
    b: "int"


@dataclass
class AddSResponse:
    value: "str"


@dataclass
class CAddRequest:
    a: "int"
    b: "int"


class BuiltinsService(ABC):
    @abstractmethod
    @staticmethod
    def Add(Add_request: AddRequest) -> AddResponse: ...
    @abstractmethod
    @staticmethod
    def AddS(AddS_request: AddSRequest) -> AddSResponse: ...
    @abstractmethod
    @staticmethod
    def CAdd(CAdd_request: CAddRequest) -> CAddResponse: ...


class BuiltinsImpl(BuiltinsService):
    pass


BuiltinsImpl()
