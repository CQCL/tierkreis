from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Optional, cast

import betterproto

import tierkreis.core.protos.tierkreis.v1alpha1.graph as pg
import tierkreis.core.protos.tierkreis.v1alpha1.signature as ps
from tierkreis.core.function import FunctionName
from tierkreis.core.tierkreis_graph import (
    BoxNode,
    ConstNode,
    FunctionNode,
    GraphValue,
    MatchNode,
    NodeRef,
    TagNode,
)
from tierkreis.core.types import GraphType, Row, TierkreisType

if TYPE_CHECKING:
    from tierkreis.core.tierkreis_graph import TierkreisGraph, TierkreisNode


def _node_port_str(idx: int, port: str, g: "TierkreisGraph") -> str:
    return f'{_node_str(idx, g[idx])[0]}["{port}"]'


def _node_str(idx: int, tkn: "TierkreisNode") -> tuple[str, Optional["TierkreisGraph"]]:
    # if node contains another graph return it as second value
    s = str(idx)
    g = None
    if isinstance(tkn, FunctionNode):
        s += f", Function({str(tkn.function_name)})"
    elif isinstance(tkn, BoxNode):
        g = tkn.graph
        s += ", Box"
        if tkn.location:
            s += "@"
            s += "/".join(tkn.location.location)
        if tkn.graph.name:
            s += f"({tkn.graph.name})"
    elif isinstance(tkn, TagNode):
        s += f", Tag({tkn.tag_name})"

    elif isinstance(tkn, MatchNode):
        s += ", Match"
    elif isinstance(tkn, ConstNode):
        val = tkn.value
        if isinstance(val, GraphValue) and val.value.name:
            val_str = f"Graph({val.value.name})"
            g = val.value
        else:
            val_str = val.viz_str()
        s += f", Const({val_str})"
    return f"NodeRef({s})", g


_NODE_IDX_LOCS = (
    "input",
    "output",
    "pair_first",
    "pair_second",
    "map_key",
    "map_value",
)


@dataclass(frozen=True)
class TierkreisTypeError(Exception):
    """Base class for all type errors."""

    proto_err: ps.TierkreisTypeError
    graph: "TierkreisGraph"
    dbg: dict[NodeRef, str] = field(default_factory=dict)

    def __str__(self) -> str:
        # default type error string
        return f"{self.proto_err.variant}\n\nIn:{self.location_str()}"

    @classmethod
    def from_proto(
        cls,
        proto: ps.TierkreisTypeError,
        g: "TierkreisGraph",
        debug: dict[NodeRef, str],
    ) -> "TierkreisTypeError":
        name, _ = betterproto.which_one_of(proto.variant, "error")
        cls_map = {
            "unify": UnifyError,
            "unknown_function": UnknownFunction,
        }

        # TODO more error variant special casing
        return cls_map.get(name, cls)(proto, g, debug)

    def _get_dbg_str(
        self, name: str, out_type: Any, g: "TierkreisGraph"
    ) -> Optional[str]:
        if name not in ("node_idx", "input", "output"):
            return ""
        idx = 0 if name == "input" else 1 if name == "output" else cast(int, out_type)
        return self.dbg.get(NodeRef(idx, g))

    def location_str(self) -> str:
        locs = []
        dbgs = []
        current_g = self.graph
        for location in self.proto_err.location:
            name, out_type = betterproto.which_one_of(location, "location")
            if dbg_str := self._get_dbg_str(name, out_type, current_g):
                # s += f"\n{dbg_str}"
                dbgs.append(dbg_str)
            if name == "root":
                continue
            elif name in _NODE_IDX_LOCS:
                locs.append(name)
            elif name == "vec_index":
                locs.append(f"Vec index[{out_type}]")
            elif name == "struct_field":
                locs.append(f"StructField({out_type})")
            elif name == "input_value":
                locs.append(f"InputValue({out_type})")
            elif name == "edge":
                tke = cast(pg.Edge, out_type)
                src = _node_port_str(tke.node_from, tke.port_from, current_g)
                tgt = _node_port_str(tke.node_to, tke.port_to, current_g)
                locs.append(f"Edge({src} -> {tgt})")
            elif name == "node_idx":
                idx = cast(int, out_type)
                s_n, next_g = _node_str(idx, current_g[idx])
                current_g = next_g or current_g
                locs.append(s_n)
            else:
                locs.append(str(out_type))

        s = "In: "
        s += "/".join(locs)
        if dbgs:
            s += "\nDebug Info:\n" + "\n".join(dbgs)

        return s

    def to_proto(self) -> ps.TierkreisTypeError:
        return self.proto_err


def _row_diff_hint(expected_r: Row, found_r: Row, name: str) -> str:
    hintstr = ""
    if expected_r.rest is None and (
        inter := set(found_r.content).difference(expected_r.content)
    ):
        hintstr += f"There are extra {name}: {inter}.\n"
    if found_r.rest is None and (
        inter := set(expected_r.content).difference(found_r.content)
    ):
        hintstr += f"There are missing {name}: {inter}.\n"

    return hintstr


class UnifyError(TierkreisTypeError):
    def __str__(self) -> str:
        expected = TierkreisType.from_proto(self.proto_err.variant.unify.expected)
        found = TierkreisType.from_proto(self.proto_err.variant.unify.found)
        s = f"Expected type {expected} but found {found}"

        s += "\n"
        s += self.location_str()

        if isinstance(expected, GraphType) and isinstance(found, GraphType):
            hintstr = _row_diff_hint(expected.inputs, found.inputs, "inputs")
            hintstr += _row_diff_hint(expected.outputs, found.outputs, "outputs")
            if hintstr:
                s += f"\nHint: {hintstr}"
        return s


class UnknownFunction(TierkreisTypeError):
    def __str__(self) -> str:
        fnam = FunctionName.from_proto(self.proto_err.variant.unknown_function)
        return f"Unknown function: {str(fnam)}\n{self.location_str()}"


@dataclass()
class TierkreisTypeErrors(Exception):
    errors: list[TierkreisTypeError]

    @classmethod
    def from_proto(
        cls, proto: ps.TypeErrors, g: "TierkreisGraph"
    ) -> "TierkreisTypeErrors":
        return cls(
            errors=[
                TierkreisTypeError.from_proto(error, g, {}) for error in proto.errors
            ],
        )

    def to_proto(self) -> ps.TypeErrors:
        return ps.TypeErrors([e.to_proto() for e in self.errors])

    def __str__(self) -> str:
        separator = "\n\n" + ("─" * 80) + "\n\n"
        return separator.join(map(str, self.errors))

    def __getitem__(self, index: int) -> TierkreisTypeError:
        return self.errors[index]

    def __len__(self) -> int:
        return len(self.errors)

    def with_debug(self, dbg: dict[NodeRef, str]) -> "TierkreisTypeErrors":
        self.errors = [replace(e, dbg=dbg) for e in self.errors]
        return self
