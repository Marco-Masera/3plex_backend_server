import os
from  server_config_local import *

#DEBUG OPTIONS
DELETE_JOB_DIRECTORY_AFTER_SUCCESS = True
DEBUG_SKIP_SERVER_AUTHENTICATION = False
#In quiet mode, the server prints only when something goes wrong. Without quiet mode it prints every command it runs.
QUIET_MODE = True

#RELATIVE PATH VARIABLES - these are unlikely to be changed
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
SNAKEFILE_PATH = os.path.join(CURRENT_PATH, "3plex_container", "3plex", "local", "rules", "Snakefile")
CONFIG_PATH = os.path.join(CURRENT_PATH, "3plex_container","3plex", "local", "config", "config_general.yaml")
CONTAINER_PATH = os.path.join(CURRENT_PATH, "3plex_container","3plex_cont")
CONFIG_SK = os.path.join(CURRENT_PATH, "3plex_container","3plex", "local", "config", "config.smk")
CONTAINER_PATH = os.path.join(CURRENT_PATH, "3plex_container", "container")
TRIPLEX_PATH = os.path.join(CURRENT_PATH, "3plex_container", "3plex")
#Modify this to specify where to keep temporary job data
WORKING_DIR_PATH = os.path.join(CURRENT_PATH, "job_data")

#SLURM CONFIGURATION
SNAKEMAKE_N_CPU = 32 #N. cpu to use
SLURM_PARTITION="low" #Slurm partition

#Do not change
def get_server_url(is_debug):
    if (is_debug==True or is_debug=="True"):
        return FRONTEND_SERVER_URL_DEBUG
    else:
        return FRONTEND_SERVER_URL
#HMAC Secret key. Warning_ keep the key used in production safe
HMAC_KEY = "YOU_WISH_YOU_KNEW_MY_SECRET_KEY!"

transcript_fastas = transcript_fastas_local
tss_ref_bed = tss_ref_bed_local
genome_fasta = genome_fasta_local
BIOINFOTREE_PATH=bioinfotree