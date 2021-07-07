"""Send requests to tierkreis server to execute a graph."""
from typing import Dict, cast
import betterproto
import requests
from dataclasses import dataclass
from tierkreis.core.tierkreis_graph import TierkreisFunction, TierkreisGraph
from tierkreis.core.values import TierkreisValue, StructValue
import tierkreis.core.protos.tierkreis.graph as pg
import tierkreis.core.protos.tierkreis.runtime as pr
import tierkreis.core.protos.tierkreis.signature as ps


@dataclass
class RuntimeHTTPError(Exception):
    endpoint: str
    response: requests.Response

    def __str__(self) -> str:
        return (
            f"Request to endpoint '{self.endpoint}'"
            f" failed with code {self.response.status_code},"
            f' and content "{str(self.response.content)} "'
        )


class RuntimeTypeError(Exception):
    pass


NamespaceDict = Dict[str, TierkreisFunction]
RuntimeSignature = Dict[str, NamespaceDict]


class RuntimeClient:
    def __init__(self, url: str = "http://127.0.0.1:8080") -> None:
        self._url = url
        self._signature_mod = self._get_signature()

    @property
    def signature(self) -> RuntimeSignature:
        return self._signature_mod

    def _get_signature(self) -> RuntimeSignature:
        resp = requests.get(
            self._url + "/signature",
            headers={"content-type": "application/protobuf"},
        )
        if resp.status_code != 200:
            raise RuntimeHTTPError("signature", resp)

        return signature_from_proto(ps.ListFunctionsResponse().parse(resp.content))

    def run_graph(
        self, graph: TierkreisGraph, inputs: Dict[str, TierkreisValue]
    ) -> Dict[str, TierkreisValue]:
        """Run a graph and return results

        :param gb: Graph to run.
        :type gb: ProtoGraphBuilder
        :param inputs: Inputs to graph as map from label to value.
        :type inputs: PyValMap
        :raises HTTPError: If server returns an error.
        :return: Outputs as map from label to value.
        :rtype: PyValMap
        """

        req = pr.RunGraphRequest(
            graph=graph.to_proto(),
            inputs=pg.StructValue(map=StructValue(inputs).to_proto_dict()),
        )
        resp = requests.post(
            self._url + "/run",
            headers={"content-type": "application/protobuf"},
            data=bytes(req),
        )
        if resp.status_code != 200:
            raise RuntimeHTTPError("run", resp)

        out = pr.RunGraphResponse().parse(resp.content)
        outputs = StructValue.from_proto_dict(out.outputs.map).values
        return outputs

    def type_check_graph(self, graph: TierkreisGraph) -> TierkreisGraph:

        resp = requests.post(
            self._url + "/type",
            headers={"content-type": "application/protobuf"},
            data=bytes(
                pr.InferTypeRequest(TierkreisValue.from_python(graph).to_proto())
            ),
        )
        if resp.status_code != 200:
            raise RuntimeHTTPError("type", resp)
        response = pr.InferTypeResponse().parse(resp.content)
        name, message = betterproto.which_one_of(response, "response")

        if name == "success":
            message = cast(pr.InferTypeSuccess, message)
            assert message.value.graph is not None
            return TierkreisValue.from_proto(message.value).to_python(TierkreisGraph)
        raise RuntimeTypeError(f"type error: {message}")


def signature_from_proto(pr_sig: ps.ListFunctionsResponse) -> RuntimeSignature:

    namespaces: Dict[str, Dict[str, TierkreisFunction]] = dict()
    for name, entry in pr_sig.functions.items():
        namespace, fname = name.split("/", 2)
        func = TierkreisFunction.from_proto(entry)
        if namespace in namespaces:
            namespaces[namespace][fname] = func
        else:
            namespaces[namespace] = {fname: func}
    return namespaces
