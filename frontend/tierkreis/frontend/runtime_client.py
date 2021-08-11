"""Send requests to tierkreis server to execute a graph."""
from typing import Dict, IO, Iterator, List, cast, Optional
from dataclasses import dataclass
import copy
from contextlib import contextmanager
from pathlib import Path
import subprocess
import requests
import betterproto
from tierkreis.core.tierkreis_graph import TierkreisGraph
from tierkreis.core.function import TierkreisFunction
from tierkreis.core.values import TierkreisValue, StructValue
import tierkreis.core.protos.tierkreis.graph as pg
import tierkreis.core.protos.tierkreis.runtime as pr
import tierkreis.core.protos.tierkreis.signature as ps
import sys


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


NamespaceDict = Dict[str, TierkreisFunction]
RuntimeSignature = Dict[str, NamespaceDict]


class _TypeCheckContext:
    """Context manger for type checked graph building."""

    @dataclass
    class TypeInferenceError(Exception):
        """Error when context exit type inference is not succesful."""

        message: str

        def __str__(self) -> str:
            return (
                f"Type inference of built graph failed with message:\n {self.message}"
            )

    def __init__(
        self, client: "RuntimeClient", initial_graph: Optional[TierkreisGraph] = None
    ) -> None:
        self.client = client
        self.graph = (
            TierkreisGraph() if initial_graph is None else copy.deepcopy(initial_graph)
        )

    def __enter__(self) -> TierkreisGraph:
        return self.graph

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        # exeception info not currently used
        # but leaves the option to add context to errors using runtime
        try:
            self.graph._graph = self.client.type_check_graph(self.graph)._graph
        except RuntimeClient.RuntimeTypeError as err:
            raise self.TypeInferenceError(err.message)


class RuntimeClient:
    @dataclass
    class RuntimeTypeError(Exception):
        message: str

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
        raise self.RuntimeTypeError(str(message))

    def build_graph(
        self, initial_graph: Optional[TierkreisGraph] = None
    ) -> _TypeCheckContext:
        return _TypeCheckContext(self, initial_graph)


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


@contextmanager
def local_runtime(
    executable: Path,
    workers: List[Path],
    http_port: str = "8080",
    grpc_port: str = "9090",
    show_output: bool = False,
) -> Iterator[RuntimeClient]:
    """Provide a context for a local runtime running in a subprocess.

    :param executable: Path to server binary
    :type executable: Path
    :param workers: Paths of worker servers
    :type workers: List[Path]
    :param http_port: Localhost http port, defaults to "8080"
    :type http_port: str, optional
    :param grpc_port: Localhost grpc port, defaults to "9090"
    :type grpc_port: str, optional
    :param show_output: Show server tracing/errors, defaults to False
    :type show_output: bool, optional
    :yield: RuntimeClient
    :rtype: Iterator[RuntimeClient]
    """
    command = [executable, "--http", http_port, "--grpc", grpc_port]
    for worker in workers:
        command.extend(["--worker-path", worker])
    # server currently relies on a poetry install to use python workers
    # TODO: remove poetry requirement?
    command = ["poetry", "run"] + command
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in cast(IO[bytes], proc.stdout):
        if "Starting grpc server" in str(line):
            break

    try:
        yield RuntimeClient(f"http://127.0.0.1:{http_port}")
    finally:
        if show_output:
            proc.terminate()
            out, errs = proc.communicate()
            if errs:
                sys.stderr.buffer.write(errs)
            if out:
                sys.stdout.buffer.write(out)

        proc.kill()
