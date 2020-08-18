# THE EYE SEARCHING TOOL
*Search (almost) everything on The-Eye* 
----

*LINUX ONLY*  
Requires at least 2GB's of RAM (database is loaded to RAM)
### Before you start
1. Unzip the database(s)
    * Navigate to the database/ directory
    * Unzip .zip database files where they are
2. Install required python libraries:   
    * Python3 dependencies: pip3 install -r requirements.txt
    * C++     dependencies: apt-get install libboost-dev libz-dev libzmq3-dev
3. Compile the searcher program
    * Navigate to the cpp/ directory
    * Compile the searcher with "make"
---- 

### Usage
1. Load the database:
    * python3 loader.py -f databaseJsonFile
2. Once(or while) the database loads, run the server:
    * python3 server.py
    * Use the -h tag for help with additional arguments 
3. Open the local server on a browser(default at localhost:5000)
    * More info on the local server
---- 

### Updating the database
1. Navigate to the database/ folder
2. Run indexer.py 
    * Indexer will start saving to json, directories can be skipped with KeyboardInterrupt
    * If a database already exists in the database/ folder, it will update incomplete or out-of-date directories
    * Some pages are blocked or can not be indexed, so you might have to run the indexer multiple times to index everything
    * Defaulted to only work on Public/ and excluding Piracy/(as it's too big)
    * Can be modified to index Priacy/ separately. Just set the GETPIRACY flag in the indexer.py file to True. This saves into a different file and might run into errors because of Cloudflare, so multiple runs are necessary for a full index. The file size is also larger meaning at least 4GB's of RAM is needed.
    * Indexer might not work for directories like alviro/ (slightly different structure | Cloudflare heavily enforced)
---- 

### Notes
* Check for updates when you can, this project is still in progress i don't deny there might be bugs(do let me know if you find them).
* This is NOT a mirror of all files in The-Eye, it is just an index of the files hosted there.
* You can update the database yourself, but I'll also update them every now and again.
* Elements of the database like HTML pages are not scraped correctly, they don't affect much but I'll have to remove or notify about them in a future update.
* I used json as it is easy to use, readable and supports the nested format that i want. The format is easy to iterate over line-by-line because of the predictable way it's formatted. Inspect the first few hundred bytes to see what i mean.
---- 

### Contribute
*Hosting the server*  
* The server.py file can be modified to be hosted for public use. You can contribute by hosting the server for other people to use. Send me an email/message if you're interested.
*Bugs*  
* For any bug reports or suggestions, open an issue. In case of reporting bugs, provide an example of how you reproduced the undesirable outcome.