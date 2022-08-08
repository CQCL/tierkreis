from .tierkreis_graph import TierkreisGraph


def _singleton(cls):
    return cls()


@_singleton
class Labels:
    THUNK = "thunk"
    VALUE = "value"
    VARIANT_VALUE = "variant_value"
    CONTINUE = "continue"
    BREAK = "break"
