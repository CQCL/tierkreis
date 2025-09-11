# Tierkreis for HPC

If an HPC cluster provides a job submission system and a shared filesystem then we can use Tierkreis in the following way.

To take advantage of the HPC job submission system we use a specific implementation of the Tierkreis executor interface tailored to the system used in the cluster.
In this section we give some examples based on commonly used job submission systems.
In cases where none of the following examples are useful, a custom executor can be provided to the Tierkreis library.

To use the HPC cluster file system we just use the built-in Tierkreis `FileStorage` as usual.

[pjsub on Fugaku](./hpc/pjsub-fugaku.md)
