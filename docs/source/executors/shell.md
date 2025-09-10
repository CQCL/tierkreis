# Shell Executors

Shell Executors allow Tierkreis to dispatch almost any unix compatible program in a shell environment.
Currently, there are two ways to run the shell that differ in how you provide the arguments and. how the outputs are read.

## Shell Executor

The `ShellExecutor` uses environment variables to handle in and output.

## StdInOut

`StdInOut` reads the first node input from `stdin` and writes to the first output to `stdout`.
