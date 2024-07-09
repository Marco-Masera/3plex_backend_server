# 3plex_backend_server

## Requirements
Only requirements are:
* python3 and pip
* git
* singularity >= 3.5
* slurm (must be able to run sbatch command)

## Build 3plex singularity container
The first step is to build the singularity container that will execute 3plex. 
* cd 3plex_container
* sudo sh build.sh
Note: this script uses the latest 3plex version in branch main.

## Setup configuration
The server configuration files are:
### server_config_local.py
* FRONTEND_SERVER_URL and FRONTEND_SERVER_URL_DEBUG: URl to the frontend server.
* bioinfotree and paths: paths to local files.
### server_config.py
This file contains a few parameters, including number of CPUs dedicated to jobs, the SLURM partition and the directory where to store temporary job data.
Most likely you won't have to modify them; in case the file is commented and it should be clear what each variable does.

## Launch server
### Create virtualenv
* cd server
* python3 -m venv env
* source env/bin/activate
* python3 -m pip install -r requirements.txt

### Launch server inside tmux (debug only)
* cd server
* source env/bin/activate
* gunicorn -w 6 -b :5000 'server:app'

### Launch as system service
* cd deploy
* make deploy