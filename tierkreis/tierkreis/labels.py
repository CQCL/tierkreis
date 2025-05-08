"""Core Tierkreis Label type."""


class Labels:
    """Special port labels used by builtin functions."""

    def __init__(self):
        raise RuntimeError("Do not instantiate")

    THUNK = "thunk"
    VALUE = "value"
    VARIANT_VALUE = "variant_value"
    CONTINUE = "continue"
    BREAK = "break"
