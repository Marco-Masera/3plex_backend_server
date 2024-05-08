#!/bin/bash

export PATH=/opt/mamba/bin:$PATH && \
export mamba_prefix=/opt/mamba
__conda_setup="$('/opt/mamba/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/opt/mamba/etc/profile.d/conda.sh" ]; then
        . "/opt/mamba/etc/profile.d/conda.sh"
    else
        export PATH="/opt/mamba/bin:$PATH"
    fi
fi
conda activate 3plex

working_directory="$1"
shift 1
snake_cmd=$1

export PATH=$PATH:/3plex/local/bin
export PRJ_ROOT=/3plex
snakemake $snake_cmd >> $working_directory/STDOUT 2>> $working_directory/STDERR