import os, sys
import argparse
import shutil
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import run_test, run_test_promoter_stability
from server_config import WORKING_DIR_PATH
from werkzeug.datastructures import FileStorage
import yaml
import requests

class DotDict():
    def from_dict(dict_):
        d = DotDict()
        d.dict = dict_
        return d
    def __getattr__(self, attr):
        if (attr in self.dict):
            return self.dict[attr]
        return None
    def get(self, attr):
        return self.dict.get(attr, None)
    def __str__(self):
        return str(self.dict)

def format_yaml(path):
    with open (path, "r") as config:
        config_str = config.read()
        return yaml.safe_load(config_str)

def get_fileStorage_from_path(path):
    fp = open(path, 'rb')
    file = FileStorage(fp)
    return file

def main():
    parser = argparse.ArgumentParser(description="Integration test for server.py and 3plex")
    parser.add_argument('--token', help='Token')
    parser.add_argument('--ssRNA_fasta_path', help='Description of argument 1')
    parser.add_argument('--species', help='Field species. Can be none, hsapiens or mmusculus')
    parser.add_argument('--param_config', help='')
    
    args = parser.parse_args()

    #Generate fake flask request
    request = {
        "files": dict(),
        "args": dict(),
        "form": format_yaml(args.param_config)
    }
    #Populate fake request from parser.args
    for key in request["form"].keys():
        request["form"][key] = str(request["form"][key])
    if (args.ssRNA_fasta_path and len(args.ssRNA_fasta_path)>0):
        request["files"]["ssRNA_fasta"] = get_fileStorage_from_path(args.ssRNA_fasta_path)
    if (args.species and len(args.species)>0):
        request["args"]["species"] = args.species

    #Set test background and putative gene list
    request["form"]["genes_all"] = ",".join(["TSPAN6","CFH","FUCA2","ENPP4","SEMA3F"])
    request["form"]["genes_interest"] = ",".join(["TSPAN6","CFH","FUCA2"])

    #Rebuild into dotDict
    request["args"] = DotDict.from_dict(request["args"])
    request =  DotDict.from_dict(request)

    #Remove test dir if exists
    if (os.path.isdir(os.path.join(WORKING_DIR_PATH, args.token))):
        shutil.rmtree(os.path.join(WORKING_DIR_PATH, args.token))

    #Run test
    result = run_test_promoter_stability(args.token, request)
    
    if (result):
        pass#shutil.rmtree(os.path.join(WORKING_DIR_PATH, args.token))
    else:
        stderr_path = os.path.join(WORKING_DIR_PATH, args.token, "STDERR")
        with open(stderr_path, "r") as log:
            print(f"\n\n    ---------   Failed test {args.token}    ---------\n\nLogs:")
            print(log.read())
            print("\n\n")
        
    assert result


if __name__=="__main__":
    main()