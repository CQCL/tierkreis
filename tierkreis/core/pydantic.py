import inspect
import warnings
from importlib.util import find_spec
from typing import Any, ParamSpec, Type

try:
    _PYDANTIC = (find_spec("pydantic")) is not None
except ModuleNotFoundError:
    _PYDANTIC = False


class PydanticNotInstalled(ImportError):
    pass


def _get_pyd():
    if _PYDANTIC:
        import pydantic as pyd

        return pyd

    warnings.warn(
        "Automatic handling of pydantic objects requires"
        " pydantic to be installed, with the optional 'pydantic' feature."
    )
    return None


def _is_base_model(type_: Type | ParamSpec) -> bool:
    pyd = _get_pyd()
    if pyd is None:
        raise RuntimeError("Can't check without pydantic installed.")

    if inspect.isclass(type_):
        try:
            return issubclass(type_, pyd.BaseModel)
        except TypeError:
            return False
    return False


def _is_base_model_instance(value: Any) -> bool:
    pyd = _get_pyd()
    if pyd is None:
        raise RuntimeError("Can't check without pydantic installed.")

    return isinstance(value, pyd.BaseModel)
