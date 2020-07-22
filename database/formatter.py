#format db file for search
import sys, os
from urllib.parse import quote
from rapidfuzz import utils
from tempfile import mkstemp
from shutil import move, copymode
import re
BASEURL = "http://the-eye.eu/public/"
def removeBrokenData(db_file, output_file):
    #TODO
    """
    Removes data extracted from .html pages
    """
    pass
def formatForSearch(db_file, output_file, process_option = 1):
    """
    Does the following: 
        * Remove information that's not necessary
            - file type(can be extracted from url)
            - success state
        * process_option defines how much the queries are processed
            0: do not process
            1: convert queries to lower-case
                - combined with lowercase conversion in searching code for best matching
            2: run default_process on queries
                - removes non alphanumerical chars, double spaces etc(see default_process)
    """
    noNameCounter = 1
    fh, abs_path = mkstemp() #incase user wants to override current file, save to temp file first then move
    with os.fdopen(fh,'w') as new_file:
        with open(db_file) as old_file:
            # use readline() to read the first line 
            line = old_file.readline()
            while line:
                #skip status
                if line.startswith('"success":'):
                    line = old_file.readline()
                    continue
                try:
                    if line[-3:-1] == ' {':
                        #name
                        string = line[1:-5]
                        oldline = line
                        newstring = string
                        if process_option == 1:
                            newstring = newstring.lower()
                        elif process_option == 2:
                            newstring = utils.default_process(newstring)
                        #url line:
                        line = old_file.readline()
                        #if name is just special chars, need to replace it with something
                        if len(newstring) == 0:
                            #replace with final part of URL
                            newstring = line.rstrip()[8:-3]
                            newstring = newstring[newstring.rfind('/')+1:]
                            #final part of URL is also, just special chars
                            if process_option == 1:
                                newstring = newstring.lower()
                            if process_option == 2:
                                newstring = utils.default_process(newstring)
                            if len(newstring) == 0:
                                newstring = "NONE" + str(noNameCounter)
                                noNameCounter += 1
                        new_file.write(oldline.replace(string, newstring))
                        if BASEURL in line:
                            #file
                            if line.startswith('\t'):
                                # url - 1
                                url = line[9:-3]
                                #skip file type, get from url in search
                                old_file.readline()
                            #dir
                            else:
                                url = line[8:-3]
                                starting = line[:8]
                            #quote the URL's, as "unsafe" characters are going to be used as delimiters later
                            new_file.write(line.replace(url, quote(url.replace(BASEURL, ''))))
                            line = old_file.readline()
                            continue
                except IndexError:
                    continue
                new_file.write(line)
                line = old_file.readline()
    #has same permission as original
    copymode(db_file, abs_path)
    move(abs_path, output_file)
# not needed, json should already be valid!
# def makeJsonValid(db_file, output_file):
#     """
#     Make json valid:
#         * Removing excess commas
#     """
#     prev_line = ""
#     fh, abs_path = mkstemp() #incase user wants to override current file, save to temp file first then move
#     with os.fdopen(fh,'w') as new_file:
#         with open(db_file) as old_file:
#             # use readline() to read the first line 
#             line = old_file.readline()
#             while line:
#                 prev_line = line
#                 line = old_file.readline()
#                 # last line check (only line that's empty)
#                 if not line:
#                     new_file.write("}\n")
#                     continue
#                 #remove excess commas
#                 # if line[0] == '}':
#                 #     prev_line = prev_line.replace(',\n', '\n')
#                 #add commas
#                 if line[0] == '"':
#                     if prev_line[-2] == '}':
#                         # print("here")
#                         prev_line = prev_line.replace('\n', ',\n')
#                 new_file.write(prev_line)
#     #has same permission as original
#     copymode(db_file, abs_path)
#     move(abs_path, output_file)
if __name__ == "__main__":
    if len(sys.argv) > 2:
        inputDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), sys.argv[1])
        outputDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), sys.argv[2])
        formatForSearch(inputDIR, outputDIR)
    else:
        print("Format for search:")
        print("\tpython3 formatter.py inputFile outputFile")
