from flask import Flask, request,render_template,Response
from werkzeug.utils import secure_filename
import os
import re
import sys
from server_config import *
import pytest
import hmac
import datetime
from execute_rules_and_ping import call_on_close

app = Flask(__name__)
class BadParameterException(Exception):
    pass

def verify_hmac(token_, received_hmac):
    if (received_hmac is None):
        return False
    def get_time_based_otp(token, offset):
        time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)
        timestamp = f"{time:%Y-%m-%d %H}"
        h = hmac.new(bytes(HMAC_KEY, 'utf-8'), msg=bytes(token+timestamp, 'utf-8'), digestmod='sha256')
        digested = h.hexdigest()
        return digested == received_hmac
    return get_time_based_otp(token_, 0) or get_time_based_otp(token_, -1) or get_time_based_otp(token_, -2)
    

@pytest.fixture()
def client(app):
    return app.test_client()

@app.errorhandler(409 )
def job_already_submitted_exception(token):
    return f"Job with token {token} already submitted", 409 

@app.errorhandler(400)
def config_params_missing(token):
    return f"Cannot receive job - 3plex params missing or incomplete", 400

@app.errorhandler(400)
def internal_server_error(token):
    return f"Internal server error", 500

def validate_input_params(input_string):
    if (input_string is None):
        return True
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
    #parameter_dict['SSTRAND'] = triplex_params['SSTRAND']
    for key in parameter_dict.keys():
        if (not validate_input_params(parameter_dict[key])):
            raise BadParameterException()
    for key in other_params.keys():
        if (not validate_input_params(other_params[key])):
            raise BadParameterException()
    stringified = '\n'.join([key+': ' + other_params[key] for key in other_params.keys()]) + "\npato:\n" + '\n'.join(['        ' + key+': ' + parameter_dict[key] for key in parameter_dict.keys()])
    if (triplex_params['SSTRAND']):
        if (not validate_input_params(triplex_params['SSTRAND'])):
            raise BadParameterException() 
        stringified += f"\nRNAplfold:\n        single_strandedness_cutoff: {triplex_params['SSTRAND']}"
    return stringified

def prepare_job(token, request):
    additional_params = dict()

    #Read request files and parameters.........................................
    use_randomization = request.args.get('use_random')
    if (use_randomization is None):
        use_randomization = 0
    else:
        additional_params["randomization_num"] = use_randomization
        use_randomization = int(use_randomization)

    dsDNA_predefined = request.args.get('dsdna_target')
    if (dsDNA_predefined):
        additional_params["dsDNA_predefined"] = dsDNA_predefined
        dsDNA_fasta = None
    else:
        dsDNA_fasta = request.files['dsDNA_fasta']
        additional_params["dsDNA_predefined"] = "null"

    dsDNA_is_bed = request.args.get('is_bed')=="True"
    ssRNA_fasta = request.files['ssRNA_fasta']
    species = request.args.get('species')

    if (species):
        additional_params["species"] = species
    else:
        additional_params["species"] = "null"
    DEBUG = request.args.get('debug')
    dsDNA_filename = "dsDNA"
    ssRNA_filename = "ssRNA"

    #Parse config generates string to be saved in the config.yaml file
    #First argument contains the form with 3plex parameters, second is a dict of any additional param
    #that does not belong to "triplexator:"
    config_formatted = parse_config(request.form, additional_params)

    #Create directory to execute the job..................................
    output_dir = os.path.join(WORKING_DIR_PATH, token)
    if (output_dir[-1]=="/"): output_dir = output_dir[:-1]
    os.makedirs(output_dir)

    setting_up = f"cd {output_dir};\n"

    #Unzip ssRNA if zipped!
    if (secure_filename(ssRNA_fasta.filename).split('.')[-1]=="gz"):
        ssRNA_fasta.save(f"{output_dir}/{ssRNA_filename}.fa.gz")
        setting_up = setting_up + f"gzip -d {ssRNA_filename}.fa.gz;\n "
    else:
        ssRNA_fasta.save(f"{output_dir}/{ssRNA_filename}.fa")

    if (dsDNA_fasta is not None):
        if (dsDNA_is_bed):
            dsDNA_fasta.save(f"{output_dir}/{dsDNA_filename}.bed")
        else:
            dsDNA_fasta.save(f"{output_dir}/{dsDNA_filename}.fa")
    
        
    #Now need to build the string containing the command to execute in shell:
    #Setting up: prepare environment to execute the snakemake rules
    setting_up = setting_up + f"""{CONDA_SETUP} \n  conda activate {CONDA_ENV_PATH}
        export PATH={BIN_PATH}:$PATH;\n
        export PRJ_ROOT={os.path.join(CURRENT_PATH, "3plex")};\n"""
    #Need to link files inside the working directory
    link_files = f"""
ln -s {SNAKEFILE_PATH} {output_dir};
ln -s {CONFIG_PATH} {output_dir}/config_general.yaml;
ln -s {CONFIG_SK} {output_dir}/config.smk;
echo \"{config_formatted}\" > {output_dir}/config.yaml;
"""
    #-------------------------------------------------------
    #Prepare the snakemake command
    #Add rule for randomization
    if (use_randomization>0):
        random_rule = f"{ssRNA_filename}.profile_range.random.msgpack"
    else:
        random_rule = ""
    #Build rule   
    rule=f"""
snakemake -p {SLURM_CONFIG} \
    {ssRNA_filename}_ssmasked-{dsDNA_filename}.tpx.summary.add_zeros.gz \
    {ssRNA_filename}_ssmasked-{dsDNA_filename}.tpx.stability.gz \
    {ssRNA_filename}_secondary_structure.msgpack {ssRNA_filename}.profile_range.msgpack\
    {random_rule} >> {output_dir}/STDOUT 2>>{output_dir}/STDERR
"""
    rule_no_srun=f"""
snakemake -c1 \
    {ssRNA_filename}_ssmasked-{dsDNA_filename}.tpx.summary.add_zeros.gz \
    {ssRNA_filename}_ssmasked-{dsDNA_filename}.tpx.stability.gz \
    {ssRNA_filename}_secondary_structure.msgpack {ssRNA_filename}.profile_range.msgpack\
    {random_rule} >> {output_dir}/STDOUT 2>>{output_dir}/STDERR
"""

    #Assemble the complete command...............................................
    command = f"{setting_up} {link_files} \n {rule} "

    return {"command": command, token: "token", "output_dir": output_dir, 
        "ssRNA_filename": ssRNA_filename, "dsDNA_filename": dsDNA_filename, "random": use_randomization>0,
        "DEBUG": DEBUG}
    
#Main API -> receive new job
@app.post("/submit/<token>")
def submit_job(token):
    try:
        hmac = request.args.get('hmac')
        verified = verify_hmac(token, hmac)
        if (not DEBUG_SKIP_SERVER_AUTHENTICATION and not verified):
            return f"Cannot authenticate server", 401
        jobData = prepare_job(token, request)
    except FileExistsError:
        return job_already_submitted_exception(token)
    except BadParameterException as e:
        return config_params_missing(token)


    #If no exceptions so far, can return a response
    response = Response( f"Job with token {token} received" )
    output_dir = jobData["output_dir"]
    ssRNA = jobData["ssRNA_filename"]
    dsDNA = jobData["dsDNA_filename"]
    files_to_send = [
        {"name": "SUMMARY", "path": f"{output_dir}/{ssRNA}_ssmasked-{dsDNA}.tpx.summary.add_zeros.gz"},
        {"name": "STABILITY", "path": f"{output_dir}/{ssRNA}_ssmasked-{dsDNA}.tpx.stability.gz"},
        {"name": "PROFILE", "path": f"{output_dir}/{ssRNA}.profile_range.msgpack"},
        {"name": "SECONDARY_STRUCTURE", "path": f"{output_dir}/{ssRNA}_secondary_structure.msgpack"}
    ]
    if (jobData["random"]):
        files_to_send.append(
            {"name": "PROFILE_RANDOM", "path": f"{output_dir}/{ssRNA}.profile_range.random.msgpack"}
        )

    #After returning response, execute command
    @response.call_on_close
    def on_close():
        pid = os.fork()
        if (pid <= 0):
            print(f"Child process with pid {pid} starts 3plex")
            call_on_close(token, jobData["command"],jobData["output_dir"],jobData["ssRNA_filename"],jobData["dsDNA_filename"], jobData["random"], DEBUG=jobData['DEBUG'], files_to_send=files_to_send)
        else:
            print(f"Parent (worker) process with pid {pid} has finished its job")
        exit()
    return response


def prepare_job_promoter_stability(token, request):
    additional_params = dict()
    ssRNA_fasta = request.files['ssRNA_fasta']
    species = request.args.get('species')
    genes_all = request.form["genes_all"]
    genes_interest = request.form["genes_interest"]

    if (species):
        additional_params["species"] = species
    else:
        additional_params["species"] = "null"
    DEBUG = request.args.get('debug')
    dsDNA_filename = "dsDNA"
    ssRNA_filename = "ssRNA"

    #Parse config generates string to be saved in the config.yaml file
    #First argument contains the form with 3plex parameters, second is a dict of any additional param
    #that does not belong to "triplexator:"
    config_formatted = parse_config(request.form, additional_params)
    config_formatted = config_formatted + f"""
promoter_tpx_stability_test:
        ssRNA: ssRNA.fa
        genes_all: genes_all.txt
        genes_of_interest: genes_of_interest.txt
        score: 
                - Stability_best
                - Stability_norm
        gsea:
                max_genes_in_set: 10000
                min_genes_in_set: 5
                nperm: 1000
                gsea_weight: 0
genome_fasta: {genome_fasta}
tss_ref_bed: {tss_ref_bed}
transcript_fastas: {transcript_fastas}

    """
    #Create directory to execute the job..................................
    output_dir = os.path.join(WORKING_DIR_PATH, token)
    if (output_dir[-1]=="/"): output_dir = output_dir[:-1]
    os.makedirs(output_dir)

    setting_up = f"cd {output_dir};\n"

    #Unzip ssRNA if zipped!
    if (secure_filename(ssRNA_fasta.filename).split('.')[-1]=="gz"):
        ssRNA_fasta.save(f"{output_dir}/{ssRNA_filename}.fa.gz")
        setting_up = setting_up + f"gzip -d {ssRNA_filename}.fa.gz;\n "
    else:
        ssRNA_fasta.save(f"{output_dir}/{ssRNA_filename}.fa")
    #Export genes list
    with open(f"{output_dir}/genes_all.txt", "w") as genes_all_file:
        genes_all_file.write("\n".join(genes_all))
    with open(f"{output_dir}/genes_of_interest.txt", "w") as genes_interest_file:
        genes_interest_file.write("\n".join(genes_interest))
        
    #Now need to build the string containing the command to execute in shell:
    #Setting up: prepare environment to execute the snakemake rules
    setting_up = setting_up + f"""{CONDA_SETUP} \n  conda activate {CONDA_ENV_PATH}
        export PATH={BIN_PATH}:$PATH;\n
        export PRJ_ROOT={os.path.join(CURRENT_PATH, "3plex")};\n"""
    #Need to link files inside the working directory
    link_files = f"""
ln -s {SNAKEFILE_PATH} {output_dir};
ln -s {CONFIG_PATH} {output_dir}/config_general.yaml;
ln -s {CONFIG_SK} {output_dir}/config.smk;
echo \"{config_formatted}\" > {output_dir}/config.yaml;
"""
    #Build rule   
    rule=f"snakemake -p {SLURM_CONFIG} run_promoter_tpx_stability_test --report report.html >> {output_dir}/STDOUT 2>>{output_dir}/STDERR"

    #Assemble the complete command...............................................
    command = f"{setting_up} {link_files} \n {rule} "

    return {"command": command, token: "token", "output_dir": output_dir, 
        "ssRNA_filename": ssRNA_filename, "DEBUG": DEBUG}

#Receive new promoter_stability test job
@app.post("/submit_promoter_test/<token>")
def submit_job_promoter_stability_test(token):
    try:
        hmac = request.args.get('hmac')
        verified = verify_hmac(token, hmac)
        if (not DEBUG_SKIP_SERVER_AUTHENTICATION and not verified):
            return f"Cannot authenticate server", 401
        jobData = prepare_job_promoter_stability(token, request)
    except FileExistsError:
        return job_already_submitted_exception(token)
    except BadParameterException as e:
        return config_params_missing(token)


    #If no exceptions so far, can return a response
    response = Response( f"Job with token {token} received" )

    files_to_send = [
        #{"name": "SUMMARY", "path": f"{output_dir}/{ssRNA}_ssmasked-{dsDNA}.tpx.summary.add_zeros.gz"},
    ]
    """
    ssRNA_ssmasked-genes_all.tss.tpx.stability.gz
    ssRNA_ssmasked-genes_all.tss.tpx.summary.add_zeros.gz
    ssRNA_Stability_best_rnk.gz
    ssRNA_Stability_norm_rnk.gz
    results/ssRNA/
        Stability_best and Stability_norm
            fgseaRes.tsv
            leading_edge.tsv
            enrichment_plot.png
            stability_comp_boxplot.png
            stability_comp.tsv
    """

    #After returning response, execute command
    @response.call_on_close
    def on_close():
        pid = os.fork()
        if (pid <= 0):
            print(f"Child process with pid {pid} starts 3plex")
            call_on_close(token, jobData["command"],jobData["output_dir"],jobData["ssRNA_filename"],jobData["dsDNA_filename"], jobData["random"], DEBUG=jobData['DEBUG'], files_to_send=files_to_send)
        else:
            print(f"Parent (worker) process with pid {pid} has finished its job")
        exit()
    return response

def run_test(token, request):
    try:
        jobData = prepare_job(token, request)
    except FileExistsError:
        sys.stderr.write("Test already executed\n")
        return False
    except BadParameterException as e:
        sys.stderr.write("Bad params\n")
        return False

    return call_on_close(token, jobData["command"],jobData["output_dir"],jobData["ssRNA_filename"],jobData["dsDNA_filename"], TEST=True)

def run_test_promoter_stability(token, request):
    try:
        jobData = prepare_job_promoter_stability(token, request)
    except FileExistsError:
        sys.stderr.write("Test already executed\n")
        return False
    except BadParameterException as e:
        sys.stderr.write("Bad params\n")
        return False

    return call_on_close(token, jobData["command"],jobData["output_dir"],jobData["ssRNA_filename"], None, TEST=True)