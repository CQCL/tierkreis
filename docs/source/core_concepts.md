# Core Concepts in Tierkreis

## Program model

In Tierkreis, a computation is represented as a sequence of tasks comprising a workflow.
They are combined in a directed acyclic graph (DAG), where each task is represented by a node.
Edges carry the data of a computation instance.
The data dependencies induce a partial order of execution, which allows parallel and asynchronous execution. 
As a result a computation can be distributed easily and run on different types of hardware including remote (cloud) and onsite:
-  CPUs
-  GPUs
-  QPUs

### Tasks

Tasks are the basic building blocks of a workflow.
They are independent and loosely coupled and represent an atomic operation in the workflow.
Still, they can consume large amounts of resources and running time.
While they can maintain state for the duration of their lifetime in the context of the workflow they are stateless.
They simply act on their inputs and produce outputs, which are linked to other tasks.

### Workflows

Workflows are a composition of tasks, that provide the control structure and data flow.
Higher-order constructions like nesting graphs, folding and mapping can be used to create complex workflows.
From the data dependencies, the runtime environment can infer which tasks it needs to run and can do so in parallel manner.

## Execution model

The second part of Tierkreis is the execution model, which is baked into the runtime environment.
It is responsible for the orchestration and the proper execution of the tasks specified in a workflow.
The goal is to distribute tasks over the available resources, based on the capabilities of each resource.

### Controller

The controller is responsible for the execution of the entire workflow, maintaining the global state and checking the progress.
It checks the state of the individual tasks and decides what to run next based on the given data availability.
In case of an error, the controller interrupts the progress such that a user can interfere.
Further, the controller interacts with all the other components of the system:
- It assigns executors to workers according to their requirements
- It dispatches workers once their inputs are ready
- It interfaces with the storage layer

A resulting feature is that computation can be interrupted and resumed at any point, without losing significant progress.
The controller also validates the workflow to ensure each node can be implemented by a combination of worker and executor.

### Storage

The storage layer is an abstraction of the state of the computation.
It stores the information of individual tasks such as their definition, their inputs (dependencies), and their status.
The actual implementation can be a file system, a database or cloud storage.

### Worker

A worker implements *atomic* functionalities that will not be broken further by the controller.
These functionalities are unrestricted and can be implemented in any language as long as they correctly implement the interface defined by the storage layer.
Typically, workers represent more expensive operations that run asynchronously.

### Executor

An executor runs a single worker tasks.
It possesses the knowledge about its environment and how to run programs there in a specific way.
For example, the `UVExecutor <tbd>`_ can run python programs locally by building them as a packaged executable.
Multiple executors could handle the same worker in different environments, the choice is then up to the controller.
