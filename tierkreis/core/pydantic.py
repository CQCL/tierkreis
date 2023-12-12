import inspect
import warnings
from importlib.util import find_spec
from typing import Type

try:
    _PYDANTIC = (find_spec("pydantic")) is not None
except ModuleNotFoundError:
    _PYDANTIC = False


class PydanticNotInstalled(ImportError):
    pass


def map_constrained_number(type_: Type) -> Type | None:
    """If the type is a pydantic constrained version of a type Tierkreis can
    handle, return the base type.
    """
    if not _PYDANTIC:
        warnings.warn(
            "Automatic handling of pydantic objects requires"
            " pydantic to be installed, with the optional 'pydantic' feature."
        )
        return None
    else:
        import pydantic as pyd

    if not inspect.isclass(type_):
        return None

    for con_ty, base_ty in [
        (pyd.ConstrainedInt, int),
        (pyd.ConstrainedFloat, float),
        (pyd.ConstrainedStr, str),
    ]:
        if issubclass(type_, con_ty):
            return base_ty
