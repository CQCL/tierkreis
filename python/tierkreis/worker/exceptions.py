"""Worker exceptions."""

from dataclasses import dataclass


class FunctionNotFound(Exception):
    """Function not found in worker."""

    def __init__(self, function):
        super().__init__()
        self.function = function


class DecodeInputError(Exception):
    """Failed to convert input values to Python objects."""

    pass


class EncodeOutputError(Exception):
    """Failed to convert worker function return values to Tierkreis values."""

    pass


@dataclass
class NodeExecutionError(Exception):
    """Error occurred during node execution."""

    base_exception: Exception


@dataclass(frozen=True)
class NamespaceClash(Exception):
    """Clash in namespace of functions."""

    namespace: list[str]
    functions: set[str]

    def __str__(self) -> str:
        return f"""Clash in namespace {'::'.join(self.namespace)} of functions\n
        {self.functions}"""
