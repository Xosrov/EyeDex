# import requests
import cloudscraper
from cloudscraper.exceptions import CloudflareException
import os
from tempfile import mkstemp
from shutil import move, copymode
import re
import atexit
import sys
import ast
import requests
from threading import Thread
from typing import List, Tuple
from datetime import datetime
from urllib.parse import unquote, quote
from time import sleep
GETPIRACY = False # set to true to get Piracy/ directory instead
if GETPIRACY:
    DBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "dbPiracy.json")
else:
    DBDIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "dbPublicNoPiracy.json")
BASEURL = "http://the-eye.eu/public/"
BASEURLPIRACY = "http://the-eye.eu/public/Piracy/"
#create a list of temp files that are created. in case program exits, delete them
tempFiles = []
def remove_temp_files():
    for Tfile in tempFiles:
        try:
            os.remove(Tfile)
        except:
            continue
atexit.register(remove_temp_files)
class Indexer():
    def __init__(self, baseURL: str, DBdir: str, skipList = []) -> None:
        self.baseurl= baseURL
        self.dbdir= DBdir
        self.exceptionCount = 0
        #Regexes:
            #Group1 url
            #Group2 date
            #Group3 size(for files only)
        self.fileRe = re.compile(r'^<a href="([^\/]*?)">.*?<\/a>\s*(.*? .*?)\s+(.*)$', re.M)
        self.dirRe = re.compile(r'^<a href="([^\/]*?\/)">.*?>\s*(.*?\s.*?)\s', re.M)
        #invalid json chars that need to be stripped(or escaped, but opted to removing here)
        self.charsToRemove = ['\b','\f','\n','\r','\t','\v','"','\\']
        self.messages = []        
        #current sleep time
        self.sleepTime = 0
        #sleep rate of decrease
        self.sleepDecreaseRate = 0.01
        #sleep step increase
        self.sleepStep = 5
        #create temporary copy of dbdir, used for comparing with new data(alt to loading to RAM)
        self.first_run = False
        self.skip_current = False
        self.scraper = cloudscraper.create_scraper()
        #urls to skip
        self.skipList = skipList
        #create temp copy of database
        self.dbcopy, self.dbcopy_path = mkstemp()
        tempFiles.append(self.dbcopy_path)
        with os.fdopen(self.dbcopy,'w') as copy:
            try:
                with open(self.dbdir, 'r') as main:
                    for line in main:
                        copy.write(line)
            except FileNotFoundError:
                self.first_run = True
        #clear db file first
        with open(self.dbdir, 'w'): pass
        self.__dbFILE = open(self.dbdir, 'a')
        #list of relative domain names that have not succeeded.
        self.__notSuccessfullStack = list()
        #begin
        self.write_to_file("{\n")
        #finalizers must run
        atexit.register(self.finalizers)
    #Index, then save to db
    #functions handling rate limiting
    def recursiveIndexer(self, depth=0, current_url=None):
        """
        recursively scrape url and save to database as non-valid json
        json can be validified with formatter.py
        Ctrl+C to skip
        """
        if not current_url:
            current_url = self.baseurl
        thread = None
        try:
            #note: below code needs testing
            if self.exceptionCount > 10: #too many request exceptions
                print("It seems the webpage is having issues handling requests right not, try again later!")
                fullRelUrl = (current_url).replace(self.baseurl, '')
                for i in range(len(fullRelUrl)):
                    if fullRelUrl[i] == '/':
                        toAdd = fullRelUrl[:i+1]
                        if not toAdd in self.__notSuccessfullStack:
                            self.__notSuccessfullStack.append(toAdd)
                return -1
            #sleep in case rate limited
            if self.sleepTime:
                sleep(self.sleepTime)
                self.sleepTime -= self.sleepDecreaseRate
                if self.sleepTime < 0:
                    self.sleepTime = 0
            #get webpage, ensure success or remember failure
            try:
                page = self.scraper.get(current_url)
                if page.is_redirect or page.status_code != 200:
                    print("Page redirected or rate limited.. setting to incomplete")
                    if page.is_redirect:
                        self.messages.append(f"\"{current_url}\" Was redirected somewhere else .. skipping")
                    else:
                        if page.status_code == 429: #rate limited
                            self.sleepTime += self.sleepStep
                            print("Rate limited, slowing down")
                        self.messages.append(f"\"{current_url}\" Skipped because returned status {page.status_code}")
                    fullRelUrl = (current_url).replace(self.baseurl, '')
                    for i in range(len(fullRelUrl)):
                        if fullRelUrl[i] == '/':
                            toAdd = fullRelUrl[:i+1]
                            if not toAdd in self.__notSuccessfullStack:
                                self.__notSuccessfullStack.append(toAdd)
                    return
                page = page.text
            except CloudflareException:
                print(f"Cloudflare couldn't be bypassed at {current_url}..setting to incomplete")
                self.messages.append(f"\"{current_url}\" Skipped because Cloudflare could not be bypassed")
                fullRelUrl = (current_url).replace(self.baseurl, '')
                for i in range(len(fullRelUrl)):
                    if fullRelUrl[i] == '/':
                        toAdd = fullRelUrl[:i+1]
                        if not toAdd in self.__notSuccessfullStack:
                            self.__notSuccessfullStack.append(toAdd)
                return
            except requests.RequestException as e:
                print(e)
                self.messages.append(f"\"{current_url}\" Skipped because of request error({e})")
                fullRelUrl = (current_url).replace(self.baseurl, '')
                for i in range(len(fullRelUrl)):
                    if fullRelUrl[i] == '/':
                        toAdd = fullRelUrl[:i+1]
                        if not toAdd in self.__notSuccessfullStack:
                            self.__notSuccessfullStack.append(toAdd)
                #error in request, page might be down! wait a while and add to exceptions
                self.exceptionCount += 1
                sleep(10) 
                return
            # check for directories:
            dirs = re.findall(self.dirRe, page)
            #skip specified links:
            for each in self.skipList:
                for one in dirs:
                    if each in unquote(current_url + one[0]):
                        print(f"{unquote(current_url + one[0])} Was in skip list, skipping")
                        self.messages.append(f"\"{current_url + one[0]}\" Was in skip list")
                        dirs.remove(one)
            if not self.first_run:
                # print("Attempting to skip repetitions..")
                thread = Thread(target=self.skip_chunk, args=(dirs, current_url,))
                thread.start()
                thread.join()
                # print("Done, continuing normal flow")
            if dirs:
                for url, date in dirs:
                    #remove unsafe chars from data
                    safeFullURL = unquote(current_url + url).translate({ord(x): '' for x in self.charsToRemove})
                    safeName = unquote(url).translate({ord(x): '' for x in self.charsToRemove}).replace('/', '')
                    safeDate = date.translate({ord(x): '' for x in self.charsToRemove})
                    self.write_to_file(f'"{safeName}": {{\n"url": "{safeFullURL}",\n"date": "{safeDate}",\n"success": false,\n')
                    print(f"navigating to {safeFullURL}")
                    if self.recursiveIndexer(depth=depth+1, current_url=current_url+url) == -1:
                        return
            files = re.findall(self.fileRe, page)
            if files:
                for url, date, size in files:
                    #remove unsafe chars from data
                    safeFullURL = unquote(current_url + url).translate({ord(x): '' for x in self.charsToRemove})
                    safeURL = unquote(url).translate({ord(x): '' for x in self.charsToRemove}).replace('/', '')
                    safeDate = date.translate({ord(x): '' for x in self.charsToRemove})
                    safeSize = size.translate({ord(x): '' for x in self.charsToRemove})
                    name, file_type = os.path.splitext(safeURL)
                    string = f'''"{name}": {{\n\t"url": "{safeFullURL}",\n\t"type": "{file_type}",\n\t"date": "{safeDate}",\n\t"size": "{safeSize}"\n}},\n'''
                    self.write_to_file(string)
            if not files and not dirs:
                print(f"its appears \"{current_url}\" is empty! if its not actually, something's wrong!")
        except KeyboardInterrupt:
            print("Processing..")
            if thread != None:
                while(thread.is_alive()):
                    print("Please wait for chunk skip thread to finish")
                    try:
                        thread.join()
                    except KeyboardInterrupt:
                        continue
                print("Done, continuing normal flow")
            fullRelUrl = (current_url).replace(self.baseurl, '')
            for i in range(len(fullRelUrl)):
                if fullRelUrl[i] == '/':
                    toAdd = fullRelUrl[:i+1]
                    if not toAdd in self.__notSuccessfullStack:
                        self.__notSuccessfullStack.append(toAdd)
            print(f"Skipping \"{current_url}\" and parent directory(depth {depth})")
            self.messages.append(f"\"{current_url}\" was skipped manually")
            return -1
        finally:
            # end chunk of data regardless of what happens
            self.write_to_file('},\n')
    def skip_chunk(self, dirsList: List[Tuple[str,str]], preURL):
        """
            checks if chunk of directory is up to date, then updates it
            also removes previous entries from db to reduce CPU usage over time
        """
        if not dirsList:
            return
        #assumes data in website and database are sorted in the same way
        urls = [unquote(preURL + a) for (a,_) in dirsList]
        fh, abs_path = mkstemp()
        tempFiles.append(abs_path)
        previous_line = ""
        stop = False
        with os.fdopen(fh,'w') as dbcopycopy:
            with open(self.dbcopy_path, 'r') as dbcopy:
                line = dbcopy.readline()
                while line:
                    if not stop and line[8:-3] in urls:
                        foundIndex = urls.index(line[8:-3])
                        print(f"Found \"{urls[foundIndex]}\" in database already")
                        #remove all previous content of file, replace with everything from here:
                        dateline = dbcopy.readline()
                        # date = re.search(self.__dateFromFileRe, dateline).group(1)
                        date = dateline[9:-3]
                        successline = dbcopy.readline()
                        success = (successline[11:-2] == "true")
                        olddate = dirsList[foundIndex][1]
                        if datetime.strptime(olddate, "%d-%b-%Y %H:%M") <= datetime.strptime(date, "%d-%b-%Y %H:%M"):
                            print("\talready up-to-date, ", end='')
                            if success: 
                                # something found! need to decrease dbcopy's file size
                                print("was fully successful too!, so..")
                                print(f"\tSkipping {urls[foundIndex]}")
                                #start writing to file until end of current data json or end of file
                                bracketCounter = 1
                                self.write_to_file(previous_line) #name
                                self.write_to_file(line) #url
                                self.write_to_file(dateline) #date
                                self.write_to_file(successline) #success
                                while bracketCounter > 0 and line:
                                    line = dbcopy.readline()
                                    try:
                                        if line[-2] == '{':
                                            bracketCounter += 1
                                        elif line[0] == '}':
                                            bracketCounter -= 1 
                                    except IndexError: # line length less than two
                                        pass
                                    self.write_to_file(line)
                                previous_line = line
                                line = dbcopy.readline()
                                #remove data point from list
                                dirsList.pop(foundIndex)
                                urls.pop(foundIndex)
                                continue
                            else:
                                print("unsuccessful though, so nvm")
                        else:
                            print(f"\tDate in previous data is {date}, while it's {unquote(olddate)} now, so nvm")
                        if not dirsList:
                            stop = True
                    dbcopycopy.write(line)
                    previous_line = line
                    line = dbcopy.readline()
        # print("Replacing dbcopy too..")
        #Copy the file permissions from the old file to the new file
        copymode(self.dbcopy_path, abs_path)
        #Remove original file
        os.remove(self.dbcopy_path)
        #Move new file
        move(abs_path, self.dbcopy_path)
        tempFiles.remove(abs_path)
    def write_to_file(self, string):
        self.__dbFILE.write(string)
    def finalizers(self):
        thread = None
        #close file:
        self.__dbFILE.close()
        print("Exiting gracefully...")
        try:
            thread = Thread(target=self.fix_success_states_and_make_json_valid)
            thread.start()
            thread.join()
            # self.sleepProcess.get()
        except KeyboardInterrupt:
            if thread != None:
                while(thread.is_alive()):
                    print("Still waiting for finishing touches")
                    try:
                        # self.sleepProcess.get()
                        thread.join()
                    except KeyboardInterrupt:
                        continue
            else:
                print("Finalizer not run correctly... dont interrupt so fast")
        print("==========DEBUG==========")
        for message in self.messages:
            print(message)
        print("==========DONE==========")
    def fix_success_states_and_make_json_valid(self):
        for i in range(len(self.__notSuccessfullStack)):
            self.__notSuccessfullStack[i] = BASEURL + unquote(self.__notSuccessfullStack[i])
        #save unsuccesful stack to file:
        if self.__notSuccessfullStack:
            print("creating backup of unuccessfull chunks: ", end='')
            suffixint = 1
            while True:
                if os.path.exists("stack" + str(suffixint)):
                    suffixint += 1
                    continue
                break
            with open("stack" + str(suffixint), 'w') as f:
                f.write(str(self.__notSuccessfullStack))
            print(f"created stack backup stack{str(suffixint)}")
        print("Correcting success status and validifying json(please be patient)")
        fh, abs_path = mkstemp()
        tempFiles.append(abs_path)
        with os.fdopen(fh,'w') as new_file:
            with open(self.dbdir, 'r') as old_file:
                # use readline() to read the first line 
                line = old_file.readline()
                url = ""
                while line:
                    prev_line = line
                    line = old_file.readline()
                    #save url for later use(only dir url, files are too "small" to be skipped)
                    # last line check (only line that's empty)
                    if not line:
                        new_file.write("}\n")
                        continue
                    if prev_line.startswith('"url": '):
                        url = prev_line[8:-3]
                    #check if its really successful or just skipped
                    if prev_line.startswith('"success": false'):
                        if not url in self.__notSuccessfullStack:
                            prev_line = prev_line.replace("false", "true")
                        else:
                            self.__notSuccessfullStack.remove(url)
                    #remove excess commas
                    if line[0] == '}':
                        prev_line = prev_line.replace(',\n', '\n')
                    #add commas if they're needed  -> needs investigating.. why does this happen?
                    elif line[0] == '"' and prev_line[-2] == '}':
                        prev_line = prev_line.replace('\n', ',\n')
                    new_file.write(prev_line)
        #Copy the file permissions from the old file to the new file
        copymode(self.dbdir, abs_path)
        #Remove original file
        os.remove(self.dbdir)
        #Move new file
        move(abs_path, self.dbdir)
        tempFiles.remove(abs_path)

def update_db(stackFile, inputdb, exceptionList=[]):
    """
    update success status of db using stack file
    exceptionList is list of url trees to ignore
    """
    with open(stackFile, 'r') as f:
        stackContents = f.read()
    for i in exceptionList:
        stackContents = re.sub(r"\s?'" + quote(i) + r".*?',?\s?",'',stackContents)
    stackContents = ast.literal_eval(stackContents)
    #todo: repetitions shouldn't exist anyway.. why did i add this(consider removal):
    stackContents = list(set(stackContents)) #remove repetitions
    #remove when stack creation also doesn't have quote:
    for i in range(len(stackContents)):
        stackContents[i] = BASEURL + unquote(stackContents[i])
    #remove exceptions
    print("formatting with\n" + str(stackContents))
    fh, abs_path = mkstemp()
    tempFiles.append(abs_path)
    with os.fdopen(fh,'w') as new_file:
        with open(inputdb, 'r') as old_file:
            # use readline() to read the first line 
            line = old_file.readline()
            url = ""
            while line:
                #save url for later use
                if line.startswith('"url": '):
                    url = line[8:-3]
                    new_file.write(line)
                    line = old_file.readline() # date
                    new_file.write(line)
                    line = old_file.readline() # success
                    #after brackets or in empty directories when indexing:
                    if line.startswith('"success": true'):
                        if url in stackContents:
                                print(f"Setting false for \"{url}\"")
                                new_file.write(line.replace("true", "false"))
                                line = old_file.readline()
                                stackContents.remove(url)
                new_file.write(line)
                line = old_file.readline()
    #Copy the file permissions from the old file to the new file
    copymode(inputdb, abs_path)
    #Remove original file
    os.remove(inputdb)
    #Move new file
    move(abs_path, inputdb)
    tempFiles.remove(abs_path)
#todo: these two functions might need revisions due to changes in other parts
# def make_empty_dirs_unsuccessful(dbfile, outputfile):
#     #first get empty dirs:
#     emptyDirs = []
#     with open(dbfile, 'r') as f:
#         line = f.readline()
#         while (line):
#             if line.startswith('"url": '):
#                 url = line[8:-3].replace(BASEURL, '')
#                 #date
#                 f.readline()
#                 #success
#                 f.readline()
#                 #other data
#                 line = f.readline()
#                 #check if dir is empty:
#                 if line.startswith('}'):
#                     for i in range(len(url)):
#                         if url[i] == '/':
#                             toAdd = url[:i+1]
#                             if not toAdd in emptyDirs:
#                                 emptyDirs.append(toAdd)
#             line = f.readline()
#         with open(outputfile, 'w') as f:
#             f.write(str(emptyDirs))
# def remove_from_db(dbfile, urlToRemove):
#     """
#     remove entire url tree from db
#     """
#     found = False
#     fh, abs_path = mkstemp()
#     tempFiles.append(abs_path)
#     with os.fdopen(fh,'w') as new_file:
#         with open(dbfile, 'r') as old_file:
#             # use readline() to read the first line 
#             line = old_file.readline()
#             while line:
#                 #save url for later use
#                 if not found and line[-2:] == "{\n": # name
#                     next_line = old_file.readline() # url
#                     url = next_line[8:-3]
#                     if urlToRemove in url:
#                         print(f"Removing {url}")
#                         found = True
#                         bracketCounter = 1
#                         while bracketCounter > 0 and line:
#                             line = old_file.readline()
#                             if line[-2] == '{':
#                                 bracketCounter += 1
#                             elif line[0] == '}':
#                                 bracketCounter -= 1 
#                         print(f"removed until:\n{line}")
#                         line = old_file.readline()
#                         continue
#                     else:
#                         new_file.write(line)
#                         new_file.write(next_line)
#                         line = old_file.readline()
#                         continue
#                 new_file.write(line)
#                 line = old_file.readline()
#     #Copy the file permissions from the old file to the new file
#     copymode(dbfile, abs_path)
#     #Remove original file
#     os.remove(dbfile)
#     #Move new file
#     move(abs_path, dbfile)
#     tempFiles.remove(abs_path)

if __name__ == "__main__":
    #incorporate stack file to db
    if len(sys.argv) > 3 and sys.argv[1] == '-c':
        update_db(sys.argv[2], sys.argv[3], [])
        quit()
    # #remove empty dirs
    # if len(sys.argv) > 3 and sys.argv[1] == '-rme':
    #     make_empty_dirs_unsuccessful(sys.argv[2], sys.argv[3])
    #     quit()
    # #remove single directory
    # if len(sys.argv) > 3 and sys.argv[1] == '-rm':
    #     remove_from_db(sys.argv[2], sys.argv[3])
    #     quit()

    if GETPIRACY:
        print("Commencing index on Piracy/ dir")
        indexer = Indexer(BASEURLPIRACY, DBDIR)
    else:
        print("Commencing index on Public/ dir (excluding Piracy/)")
        indexer = Indexer(BASEURL, DBDIR, skipList=["http://the-eye.eu/public/Piracy/"])
    indexer.recursiveIndexer()