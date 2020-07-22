from argparse import ArgumentParser
import os
from database.formatter import formatForSearch
import subprocess
current_path = os.path.dirname(os.path.realpath(__file__))
cpp_dir = os.path.join(current_path, "cpp")
#check for searcher executable
if not os.path.exists(os.path.join(cpp_dir, 'search')):
    print("Compile the searcher first! check the cpp/ directory")
    quit()
def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    return arg
parser = ArgumentParser(description="Format the database, load it to RAM and ready back-end for server")
parser.add_argument("-f", "--file", dest="filename",
                    help="Database file to load, overrides current database file", metavar="DATABASE",
                    type=lambda x: is_valid_file(parser, x))
parser.add_argument('-po', '--process-option', dest='option', type=int, default=1,
                    help="process option (see formatter.py) - leave leave empty ")
args = parser.parse_args()
formattedPath = os.path.join(cpp_dir, "dbformatted.json")
if not args.filename and os.path.exists(os.path.join(cpp_dir, "dbformatted.json")):
    print("Formatted Database already found, using that. use the -f flag to override it")
else:
    if not args.filename:
        print("No formatted database currently exists, use the -f argument to load one")
        quit()
    print("Formatting database..Please be patient")
    formattedPath = os.path.join(cpp_dir, "dbformatted.json")
    try:
        formatForSearch(args.filename, formattedPath, args.option)
    except KeyboardInterrupt:
        print("ok. cleaning up..")
        if os.path.exists(formattedPath):
            os.remove(formattedPath)
        quit()
print("Done, now loading to RAM..")
process = subprocess.Popen([os.path.join(cpp_dir, 'search'), formattedPath], shell=False)
try:
    while("True"):
        pass
except KeyboardInterrupt:
    pass
process.kill()