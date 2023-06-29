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
    pattern = r'^[a-zA-Z0-9-_.]+$'
    return re.match(pattern, input_string) is not None

def parse_config(triplex_params, other_params):
    parameter_dict = {}
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
    stringified = '\n'.join([key+': ' + other_params[key] for key in other_params.keys()]) + "\ntriplexator:\n" + '\n'.join(['        ' + key+': ' + parameter_dict[key] for key in parameter_dict.keys()])
    return stringified

#Main API -> receive new job
@app.post("/submit/<token>")
def submit_job(token):
    #Read input files
    dsDNA_predefined = request.args.get('dsdna_target')
    ssRNA_fasta = request.files['ssRNA_fasta']
    species = request.args.get('species')
    

    try:
        #Parse config generates string to be saved in the config.yaml file
        #First argument contains the form with 3plex parameters, second is a dict of any additional param
        #that does not belong to "triplexator:"
        config_formatted = parse_config(request.form, {"species": species})
    except Exception:
        return config_params_missing(token)
    
    if (dsDNA_predefined is None):
        dsDNA_fasta = request.files['dsDNA_fasta']
    else:
        dsDNA_fasta = None
        #Verify file exists
        if ("/" in dsDNA_predefined):
            return "Illegal character in dsDNA", 400
        dsDNA_file_path = os.path.join(TARGET_DSDNA_PATH, dsDNA_predefined)
        print(dsDNA_file_path)
        if not (os.path.isfile(dsDNA_file_path) or os.path.islink(dsDNA_file_path)):
            return f"dsDNA {dsDNA_predefined} does not exist", 404
    
    #Create directory to execute the job
    output_dir = os.path.join(WORKING_DIR_PATH, token)
    if (output_dir[-1]=="/"): output_dir = output_dir[:-1]
    try:
        os.mkdir(output_dir)
    except FileExistsError:
        return job_already_submitted_exception(token)


    #Save files inside it
    ssRNA_fasta.save(output_dir + "/" + secure_filename(ssRNA_fasta.filename))
    if (dsDNA_fasta is not None):
        dsDNA_fasta.save(output_dir + "/" + secure_filename(dsDNA_fasta.filename))
        dna_fn = dsDNA_fasta.filename.removesuffix(f".{dsDNA_fasta.filename.split('.')[-1]}")
        link_dna = ""
    elif (dsDNA_predefined is not None):
        dna_fn = "dsDNA"
        link_dna = f"ln -s {dsDNA_file_path} {output_dir}/{dna_fn}.fa; \n"

    #Now need to build the string containing the command to execute in shell:
    #Setting up: prepare environment to execute the snakemake rules
    setting_up = f"""{CONDA_SETUP} \n cd {output_dir} \n conda activate {CONDA_ENV_PATH}
        export PATH={BIN_PATH}:$PATH:{BIOINFOTREE_ROOT} \n cd {output_dir};\n"""

    #If ssRNA_fasta compressed need to add line to unzip it
    if (ssRNA_fasta.filename.split('.')[-1]=="gz"):
        rna_fn = ssRNA_fasta.filename.removesuffix(f".{ssRNA_fasta.filename.split('.')[-2]}.gz")
        setting_up = setting_up + f"gzip -d {ssRNA_fasta.filename}; "
    else:
        rna_fn = ssRNA_fasta.filename.removesuffix(f".{ssRNA_fasta.filename.split('.')[-1]}")
    
    #Need to link files inside the working directory
    link_files = f"""{link_dna}
ln -s {SNAKEFILE_PATH} {output_dir};
ln -s {CONFIG_PATH} {output_dir}/config_general.yaml;
ln -s {CONFIG_SK} {output_dir}/config.sk;
echo \"{config_formatted}\" > {output_dir}/config.yaml;
"""

    #Prepare the snakemake command
    rule=f"""
snakemake -p {SLURM_CONFIG} \
    {rna_fn}_ssmasked-{dna_fn}.tpx.summary.add_zeros.gz \
    {rna_fn}_ssmasked-{dna_fn}.tpx.stability.gz \
    {rna_fn}_secondary_structure.msgpack {rna_fn}profile_range.msgpack\
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
            call_on_close(token, command, output_dir, rna_fn, dna_fn)
        else:
            print(f"Parent (worker) process with pid {pid} has finished its job")
        exit()
    return response
    


