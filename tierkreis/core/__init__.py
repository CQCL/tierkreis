class Labels:
    def __init__(self):
        raise RuntimeError("Do not instantiate")

    THUNK = "thunk"
    VALUE = "value"
    VARIANT_VALUE = "variant_value"
    CONTINUE = "continue"
    BREAK = "break"
    # These are not set by the protobuf/Tierkreis framework,
    # but used by the python frontend to map to python 'Optional'
    SOME = "Some"
    NONE = "None"


# This needs to be here to fix some cycles in the imports
from .tierkreis_graph import TierkreisGraph  # pylint: disable=wrong-import-position
