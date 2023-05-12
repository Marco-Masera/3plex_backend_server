from flask import Flask, request,render_template,Response
from werkzeug.utils import secure_filename
import tempfile
import subprocess
from time import sleep
import shutil
import json
from threading import Thread
import os
import traceback
from werkzeug.wsgi import ClosingIterator

app = Flask(__name__)

#Working dir is where temporary files will be stored before and during being processed
CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
WORKING_DIR_PATH = os.path.join(CURRENT_PATH, "working_dir")

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


def execute_command(cmd, path):
    return_code = -1
    print(f"Executing task: {cmd}")
    try:
        cwd = tempfile.mkdtemp(path)
        with subprocess.Popen(['/bin/bash', '-c', cmd], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, bufsize=1) as p:
            print("\n\nStdout:\n")
            for line in p.stdout:
                print(line, end='')
            print("\n\nStderr:\n")
            for line in p.stderr:
                print(line, end='')
            return_code = p.wait()
            print(f"Return code: {return_code}")
    finally:
        try:
            shutil.rmtree(cwd)  # delete directory
        except Exception:
            pass
    return return_code

         
def ping_job_failed(token, stderr=""):
    js = {"reason": stderr}
    json_string = json.dumps(js)
    send_response = f"curl  -X POST -H \"Content-Type: application/json\" -d '{json_string}' http://192.168.186.10:8001/results/submiterror/{token}/"
    execute_command(f"cd {CURRENT_PATH} \n source env/bin/activate \n {send_response}", token)
    execute_command(f"cd {CURRENT_PATH} \n source env/bin/activate \n rm -rf $PWD/working_dir/{token}/", token)

def ping_job_succeeded(token, ssRNA, dsDNA):
    tries = 0
    send_response = f"curl -F SUMMARY=@$PWD/working_dir/{token}/{ssRNA}_ssmasked-{dsDNA}.tpx.summary.gz -F STABILITY=@$PWD/working_dir/{token}/{ssRNA}_ssmasked-{dsDNA}.tpx.stability.gz  http://192.168.186.10:8001/results/submitresult/{token}/"
    while True:
        r = execute_command(f"cd {CURRENT_PATH} \n source env/bin/activate \n {send_response}", token)
        if (r == 0):
            break
        if (tries >= 600):
            ping_job_failed(token, "Cannot send data back to frontend")
            return;
        tries += 1
        sleep(120)
    r = execute_command(f"cd {CURRENT_PATH} \n source env/bin/activate \n rm -rf $PWD/working_dir/{token}/", token)



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
    
    rna_fn = ssRNA_fasta.filename.removesuffix(f".{ssRNA_fasta.filename.split('.')[-1]}")
    dna_fn = dsDNA_fasta.filename.removesuffix(f".{dsDNA_fasta.filename.split('.')[-1]}")
    
    rule = f"snakemake -p -c1 working_dir/{token}/{rna_fn}__{dna_fn}__output.txt"
    config_ = " --config " + " ".join([f"{key}={triplex_params[key]}" for key in triplex_params.keys()])
    #execute_task(rule, config_, token)
    #Thread(target = execute_task(rule, config_, token)).start()
    response = Response( f"Job with token {token} received" )
    @response.call_on_close
    def on_close():
        return_code = execute_command(f"cd {CURRENT_PATH} \n source env/bin/activate \n {rule} {config_}", token)
        if (return_code==0):
            ping_job_succeeded(token, rna_fn, dna_fn)
        else:
            ping_job_failed(token)

    return response


