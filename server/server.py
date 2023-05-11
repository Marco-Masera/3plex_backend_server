from flask import Flask, request,render_template
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

#Working dir is where temporary files will be stored before and during being processed
WORKING_DIR_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "working_dir")

@app.errorhandler(409 )
def job_already_submitted_exception(token):
    return f"Job with token {token} already submitted", 409 

@app.errorhandler(400)
def triplex_params_missing(token):
    return f"Cannot receive job - 3plex params missing or incomplete", 400

def parse_triplex_params(form):
    parameter_dict = {}
    parameter_dict['min_len'] = form['min_len']
    parameter_dict['max_len'] = form['max_len']
    parameter_dict['error_rate'] = form['error_rate']
    parameter_dict['guanine_rate'] = form['guanine_rate']
    parameter_dict['filter_repeat'] = form['filter_repeat']
    parameter_dict['consecutive_errors'] = form['consecutive_errors']
    parameter_dict['SSTRAND'] = form['SSTRAND']
    return parameter_dict

@app.post("/submit/<token>")
def submit_job(token):
    ssRNA_fasta = request.files['ssRNA_fasta']
    dsDNA_fasta = request.files['dsDNA_fasta']
    try:
        triplex_params = parse_triplex_params(request.form)
    except Exception:
        return triplex_params_missing(token)

    try:
        os.mkdir(os.path.join(WORKING_DIR_PATH, token))
    except FileExistsError:
        return job_already_submitted_exception(token)
    ssRNA_fasta.save(os.path.join(WORKING_DIR_PATH,token) + "/" + secure_filename(ssRNA_fasta.filename))
    dsDNA_fasta.save(os.path.join(WORKING_DIR_PATH,token) + "/" + secure_filename(dsDNA_fasta.filename))
    
    rna_fn = "".join(ssRNA_fasta.filename.split(".")[:-1])
    dna_fn = "".join(dsDNA_fasta.filename.split(".")[:-1])
    rule = f"snakemake -p -c1 working_dir/{token}/{rna_fn}__{dna_fn}__output.txt"
    config_ = " --config " + " ".join([f"{key}={triplex_params[key]}" for key in triplex_params.keys()])
    print(rule + " " + config_)
    return f"Job with token {token} received"
