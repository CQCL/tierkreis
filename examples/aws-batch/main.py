from uuid import UUID
from tierkreis.controller import run_graph
from tierkreis.storage import FileStorage
from tierkreis.executor import AwsBatchExecutor
from examples.hello_world_graph import hello_graph

storage = FileStorage(UUID(int=1), "hello_world")
executor = AwsBatchExecutor()
run_graph(storage, executor, hello_graph().get_data(), {}, n_iterations=10)
