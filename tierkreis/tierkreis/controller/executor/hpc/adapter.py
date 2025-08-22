from functools import partial

from tierkreis.controller.executor.hpc.hpc_executor import HpcExecutor
from tierkreis.controller.executor.hpc.job_spec import (
    pjsub_large_spec,
    pjsub_small_spec,
)
from tierkreis.controller.executor.hpc.pbs import generate_pbs_script
from tierkreis.controller.executor.hpc.pjsub import generate_pjsub_script
from tierkreis.controller.executor.hpc.protocol import TemplateAdapter
from tierkreis.controller.executor.hpc.slurm import generate_slurm_script


PJSUB_ADAPTER = TemplateAdapter(generate_pjsub_script, "pjsub")
PBS_ADAPTER = TemplateAdapter(generate_pbs_script, "qsub")
SLURM_ADAPTER = TemplateAdapter(generate_slurm_script, "sbatch")

PJSUB_EXECUTOR_SMALL = partial(
    HpcExecutor, adapter=PJSUB_ADAPTER, spec=pjsub_small_spec()
)
PJSUB_EXECUTOR_LARGE = partial(
    HpcExecutor, adapter=PJSUB_ADAPTER, spec=pjsub_large_spec()
)
PBS_EXECUTOR = partial(HpcExecutor, adapter=PBS_ADAPTER)
SLURM_EXECUTOR = partial(HpcExecutor, adapter=SLURM_ADAPTER)
