from argparse import ArgumentParser
import os
import subprocess
current_path = os.path.dirname(os.path.realpath(__file__))
cpp_dir = os.path.join(current_path, "cpp")
#check for searcher executable
if not os.path.exists(os.path.join(cpp_dir, 'search')):
    print("Compile the searcher first! try running make the in cpp/ directory")
    quit()
def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    return arg
parser = ArgumentParser(description="Format the database, load it to RAM and ready back-end for server")
parser.add_argument("-f", "--file", dest="filename",
                    help="Database file to load, overrides current database file", metavar="DATABASE",
                    type=lambda x: is_valid_file(parser, x))
args = parser.parse_args()
if not args.filename:
    print("No formatted database currently exists, use the -f argument to load one")
    quit()
print("file found, Loading to RAM..(KeyboardInterrupt to quit)")
process = subprocess.Popen([os.path.join(cpp_dir, 'search'), os.path.join(current_path, args.filename)], shell=False)
try:
    while("True"):
        pass
except KeyboardInterrupt:
    pass
process.kill()