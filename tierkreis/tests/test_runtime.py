"""Tests for the public runtime facade."""

from tierkreis import runtime


def test_runtime_api_is_public() -> None:
    """The supported facade exposes the Rust runtime entry points."""
    assert runtime.Runtime is not None
    assert hasattr(runtime.Runtime, "get_raw_outputs")
    assert runtime.RuntimeConfig is not None
    assert callable(runtime.new_default)
    assert callable(runtime.new_from_config)
    assert callable(runtime.load_runtime_config)
