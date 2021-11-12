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
