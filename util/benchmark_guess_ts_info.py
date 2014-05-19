from timestream.parse import guess_manifest_info
from sys import argv, stdout
import json

def main():
    json.dump(_guess_manifest_info(argv[1]), stdout, indent=2)

if __name__ == "__main__":
    main()
