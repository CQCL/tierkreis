"""Implementation of Hugr std lib in python."""
from dataclasses import dataclass
from typing import cast

from hugr import ops, tys, val
from hugr.std.int import IntVal
from hugr.val import Value


@dataclass
class USizeVal(val.ExtensionValue):
    v: int

    def to_value(self) -> val.Extension:
        return val.Extension(
            "ConstUSize",
            typ=tys.USize(),
            val = {"value": self.v} # or just the int without the dict?
        )
    
    def __str(self) -> str:
        return f"{self.v}"

def run_ext_op(op: ops.Custom, inputs: list[Value]) -> list[Value]:
    def two_ints_logwidth() -> tuple[int, int, int]:
        (a, b) = inputs
        if not isinstance(a, val.Extension):
            a = cast(val.ExtensionValue, a).to_value()
        av = a.val["value"]
        assert isinstance(av, int)

        if not isinstance(b, val.Extension):
            b = cast(val.ExtensionValue, b).to_value()
        bv = b.val["value"]
        assert isinstance(bv, int)

        lw = a.val["log_width"]
        assert isinstance(lw, int)
        assert lw == b.val["log_width"]
        return av, bv, lw
    def one_int_logwidth() -> tuple[int, int]:
        (a,) = inputs
        if not isinstance(a, val.Extension):
            a = cast(val.ExtensionValue, a).to_value()
        av = a.val["value"]
        assert isinstance(av, int)

        lw = a.val["log_width"]
        assert isinstance(lw, int)
        return av, lw

    if op.extension == "arithmetic.conversions":
        if op.op_name == "itousize":
            (a,_) = one_int_logwidth()
            return [USizeVal(a).to_value()]
    elif op.extension == "arithmetic.int":
        if op.op_name in ["ilt_u", "ilt_s"]:  # TODO how does signedness work here
            (a, b, _) = two_ints_logwidth()
            return [val.TRUE if a < b else val.FALSE]
        if op.op_name in ["igt_u", "igt_s"]:  # TODO how does signedness work here
            (a, b, _) = two_ints_logwidth()
            return [val.TRUE if a > b else val.FALSE]
        if op.op_name == "isub":
            (a, b, lw) = two_ints_logwidth()
            # TODO: wrap/underflow to appropriate width
            return [IntVal(a - b, lw).to_value()]
        if op.op_name == "imul":
            (a, b, lw) = two_ints_logwidth()
            # TODO: wrap/overflow to appropriate width
            return [IntVal(a * b, lw).to_value()]
        if op.op_name == "iadd":
            (a, b, lw) = two_ints_logwidth()
            # TODO: wrap/underflow to appropriate width
            return [IntVal(a + b, lw).to_value()]
        if op.op_name in ["idiv_s", "idiv_u"]:  # TODO how does signedness work here
            (a, b, lw) = two_ints_logwidth()
            return [IntVal(a//b, lw).to_value()]
        if op.op_name in ["imod_s", "imod_u"]:  # TODO how does signedness work here
            (a, b, lw) = two_ints_logwidth()
            return [IntVal(a % b, lw).to_value()]
        if op.op_name == "ineg":
            (a, lw) = one_int_logwidth()
            return [IntVal(-a, lw).to_value()]
    elif op.extension == "logic":
        if op.op_name == "Not":
            (a,) = inputs
            assert a in [val.TRUE, val.FALSE]
            return [val.FALSE if a == val.TRUE else val.TRUE]
        if op.op_name == "Eq":  # Yeah, presumably case sensitive, so why not 'eq'
            (a,b) = inputs
            assert a in [val.TRUE, val.FALSE]
            assert b in [val.TRUE, val.FALSE]
            return [val.TRUE if (a == b) else val.FALSE]
    raise RuntimeError(f"Unknown op {op}")
