# How to run the slurm test

For setup see the [README](README.md).
In short:

- install docker
- From `infra/slurm_local`
  - create a symlink `ln -s ~/.tierkreis /tmp/tierkreis`
  - build the containers with `docker compose build`
  - ensure the containers are running `docker compose up -d`
  - This will mount `/tmp/tierkreis` inside the containers on `/tmp/tierkreis/`

To run the test we emulate `sbatch`.
The devenv contains a script for this, if you want link it to a location in your path to make it available elsewhere.

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
