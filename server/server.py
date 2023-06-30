from flask import Flask, request,render_template,Response
from werkzeug.utils import secure_filename
import os
import re
from server_config import *
from execute_rules_and_ping import call_on_close

app = Flask(__name__)


@app.errorhandler(409 )
def job_already_submitted_exception(token):
    return f"Job with token {token} already submitted", 409 

@app.errorhandler(400)
def config_params_missing(token):
    return f"Cannot receive job - 3plex params missing or incomplete", 400

def validate_input_params(input_string):
    if (input_string is None):
        return True
    pattern = r'^[a-zA-Z0-9-_.]+$'
    return re.match(pattern, input_string) is not None

def parse_config(triplex_params, other_params):
    parameter_dict = {}
    print(triplex_params)
    print(other_params)
    parameter_dict['min_length'] = triplex_params['min_len']
    parameter_dict['max_length'] = triplex_params['max_len']
    parameter_dict['error_rate'] = triplex_params['error_rate']
    parameter_dict['guanine_rate'] = triplex_params['guanine_rate']
    parameter_dict['filter_repeat'] = triplex_params['filter_repeat']
    parameter_dict['consecutive_errors'] = triplex_params['consecutive_errors']
    parameter_dict['SSTRAND'] = triplex_params['SSTRAND']
    for key in parameter_dict.keys():
        if (not validate_input_params(parameter_dict[key])):
            raise Exception()
    for key in other_params.keys():
        if (not validate_input_params(other_params[key])):
            raise Exception()
    stringified = '\n'.join([key+': ' + other_params[key] for key in other_params.keys()]) + "\ntriplexator:\n" + '\n'.join(['        ' + key+': ' + parameter_dict[key] for key in parameter_dict.keys()])
    return stringified

#Main API -> receive new job
@app.post("/submit/<token>")
def submit_job(token):
    additional_params = dict()
    #Read input files
    dsDNA_predefined = request.args.get('dsdna_target')
    if (dsDNA_predefined):
        additional_params["dsDNA_predefined"] = dsDNA_predefined
    else:
        dsDNA_fasta = request.files['dsDNA_fasta']
    ssRNA_fasta = request.files['ssRNA_fasta']
    species = request.args.get('species')
    if (species):
        additional_params["species"] = species

    dsDNA_filename = "dsDNA" #TODO spostare in server_config.py
    ssRNA_filename = "ssRNA" #TODO spostare in server_config.py

    
    try:
        #Parse config generates string to be saved in the config.yaml file
        #First argument contains the form with 3plex parameters, second is a dict of any additional param
        #that does not belong to "triplexator:"
        config_formatted = parse_config(request.form, additional_params)
    except Exception as e:
        return config_params_missing(token)
        
    #Create directory to execute the job
    output_dir = os.path.join(WORKING_DIR_PATH, token)
    if (output_dir[-1]=="/"): output_dir = output_dir[:-1]
    try:
        os.mkdir(output_dir)
    except FileExistsError:
        return job_already_submitted_exception(token)

    setting_up = f"cd {output_dir};\n"

    #Save files inside it
    
    if (ssRNA_fasta.filename.split('.')[-1]=="gz"):
        ssRNA_fasta.save(f"{output_dir}/{ssRNA_filename}.fa.gz")
        setting_up = setting_up + f"gzip -d {ssRNA_filename}.fa.gz;\n "
    else:
        ssRNA_fasta.save(f"{output_dir}/{ssRNA_filename}.fa")

    if (dsDNA_fasta is not None):
        dsDNA_fasta.save(f"{output_dir}/{dsDNA_filename}.fa")
        
    #Now need to build the string containing the command to execute in shell:
    #Setting up: prepare environment to execute the snakemake rules
    setting_up = setting_up + f"""{CONDA_SETUP} \n  conda activate {CONDA_ENV_PATH}
        export PATH={BIN_PATH}:$PATH:{BIOINFOTREE_ROOT};\n"""
    
    #Need to link files inside the working directory
    link_files = f"""
ln -s {SNAKEFILE_PATH} {output_dir};
ln -s {CONFIG_PATH} {output_dir}/config_general.yaml;
ln -s {CONFIG_SK} {output_dir}/config.smk;
echo \"{config_formatted}\" > {output_dir}/config.yaml;
"""

    #Prepare the snakemake command
    rule=f"""
snakemake -p {SLURM_CONFIG} \
    {ssRNA_filename}_ssmasked-{dsDNA_filename}.tpx.summary.add_zeros.gz \
    {ssRNA_filename}_ssmasked-{dsDNA_filename}.tpx.stability.gz \
    {ssRNA_filename}_secondary_structure.msgpack {ssRNA_filename}profile_range.msgpack\
    >> {output_dir}/STDOUT 2>>{output_dir}/STDERR
"""

    #Assemble the complete command
    command = f"{setting_up} {link_files} \n {rule} "

    #If no exceptions so far, can return a response
    response = Response( f"Job with token {token} received" )
    
    #After returning response, execute command
    @response.call_on_close
    def on_close():
        pid = os.fork()
        if (pid <= 0):
            print(f"Child process with pid {pid} starts 3plex")
            call_on_close(token, command, output_dir, ssRNA_filename, dsDNA_filename)
        else:
            print(f"Parent (worker) process with pid {pid} has finished its job")
        exit()
    return response
    


