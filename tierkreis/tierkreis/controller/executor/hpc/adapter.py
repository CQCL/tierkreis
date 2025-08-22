from functools import partial

from tierkreis.controller.executor.hpc.hpc_executor import HpcExecutor
from tierkreis.controller.executor.hpc.job_spec import (
    pjsub_large_spec,
    pjsub_small_spec,
)
from tierkreis.controller.executor.hpc.protocol import TemplateAdapter

_template_dir = "./tierkreis/tierkreis/controller/executor/hpc"

PJSUB_ADAPTER = TemplateAdapter("pjsub.jinja", "pjsub", template_dir=_template_dir)
PBS_ADAPTER = TemplateAdapter("pbs.jinja", "qsub", template_dir=_template_dir)
SLURM_ADAPTER = TemplateAdapter("slurm.jinja", "sbatch", template_dir=_template_dir)

PJSUB_EXECUTOR_SMALL = partial(
    HpcExecutor, adapter=PJSUB_ADAPTER, spec=pjsub_small_spec()
)
PJSUB_EXECUTOR_LARGE = partial(
    HpcExecutor, adapter=PJSUB_ADAPTER, spec=pjsub_large_spec()
)
PBS_EXECUTOR = partial(HpcExecutor, adapter=PBS_ADAPTER)
SLURM_EXECUTOR = partial(HpcExecutor, adapter=SLURM_ADAPTER)
