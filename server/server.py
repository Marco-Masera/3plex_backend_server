from flask import Flask, request,render_template
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

#Working dir is where temporary files will be stored before and during being processed
WORKING_DIR_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "working_dir")

@app.errorhandler(409 )
def job_already_submitted_exception(token):
    return f"Job with token {token} already submitted", 409 

@app.post("/submit/<token>")
def submit_job(token):
    ssRNA_fasta = request.files['ssRNA_fasta']
    dsDNA_fasta = request.files['dsDNA_fasta']
    try:
        os.mkdir(os.path.join(WORKING_DIR_PATH, token))
    except FileExistsError:
        return job_already_submitted_exception(token)
    ssRNA_fasta.save(os.path.join(WORKING_DIR_PATH,token) + "/" + secure_filename(ssRNA_fasta.filename))
    dsDNA_fasta.save(os.path.join(WORKING_DIR_PATH,token) + "/" + secure_filename(dsDNA_fasta.filename))
    return f"Job with token {token} received"
