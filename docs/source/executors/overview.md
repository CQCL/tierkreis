# Executors

Executors are fundamental in running graph nodes in different environments.
They also ensure that the workers can fulfill their contracts by preparing inputs and outputs.

## The worker contract

To function properly, the controller makes assumptions about the input and outputs of tasks.
Typically the workers assure that these assumptions are met.
The executors have to provide the required information to ensure the workers do this correctly.
The information is stored in the [`WorkerCallArgs`](#tierkreis.controller.data.location.WorkerCallArgs) which is also used to invoke the worker.
If a worker cannot produce the necessary files, this causes tierkreis to not complete a workflow.
The responsibility of the executor is to ensure the normal operations by, for example, translating relative paths to absolute ones.

### Controller files

The controller is aware of the following files, if not specified otherwise they are expected in `<checkpoints_dir>/<workflow_id>/<node_location>/`

- The `logs` files: any logging information should be written to either of two files
  - controller logs are written to `<checkpoints_dir>/<workflow_id>/logs` and contain global progress information
  - worker specific logs should be written to the `logs_path` location of its call arguments, typically `<checkpoints_dir>/<workflow_id>/<node_location>/logs`
- The presence of the `nodedef` file indicates the node has been started, workers should not interact with this
- The `definition` file contains the serialized `WorkerCallArgs`, the worker needs to parse this to find out about the locations inputs, outputs and the here listed files.
- Completion is indicated by the `_done` file, workers must set this once they have written all outputs
- Failures is indicated by the `_error` file, workers must set this if they can not complete normal execution
- In case of failure error messages should be written to the `errors_path` location of its call arguments, typically `<checkpoints_dir>/<workflow_id>/<node_location>/errors`.
  Currently as a fallback it is also possible to write to the `<checkpoints_dir>/<workflow_id>/<node_location>/_errors` file.

### Task, Inputs and Outputs

`WorkerCallArgs` contain the information of the function name of the task to call and it's inputs and the location to write outputs to.
To supply workers with their inputs the `WorkerCallArgs` specify a mapping of input name to a location where the input is stored.
For example, the `greet` task of the [`hello_world_worker`](../worker/hello_world.md) expects two string inputs and outputs one file.
The inputs are can be looked up by port name (`greeting`, `subject`) their values are stored in the output of other nodes in a a file `<checkpoints_dir>/<workflow_id>/<node_location>/outputs/<port_name>`.
The outputs of a worker follow the same pattern and are stored in the `output_dir` directory specified in the call args.
For each value to output, there is an entry for it in the caller arguments output mapping.

## Existing executors

Currently the following executors are available for the use

| Executor         |             Target Workers              | Enabled |                                        Notes                                         |
| ---------------- | :-------------------------------------: | :-----: | :----------------------------------------------------------------------------------: |
| UVExecutor       | Python based with dependency management |    ✔    |                           Default for python based workers                           |
| ShellExecutor    |                 Scripts                 |    ✔    |                                  Runs shell scripts                                  |
| StdInOut         |                 Scripts                 |    ✔    |                 Runs shell scripts with single input and output file                 |
| InMemoryExecutor |                 Python                  |    ✔    | Runs in the same memory spaces as the controller, does not work for external workers |
| SLURMExecutor    |                   Any                   |    ✔    |                        Wraps a command in a SLURM submission                         |
| PJSUBExecutor    |                   Any                   |    ✔    |                        Wraps a command in a PJSUB submission                         |
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
