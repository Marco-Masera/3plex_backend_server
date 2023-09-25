import os
from  server_config_local import *

cores=32
jobs=10

DELETE_JOB_DIRECTORY_AFTER_SUCCESS = False

#BASE VARIABLES
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
TARGET_DSDNA_PATH = os.path.join(CURRENT_PATH, "local", "data", "target_dsdna")
SNAKEFILE_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "rules", "Snakefile")
CONFIG_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "config", "config_v1_for_server.yaml")
CONFIG_SK = os.path.join(CURRENT_PATH, "3plex", "local", "config", "config.smk")
WORKING_DIR_PATH = os.path.join(CURRENT_PATH, "3plex", "dataset", "jobs")
BIN_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "bin")
CONDA_ENV_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "envs", "3plex_test") 
#Other params
SERVER_URL = FRONTEND_SERVER_URL
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