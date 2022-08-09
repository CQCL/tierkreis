from .tierkreis_graph import TierkreisGraph


class Labels:
    def __init__(self):
        raise RuntimeError("Do not instantiate")

    THUNK = "thunk"
    VALUE = "value"
    VARIANT_VALUE = "variant_value"
    CONTINUE = "continue"
    BREAK = "break"
