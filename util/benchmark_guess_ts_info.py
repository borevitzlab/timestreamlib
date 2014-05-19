from timestream.parse import guess_manifest_info
from sys import argv, stdout
import json
import timeit

def main():
    n = 10
    cmd = "from timestream.parse import guess_manifest_info;"
    cmd += "from sys import argv; guess_manifest_info(argv[1])"
    time = timeit.timeit(cmd, number=n) / float(n)
    print("guess_manifest_info took {}s per iteration".format(time))
    json.dump(guess_manifest_info(argv[1]), stdout, indent=2)

if __name__ == "__main__":
    main()
