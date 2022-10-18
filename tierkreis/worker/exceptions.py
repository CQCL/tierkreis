"""Worker exceptions."""
from dataclasses import dataclass


class FunctionNotFound(Exception):
    """Function not found."""

    def __init__(self, function):
        super().__init__()
        self.function = function


class DecodeInputError(Exception):
    pass


class EncodeOutputError(Exception):
    pass


@dataclass
class NodeExecutionError(Exception):
    base_exception: Exception


@dataclass(frozen=True)
class NamespaceClash(Exception):
    namespace: list[str]
    functions: set[str]

    def __str__(self) -> str:
        return f"""Clash in namespace {'::'.join(self.namespace)} of functions\n
        {self.functions}"""
