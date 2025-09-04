# How to run the slurm test

For setup see the [README](README.md).
In short:

- install docker
- From `infra/slurm_local`
  - make the local sbatch script executable `chmod +x sbatch`
  - build the containers with `docker compose build`
  - ensure the containers are running `docker compose up -d`
  - This will mount `~/.tierkreis` inside the containers on `/root/tierkreis/` and the tierkreis directory to `/tierkreis`

To run the test we emulate `sbatch`.
The devenv contains a script for this (same as the sbatch script), if you want, link it to a location in your path to make it available elsewhere.

```
#!/bin/bash
if [ -z "$1" ]; then
    echo "Usage: sbatch <path_to_slurm_script>"
    echo "Any further arguments will be discarded"
    exit 1
fi
SCRIPT_FILE=$(basename "$1")
docker cp "$1" slurmctld:/data/"$SCRIPT_FILE"
docker exec slurmctld sbatch --chdir=/data /data/"$SCRIPT_FILE"
```

Run the test:

```
pytest tierkreis/tests/executor/test_hpc_executor.py
```

**Caveats**:

- it seems jobfiles don't get deleted correctly, logging is also not working as intended
