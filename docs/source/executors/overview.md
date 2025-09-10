# Executors

Executors are fundamental in running graph nodes in different environments.

## Existing executors

Currently the following executors are available for the use

| Executor         |             Target Workers              | Enabled |                                        Notes                                         |
| ---------------- | :-------------------------------------: | :-----: | :----------------------------------------------------------------------------------: |
| UVExecutor       | Python based with dependency management |    ✔    |                           Default for python based workers                           |
| ShellExecutor    |                 Scripts                 |    ✔    |                                  Runs shell scripts                                  |
| StdInOut         |                 Scripts                 |    ✔    |                 Runs shell scripts with single input and output file                 |
| InMemoryExecutor |                 Python                  |    ✔    | Runs in the same memory spaces as the controller, does not work for external workers |
| SLURMExecutor    |                   Any                   |    ✔    |                        Wraps a command in a SLURM submission                         |
| PJSUBExecutor    |                   Any                   |   ❌    |                        Wraps a command in a PJSUB submission                         |
| PBSExecutor      |                   Any                   |   ❌    |                         Wraps a command in a PBS submission                          |

## Combining Executors

By default only one executor needs to be available to the controller.
All workers will be run through this executor.
If different executors are necessary they can be combined using the `MultipleExecutor` like so:

```py
multi_executor = MultipleExecutor(
    default = default_executor,
    executors={"custom_a": custom_executor_a, "custom+b": custom_executor_b},
    assignments={"worker_a": "custom_a", "worker_b": "custom_b"},
)
```

It provides a an assignment of workers to executors by a string mapping, a default executor will execute all unassigned workers.

## Writing your own executor

Most use cases should already be covered by the existing executors.
In some instances it might be necessary to write a custom executor which can be done by implementing the protocol.
The executor protocol defines a single function

```py
def run(self, launcher_name: str, worker_call_args_path: Path) -> None:
    ...
```

- `launcher_name` identifies the worker to be run
- `worker_call_args_path` is the _relative_ path to the node definition containing
  - the name of the worker task
  - _relative_ locations to input and output files
  - _relative_ locations to internal files, such as error flags and log files

The executor is responsible to modify these inputs in such a way that the worker can operate correctly.
Assuming the worker already can deal with all of this, a minimal executor could simply spawn a new process running the worker.

```py
class MinimalExecutor:
    def run(self, launcher_name: str, worker_call_args_path: Path) -> None:
        subprocess.Popen(
            [launcher_name, str(worker_call_args_path)],
        )
```
