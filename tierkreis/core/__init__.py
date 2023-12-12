class Labels:
    def __init__(self):
        raise RuntimeError("Do not instantiate")

    THUNK = "thunk"
    VALUE = "value"
    VARIANT_VALUE = "variant_value"
    CONTINUE = "continue"
    BREAK = "break"


# This needs to be here to fix some cycles in the imports
from .tierkreis_graph import TierkreisGraph  # noqa: E402, F401
