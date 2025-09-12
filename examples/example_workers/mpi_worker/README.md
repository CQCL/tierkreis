# mpi_worker

To showcase how to include cpp applications into tierkreis.

## Use as a worker

1. Define the interface in as a Typespec
2. Generate the stubs from the spec
3. Use the stubs to type the tasks
4. Invoke with a custom executor that runs mpi

## MPI project

To build and run, make sure you have `mpi` and `n_lohmann/json` installed on your machine.
Make sure the target will have the same name as the interface defined in the typespec.

```sh
mkdir build && cd build
cmake ..
make
```

## Run the example

Make sure to build the binary in the build folder.
After you can invoke: `uv run mpi_graph.py`
