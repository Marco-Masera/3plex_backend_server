import os, sys
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import run_test
from werkzeug.datastructures import FileStorage

def get_fileStorage_from_path(path):
    file = None
    with open('document-test/test.pdf', 'rb') as fp:
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
    args = parser.parse_args()
    #Generate fake flask request
    request = {
        "files": dict(),
        "args": dict()
    }
    if (args.ssRNA_fasta_path and len(args.ssRNA_fasta_path)>0):
        request.files["ssRNA_fasta"] = get_fileStorage_from_path(args.ssRNA_fasta_path)
    if (args.dsDNA_fasta_or_bed_path and len(args.dsDNA_fasta_or_bed_path)>0):
        request.files["dsDNA_fasta"] = get_fileStorage_from_path(args.dsDNA_fasta_or_bed_path)
    if (args.dsdna_target and len(args.dsdna_target)>0):
        request.args["dsdna_target"] = args.dsdna_target
    if (args.species and len(args.species)>0):
        request.args["species"] = args.species

    success = run_test(args.token, request)
    


if __name__=="__main__":
    main()