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
            """print("Stdout:")
            for line in p.stdout:
                print(line)
            print("Stderr:")
            for line in p.stderr:
                print(line)"""
            return_code = p.wait()
    finally:
        try:
            shutil.rmtree(cwd)
        except Exception:
            pass
    return return_code
 
def ping_job_failed(token, output_dir, htoken, SERVER_URL_G, api_name="submiterror"):
    send_response = f"curl {SERVER_URL_G}/results/{api_name}/{token}/ -F STDOUT=@{output_dir}/STDOUT -F STDERR=@{output_dir}/STDERR -F HTOKEN={htoken}"
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

def ping_job_succeeded(token, output_dir, htoken, use_random=False, SERVER_URL_G="", files_to_send={}, api_name="submitresult"):
    tries = 0
    send_files_command = " ".join(
        [f"-F {f['name']}=@{f['path']}" for f in files_to_send]
    )
    send_response = f"curl {SERVER_URL_G}/results/{api_name}/{token}/ {send_files_command} -F HTOKEN={htoken}"
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

def call_on_close(token, command, output_dir, use_random=False, DEBUG=False, TEST=False, files_to_send={}, api_names = ["submitresult", "submiterror"]):
    use_server = get_server_url(DEBUG)
    hashed_token = get_hashed(token)
    return_code = execute_command(command, token)
    if (TEST==True):
        return (return_code==0)
    if (return_code==0):
        ping_job_succeeded(token, output_dir, hashed_token, use_random=use_random, SERVER_URL_G=use_server, files_to_send=files_to_send, api_name=api_names[0])
    else:
        ping_job_failed(token, output_dir, hashed_token, use_server,  api_name=api_names[1])