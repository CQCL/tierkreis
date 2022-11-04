from typing import Optional, Tuple, Union, overload

import betterproto

try:
    import tierkreis_typecheck

    _TYPE_CHECK = True
except ImportError:
    _TYPE_CHECK = False

import tierkreis.core.protos.tierkreis.v1alpha.graph as pg
import tierkreis.core.protos.tierkreis.v1alpha.signature as ps

# Awkwardly, the Rust stubs end up here:
from tierkreis import TierkreisGraph
from tierkreis.core.signature import Namespace, Signature
from tierkreis.core.type_errors import TierkreisTypeErrors
from tierkreis.core.values import StructValue


class TypeCheckNotInstalled(ImportError):
    pass


_ERR = TypeCheckNotInstalled(
    "Type checking requires tierkreis_typecheck package to be installed."
)


@overload
def infer_graph_types(
    g: TierkreisGraph,
    funcs: Signature,
    inputs: None = None,
) -> TierkreisGraph:
    ...


@overload
def infer_graph_types(
    g: TierkreisGraph,
    funcs: Signature,
    inputs: StructValue,
) -> Tuple[TierkreisGraph, StructValue]:
    ...


def infer_graph_types(
    g: TierkreisGraph,
    funcs: Signature,
    inputs: Optional[StructValue] = None,
) -> Union[TierkreisGraph, Tuple[TierkreisGraph, StructValue]]:
    if not _TYPE_CHECK:
        raise _ERR
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
    if not _TYPE_CHECK:
        raise _ERR

    return Namespace.from_proto(
        ps.Namespace().parse(tierkreis_typecheck.builtin_namespace())
    )
