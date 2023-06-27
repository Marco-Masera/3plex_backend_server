import os

threads=16

DELETE_JOB_DIRECTORY_AFTER_SUCCESS = False

#Genome Fasta files for each species
GENOME_FASTA_FOR_SPECIES = {
    "hsapiens": "/home/reference_data/bioinfotree/task/gencode/dataset/hsapiens/42/GRCh38.primary_assembly.genome.fa",
    "mmusculus": "/home/reference_data/bioinfotree/task/gencode/dataset/mmusculus/TODO"
}

#BASE VARIABLES
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
TARGET_DSDNA_PATH = os.path.join(CURRENT_PATH, "local", "data", "target_dsdna")#local/data/target_dsdna
SNAKEFILE_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "rules", "Snakefile")
CONFIG_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "config", "config_v1_for_server.yaml")
WORKING_DIR_PATH = os.path.join(CURRENT_PATH, "3plex", "dataset", "jobs")
BIN_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "bin")
BIOINFOTREE_ROOT = "/home/reference_data/bioinfotree/local/bin/"
CONDA_ENV_PATH = "3plex_test" #"/home/imoliner/.conda/envs/3plex_test/"
#Other params
SERVER_URL = "http://192.168.186.10:8001"
#HMAC Secret key. Warning_ keep the key used in production safe
HMAC_KEY = "YOU_WISH_YOU_KNEW_MY_SECRET_KEY!"

#CONDA_SETUP is needed to run conda commands inside shell scripts executed from py
CONDA_SETUP = """__conda_setup="$('/opt/conda/miniconda3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/opt/conda/miniconda3/etc/profile.d/conda.sh" ]; then
        . "/opt/conda/miniconda3/etc/profile.d/conda.sh"
    else
        export PATH="/opt/conda/miniconda3/bin:$PATH"
    fi
fi"""


SLURM_CONFIG=f"--slurm --default-resources slurm_partition=low mem_mb=8000 --jobs {threads}"