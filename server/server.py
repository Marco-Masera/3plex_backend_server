from flask import Flask, request,render_template,Response
from werkzeug.utils import secure_filename
import tempfile
import hmac
import subprocess
from time import sleep
import shutil
import json
import os
import re

app = Flask(__name__)

#Working dir is where temporary files will be stored before and during being processed
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
SNAKEFILE_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "rules", "Snakefile")
CONFIG_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "config", "config_v1.yaml")
WORKING_DIR_PATH = os.path.join(CURRENT_PATH, "3plex", "working_dir")
BIN_PATH = os.path.join(CURRENT_PATH, "3plex", "local", "bin")
BIOINFOTREE_ROOT = "/home/reference_data/bioinfotree/local/bin/"
CONDA_ENV_PATH = "/home/imoliner/.conda/envs/3plex_test/"
#Other params
SERVER_URL = "http://192.168.186.10:8001"
#HMAC Secret key. Warning_ keep the key used in production safe
HMAC_KEY = "YOU_WISH_YOU_KNEW_MY_SECRET_KEY!"


@app.errorhandler(409 )
def job_already_submitted_exception(token):
    return f"Job with token {token} already submitted", 409 

@app.errorhandler(400)
def triplex_params_missing(token):
    return f"Cannot receive job - 3plex params missing or incomplete", 400

def get_hashed(token):
    h = hmac.new(bytes(HMAC_KEY, 'utf-8'), msg=bytes(token, 'utf-8'), digestmod='sha256')
    digested = h.hexdigest()
    return digested

def validate_input_params(input_string):
    #return True
    pattern = r'^[a-zA-Z0-9-_.]+$'
    return re.match(pattern, input_string) is not None

def parse_triplex_params(form):
    parameter_dict = {}
    parameter_dict['min_len'] = form['min_len']
    parameter_dict['max_len'] = form['max_len']
    parameter_dict['error_rate'] = form['error_rate']
    parameter_dict['guanine_rate'] = form['guanine_rate']
    parameter_dict['filter_repeat'] = form['filter_repeat']
    parameter_dict['consecutive_errors'] = form['consecutive_errors']
    parameter_dict['SSTRAND'] = form['SSTRAND']
    for key in parameter_dict.keys():
        if (not validate_input_params(parameter_dict[key])):
            raise Exception()
    return parameter_dict


def execute_command(cmd, path):
    return_code = -1
    print(f"\nExecuting task: {cmd}\n")
    try:
        cwd = tempfile.mkdtemp(path)
        with subprocess.Popen(['/bin/bash', '-c', cmd], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, bufsize=1) as p:
            print("Stdout:")
            for line in p.stdout:
                print(line)
            print("Stderr:")
            for line in p.stderr:
                print(line)
            return_code = p.wait()
    finally:
        try:
            shutil.rmtree(cwd)  # delete directory
        except Exception:
            pass
    return return_code

         
def ping_job_failed(token, output_dir, htoken):
    send_response = f"curl {SERVER_URL}/results/submiterror/{token}/ -F STDOUT=@{output_dir}/STDOUT -F STDERR=@{output_dir}/STDERR -F HTOKEN={htoken}"
    tries = 0
    while True:
        r = execute_command(f"{send_response}", token)
        if (r == 0):
            break
        if (tries >= 288):
            break
        tries += 1
        sleep(300)
    #r = execute_command(f"rm -rf {output_dir}", token)

def ping_job_succeeded(token, output_dir, ssRNA, dsDNA, htoken):
    tries = 0
    send_response = f"curl {SERVER_URL}/results/submitresult/{token}/ -F SUMMARY=@{output_dir}/{ssRNA}_ssmasked-{dsDNA}.tpx.summary.gz -F STABILITY=@{output_dir}/{ssRNA}_ssmasked-{dsDNA}.tpx.stability.gz -F PROFILE=@{output_dir}/profile_range.msgpack -F SECONDARY_STRUCTURE=@{output_dir}/{ssRNA}_secondary_structure.msgpack -F HTOKEN={htoken}"
    while True:
        r = execute_command(send_response, token)
        if (r == 0):
            break
        if (tries >= 288):
            execute_command(f'ECHO "Network error" > {output_dir}/STDERR', token)
            ping_job_failed(token, output_dir)
            break
        tries += 1
        sleep(300)
    r = execute_command(f"rm -rf {output_dir}", token)


@app.post("/submit/<token>")
def submit_job(token):
    ssRNA_fasta = request.files['ssRNA_fasta']
    dsDNA_fasta = request.files['dsDNA_fasta']
    try:
        triplex_params = parse_triplex_params(request.form)
    except Exception:
        return triplex_params_missing(token)
    
    output_dir = os.path.join(WORKING_DIR_PATH, token)
    if (output_dir[-1]=="/"): output_dir = output_dir[:-1]
    
    try:
        os.mkdir(output_dir)
    except FileExistsError:
        return job_already_submitted_exception(token)


    ssRNA_fasta.save(output_dir + "/" + secure_filename(ssRNA_fasta.filename))
    dsDNA_fasta.save(output_dir + "/" + secure_filename(dsDNA_fasta.filename))

    dna_fn = dsDNA_fasta.filename.removesuffix(f".{dsDNA_fasta.filename.split('.')[-1]}")

    #Need to build the command to run 3plex
    conda_setup = """__conda_setup="$('/opt/conda/miniconda3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/opt/conda/miniconda3/etc/profile.d/conda.sh" ]; then
        . "/opt/conda/miniconda3/etc/profile.d/conda.sh"
    else
        export PATH="/opt/conda/miniconda3/bin:$PATH"
    fi
fi"""
    setting_up = f"{conda_setup} \n cd {output_dir} \n conda activate {CONDA_ENV_PATH} \n export PATH={BIN_PATH}:$PATH:{BIOINFOTREE_ROOT} \n cd {output_dir}"
    #Is ssRNA_fasta compressed?
    ssRNA_fasta_compressed = False
    if (ssRNA_fasta.filename.split('.')[-1]=="gz"):
        ssRNA_fasta_compressed = True
        rna_fn = ssRNA_fasta.filename.removesuffix(f".{ssRNA_fasta.filename.split('.')[-2]}")
        setting_up = setting_up + f"\n gzip -d {ssRNA_fasta.filename} "
    else:
        rna_fn = ssRNA_fasta.filename.removesuffix(f".{ssRNA_fasta.filename.split('.')[-1]}")
    
    link_files = f"\n ln -s {SNAKEFILE_PATH} {output_dir} \n ln -s {CONFIG_PATH} {output_dir}/config.yaml "
    rule=f"snakemake -c1 --slurm --default-resources slurm_partition=low mem_mb=8000 --jobs 10 {rna_fn}_ssmasked-{dna_fn}.tpx.summary.add_zeros.gz {rna_fn}_ssmasked-{dna_fn}.tpx.stability.gz  {rna_fn}_secondary_structure.msgpack {rna_fn}profile_range.msgpack"
    config_ = " --config " + " ".join([f"{key}={triplex_params[key]}" for key in triplex_params.keys()])
    response = Response( f"Job with token {token} received" )
    
    @response.call_on_close
    def on_close():
        hashed_token = get_hashed(token)
        print(f"{setting_up} {link_files} \n {rule} {config_} > {output_dir}/STDOUT 2>{output_dir}/STDERR")
        return_code = execute_command(f"{setting_up} {link_files} \n {rule} {config_} > {output_dir}/STDOUT 2>{output_dir}/STDERR", token)
        if (return_code==0):
            ping_job_succeeded(token, output_dir, rna_fn, dna_fn, hashed_token)
        else:
            ping_job_failed(token, output_dir, hashed_token)
    
    return response
    


