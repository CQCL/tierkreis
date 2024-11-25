"""Type inference for Tierkreis graphs, depends on the `tierkreis_typecheck` package."""

from importlib.util import find_spec
from typing import Optional, Tuple, Union, overload

import betterproto

import tierkreis.core.protos.tierkreis.v1alpha1.graph as pg
import tierkreis.core.protos.tierkreis.v1alpha1.signature as ps

# Awkwardly, the Rust stubs end up here:
from tierkreis import TierkreisGraph
from tierkreis.core.signature import Namespace, Signature
from tierkreis.core.type_errors import TierkreisTypeErrors
from tierkreis.core.values import StructValue

try:
    _TYPE_CHECK = find_spec("tierkreis_typecheck") is not None
except ModuleNotFoundError:
    _TYPE_CHECK = False


class TypeCheckNotInstalled(ImportError):
    """Raised when tierkreis_typecheck is not installed."""

    pass


_ERR = TypeCheckNotInstalled(
    "Type checking requires tierkreis_typecheck package to be installed."
)


@overload
def infer_graph_types(
    g: TierkreisGraph,
    funcs: Signature,
    inputs: None = None,
) -> TierkreisGraph: ...


@overload
def infer_graph_types(
    g: TierkreisGraph,
    funcs: Signature,
    inputs: StructValue,
) -> Tuple[TierkreisGraph, StructValue]: ...


def infer_graph_types(
    g: TierkreisGraph,
    funcs: Signature,
    inputs: Optional[StructValue] = None,
) -> Union[TierkreisGraph, Tuple[TierkreisGraph, StructValue]]:
    """Infer the types in a graph and its inputs given a signature to check
    against.
    If successful both the graph and inputs are returned, with type annotations
    added.
    If inputs are not provided, only the graph is returned.
    Raises `TierkreisTypeErrors` if the inference fails.
    """
    if not _TYPE_CHECK:
        raise _ERR
    else:
        import tierkreis_typecheck

    req = ps.InferGraphTypesRequest(
        gwi=ps.GraphWithInputs(
            graph=g.to_proto(),
            inputs=None
            if inputs is None
            else pg.StructValue(map=inputs.to_proto_dict()),
        ),
        functions=funcs.root.to_proto(),
    )
    resp = ps.InferGraphTypesResponse().parse(
        tierkreis_typecheck.infer_graph_types(bytes(req))
    )
    name, _ = betterproto.which_one_of(resp, "response")
    if name == "success":
        g = TierkreisGraph.from_proto(resp.success.graph)
        if inputs is None:
            assert resp.success.inputs is None
            return g
        return (g, StructValue.from_proto(resp.success.inputs))
    raise TierkreisTypeErrors.from_proto(resp.error, g)


def builtin_namespace() -> Namespace:
    """The namespace of built-in functions."""
    if _TYPE_CHECK:
        import tierkreis_typecheck

        return Namespace.from_proto(
            ps.Namespace().parse(tierkreis_typecheck.builtin_namespace())
        )
    else:
        raise _ERR
