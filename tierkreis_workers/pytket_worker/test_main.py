from pytket._tket.unit_id import Bit
from pytket.backends.backendresult import BackendResult
from pytket.utils.outcomearray import OutcomeArray

from .main import backend_result_from_dict, backend_result_to_dict


def test_backend_result_conversion() -> None:
    original_result = BackendResult(
        shots=OutcomeArray.from_readouts([[0, 1, 0], [1, 0, 1], [1, 1, 1]]),
        c_bits=[Bit("a", 0), Bit("b", 0), Bit("b", 1)],
    )
    result_dict = backend_result_to_dict(original_result)
    reconstructed_result = backend_result_from_dict(result_dict)
    assert (
        original_result.get_shots().tolist()
        == reconstructed_result.get_shots().tolist()
    )
    assert original_result.c_bits == reconstructed_result.c_bits
    assert result_dict == {
        "a": ["0", "1", "1"],
        "b": ["10", "01", "11"],
    }


if __name__ == "__main__":
    test_backend_result_conversion()
