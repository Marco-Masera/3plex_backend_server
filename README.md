# 3plex_backend_server

## Requirements
Only requirements are:
* python3 and pip
* git
* singularity
* slurm (must be able to run sbatch command)

## Build 3plex singularity container
The first step is to build the singularity container that will execute 3plex. 
* cd 3plex_singularity
* sudo sh build.sh

## Setup configuration
TODO

## Create virtualenv
* python3 -m venv env
* source env/bin/activate
* python3 -m pip install -r requirements.txt