# THE EYE SEARCHING TOOL
*Search (almost) everything on The-Eye* 
----

*LINUX ONLY*  
Requires at least 4GB's of RAM (database is loaded to RAM)
### Before you start
1. Unzip the database(s)
    * Navigate to the database/ directory
    * Unzip .zip files where they are
2. Compile the searcher program
    * Navigate to the cpp folder
    * Compile the searcher with "make"
    * In case of errors, make sure required libs are installed(libzmq3-dev and others as needed)
3. Install required python libraries:   
    * pip3 install -r requirements.txt
---- 

### Usage
1. Format/load the database:
    * python3 loader.py
    * Use the -h tag for help with additional arguments 
2. Once the database loads, run the server:
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
    * Indexer might not work for directories like alviro/ (haven't tested yet)
---- 

### Notes
* Check for updates when you can, this project is still in progress i don't deny there might be bugs(do let me know if you find them).
* This is NOT a mirror of all files in The-Eye, it is just an index of the files hosted there.
* You can update the database yourself, but I'll also update them every now and again.
* Elements of the database like HTML pages are not scraped correctly, they don't affect much but I'll have to remove or notify about them in a future update.
* I used json as it is easy to use, readable and supports the nested format that i want. The format is easy to iterate over line-by-line because of the predictable way it's formatted. Inspect the first few hundred bytes to see what i mean.