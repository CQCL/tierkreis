import pytest

from tierkreis import Labels


def test_instantiate_raises() -> None:
    with pytest.raises(RuntimeError):
        Labels()
