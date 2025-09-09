# mpi_worker

To showcase how to include cpp applications into tierkreis.

## MPI project

To build and run, make sure you have mpi installed on your machine.

```sh
mkdir build && cd build
cmake ..
make
cp trk_mpi_worker ../example
mpirun -n 4 tkr_mpi_worker example_def.json
```

## Use as a worker

1. Define the interface in as a Typespec
2. Generate the stubs from the spec
3. include in the workers
