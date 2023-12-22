import os
from  server_config_local import *

cores=32
jobs=20

DELETE_JOB_DIRECTORY_AFTER_SUCCESS = False
DEBUG_SKIP_SERVER_AUTHENTICATION = False
#BASE VARIABLES
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
TARGET_DSDNA_PATH = os.path.join(CURRENT_PATH, "local", "data", "target_dsdna")
SNAKEFILE_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "rules", "Snakefile")
CONFIG_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "config", "config_general.yaml")
CONFIG_SK = os.path.join(CURRENT_PATH, "3plex", "local", "config", "config.smk")
WORKING_DIR_PATH = os.path.join(CURRENT_PATH, "3plex", "dataset", "jobs")
BIN_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "bin")
CONDA_ENV_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "envs", "3plex") 
#Other params
def get_server_url(is_debug):
    print(f"Debug is {is_debug} - debug server: {FRONTEND_SERVER_URL_DEBUG} - standard: {FRONTEND_SERVER_URL}")
    if (is_debug==True):
        return FRONTEND_SERVER_URL_DEBUG
    else:
        return FRONTEND_SERVER_URL
#HMAC Secret key. Warning_ keep the key used in production safe
HMAC_KEY = "YOU_WISH_YOU_KNEW_MY_SECRET_KEY!"

#CONDA_SETUP is needed to run conda commands inside shell scripts executed from py
CONDA_SETUP = """__conda_setup="$('""" + CONDA_BASE + """/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f \"""" + CONDA_BASE + """/etc/profile.d/conda.sh" ]; then
        . \"""" + CONDA_BASE + """/etc/profile.d/conda.sh"
    else
        export PATH=\"""" + CONDA_BASE + """/bin/:$PATH"
    fi
fi"""


SLURM_CONFIG=f"--slurm --default-resources slurm_partition=low mem_mb=8000 --cores {cores} --jobs {jobs}"

transcript_fastas = transcript_fastas_local
tss_ref_bed = tss_ref_bed_local
genome_fasta = genome_fasta_local