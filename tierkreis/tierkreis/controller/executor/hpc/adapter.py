from tierkreis.controller.executor.hpc.protocol import TemplateAdapter

_template_dir = "./tierkreis/tierkreis/controller/executor/hpc"

PJSUB_ADAPTER = TemplateAdapter("pjsub.jinja", "pjsub", template_dir=_template_dir)
PBS_ADAPTER = TemplateAdapter("pbs.jinja", "qsub", template_dir=_template_dir)
SLURM_ADAPTER = TemplateAdapter("slurm.jinja", "sbatch", template_dir=_template_dir)
