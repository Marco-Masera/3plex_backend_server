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
def triplex_params_missing(token):
    return f"Cannot receive job - 3plex params missing or incomplete", 400

def validate_input_params(input_string):
    pattern = r'^[a-zA-Z0-9-_.]+$'
    return re.match(pattern, input_string) is not None

def parse_triplex_params(form):
    parameter_dict = {}
    parameter_dict['min_length'] = form['min_len']
    parameter_dict['max_length'] = form['max_len']
    parameter_dict['error_rate'] = form['error_rate']
    parameter_dict['guanine_rate'] = form['guanine_rate']
    parameter_dict['filter_repeat'] = form['filter_repeat']
    parameter_dict['consecutive_errors'] = form['consecutive_errors']
    parameter_dict['SSTRAND'] = form['SSTRAND']
    for key in parameter_dict.keys():
        if (not validate_input_params(parameter_dict[key])):
            raise Exception()
    stringified = "triplexator:\n" + '\n'.join(['        ' + key+': ' + parameter_dict[key] for key in parameter_dict.keys()])
    return stringified

#Main API -> receive new job
@app.post("/submit/<token>")
def submit_job(token):
    #Read input files
    dsdna_target = request.args.get('dsdna_target')
    ssRNA_fasta = request.files['ssRNA_fasta']
    species = request.args.get('species')
    if (species):
        if (species in GENOME_FASTA_FOR_SPECIES):
            species_fasta = GENOME_FASTA_FOR_SPECIES[species]
        else:
            return f"Species {species} not recognized", 404
    else:
        species_fasta = "none"

    try:
        triplex_params_formatted = parse_triplex_params(request.form)
    except Exception:
        return triplex_params_missing(token)
    
    if (dsdna_target is None):
        dsDNA_fasta = request.files['dsDNA_fasta']
    else:
        dsDNA_fasta = None
        #Verify file exists
        if ("/" in dsdna_target):
            return "Illegal character in dsDNA", 400
        dsdna_file_path = os.path.join(TARGET_DSDNA_PATH, dsdna_target)
        print(dsdna_file_path)
        if not (os.path.isfile(dsdna_file_path) or os.path.islink(dsdna_file_path)):
            return f"dsDNA {dsdna_target} does not exist", 404
    
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
    elif (dsdna_target is not None):
        dna_fn = "dsDNA"
        link_dna = f"ln -s {dsdna_file_path} {output_dir}/{dna_fn}.fa \n"

    #Now need to build the string containing the command to execute in shell:
    #Setting up: prepare environment to execute the snakemake rules
    setting_up = f"""{CONDA_SETUP} \n cd {output_dir} \n conda activate {CONDA_ENV_PATH}
        export PATH={BIN_PATH}:$PATH:{BIOINFOTREE_ROOT} \n cd {output_dir}"""

    #If ssRNA_fasta compressed need to add line to unzip it
    if (ssRNA_fasta.filename.split('.')[-1]=="gz"):
        rna_fn = ssRNA_fasta.filename.removesuffix(f".{ssRNA_fasta.filename.split('.')[-2]}.gz")
        setting_up = setting_up + f"\n gzip -d {ssRNA_fasta.filename} "
    else:
        rna_fn = ssRNA_fasta.filename.removesuffix(f".{ssRNA_fasta.filename.split('.')[-1]}")
    
    #Need to link files inside the working directory
    link_files = f"\n {link_dna} ln -s {SNAKEFILE_PATH} {output_dir} \n echo \"{triplex_params_formatted}\" > {output_dir}/config.yaml  \n cat {CONFIG_PATH} >> {output_dir}/config.yaml "
    #Prepare the snakemake command
    rule=f"snakemake -c12 --slurm --default-resources slurm_partition=low mem_mb=8000 --jobs 8 " \
        f"{rna_fn}_ssmasked-{dna_fn}.tpx.summary.add_zeros.gz " \
        f"{rna_fn}_ssmasked-{dna_fn}.tpx.stability.gz "  \
        f"{rna_fn}_secondary_structure.msgpack {rna_fn}profile_range.msgpack "
    
    #Add config_, containing triplex parameters
    config_ = f" --config species_fasta={species_fasta} "
    #Assemble the complete command
    command = f"{setting_up} {link_files} \n {rule} {config_} > {output_dir}/STDOUT 2>{output_dir}/STDERR"

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
    


