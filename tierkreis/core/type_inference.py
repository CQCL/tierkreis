from typing import Optional, Tuple, Union, overload

import betterproto

import tierkreis.core.protos.tierkreis.graph as pg
import tierkreis.core.protos.tierkreis.signature as ps

# Awkwardly, the Rust stubs end up here:
from tierkreis import TierkreisGraph
from tierkreis import tierkreis as tierkreis_type_inference
from tierkreis.core.signature import Namespace, Signature
from tierkreis.core.types import TierkreisTypeErrors
from tierkreis.core.values import StructValue


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
        tierkreis_type_inference.infer_graph_types(bytes(req))
    )
    name, _ = betterproto.which_one_of(resp, "response")
    if name == "success":
        g = TierkreisGraph.from_proto(resp.success.graph)
        if inputs is None:
            assert resp.success.inputs is None
            return g
        return (g, StructValue.from_proto(resp.success.inputs))
    raise TierkreisTypeErrors.from_proto(resp.error)


def builtin_namespace() -> Namespace:
    return Namespace.from_proto(
        ps.Namespace().parse(tierkreis_type_inference.builtin_namespace())
    )
