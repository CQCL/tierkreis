# Tierkreis for HPC

If an HPC cluster provides a job submission system and a shared filesystem then we can use Tierkreis in the following way.

To take advantage of the HPC job submission system we use a specific implementation of the Tierkreis executor interface tailored to the system used in the cluster.
HPC Executors provide a simple interface to interact with submission systems of HPC Centers.
They work slightly differently compared to other executors as they wrap a command into a format accepted by the submission system.
The executors therefore only provide a bridging mechanism to transform the resource and job specification into a valid submission command.
On the requested resources, the command is treated as a regular submission with all the associated complexities.

To use the HPC cluster file system we just use the built-in Tierkreis `FileStorage` as usual.

## Job Spec

The `JobSpec` is a common description of the arguments required to submit a program to submission systems.
It provides a single entrypoint to any submission system without the need to rewrite job scripts at the cost of missing some custom flags.
Most configurations are optional, and will fall back to the configured default of the submission system.

- Job Name, to identify the job
- Command, the command to be run on the compute nodes
- Walltime, the maximum duration of the job
- Output path, output files for log messages
- Error path, error path for log messages
- Queue, the queue or resource to submit to
- Account, the entity to be charged/associated with the job

  queue: str | None = None
  extra_scheduler_args: dict[str, str | None] = Field(default_factory=dict)
  environment: dict[str, str] = Field(default_factory=dict)

It consists of the following sub specifications:

### Resources

### User

### MPI

### Containers

## SLURM

## PJSUB

## PBS

## Examples

In this section we give some examples based on commonly used job submission systems.
In cases where none of the following examples are useful, a custom executor can be provided to the Tierkreis library.

[pjsub on Fugaku](./hpc/pjsub-fugaku.md)
