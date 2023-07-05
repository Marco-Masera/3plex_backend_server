import os, sys
import argparse
import shutil
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import run_test
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
        return self.attr

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
    # Add the named arguments
    parser.add_argument('--token', help='Token')
    parser.add_argument('--ssRNA_fasta_path', help='Description of argument 1')
    parser.add_argument('--dsDNA_fasta_or_bed_path', help='Description of argument 2')
    parser.add_argument('--dsdna_target', help='Description of argument 3')
    parser.add_argument('--species', help='Description of argument 4')
    parser.add_argument('--param_config', help='')
    
    args = parser.parse_args()
    #Generate fake flask request
    request = {
        "files": dict(),
        "args": dict(),
        "form": format_yaml(args.param_config)
    }
    for key in request["form"].keys():
        request["form"][key] = str(request["form"][key])
    if (args.ssRNA_fasta_path and len(args.ssRNA_fasta_path)>0):
        request["files"]["ssRNA_fasta"] = get_fileStorage_from_path(args.ssRNA_fasta_path)
    if (args.dsDNA_fasta_or_bed_path and len(args.dsDNA_fasta_or_bed_path)>0):
        request["files"]["dsDNA_fasta"] = get_fileStorage_from_path(args.dsDNA_fasta_or_bed_path)
    else:
        request["files"]["dsDNA_fasta"] = None
    if (args.dsdna_target and len(args.dsdna_target)>0):
        request["args"]["dsdna_target"] = args.dsdna_target
    if (args.species and len(args.species)>0):
        request["args"]["species"] = args.species
    #Rebuild into dotDict
    #request["form"] = DotDict.from_dict(request["form"])
    request["args"] = DotDict.from_dict(request["args"])
    request =  DotDict.from_dict(request)
    result = run_test(args.token, request)
    
    if (result):
        shutil.rmtree(os.path.join(WORKING_DIR_PATH, args.token))

    assert result


if __name__=="__main__":
    main()