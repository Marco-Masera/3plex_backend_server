import hmac
import tempfile
import subprocess
from time import sleep
import shutil
import os
from server_config import *

def get_hashed(token):
    h = hmac.new(bytes(HMAC_KEY, 'utf-8'), msg=bytes(token, 'utf-8'), digestmod='sha256')
    digested = h.hexdigest()
    return digested

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
            shutil.rmtree(cwd)
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
    send_response = f"curl {SERVER_URL}/results/submitresult/{token}/ -F SUMMARY=@{output_dir}/{ssRNA}_ssmasked-{dsDNA}.tpx.summary.gz -F STABILITY=@{output_dir}/{ssRNA}_ssmasked-{dsDNA}.tpx.stability.gz -F PROFILE=@{output_dir}/{ssRNA}.profile_range.msgpack -F SECONDARY_STRUCTURE=@{output_dir}/{ssRNA}_secondary_structure.msgpack -F HTOKEN={htoken}"
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
    if (DELETE_JOB_DIRECTORY_AFTER_SUCCESS):
        r = execute_command(f"rm -rf {output_dir}", token)

def call_on_close(token, command, output_dir, rna_fn, dna_fn, DEBUG=False):
    hashed_token = get_hashed(token)
    return_code = execute_command(command, token)
    if (DEBUG==True):
        return (return_code==0)
    if (return_code==0):
        ping_job_succeeded(token, output_dir, rna_fn, dna_fn, hashed_token)
    else:
        ping_job_failed(token, output_dir, hashed_token)