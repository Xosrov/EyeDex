# THE EYE SEARCHING TOOL
*Search (almost) everything on The-Eye* 
----

I created this because a friend of mine wanted books on a particular subject, but didn't want to sift through all files on the site  
Requires at least 4GB's of RAM (database is loaded to RAM)
### Before you start
1. Download the databases
    * [Google Drive Link](https://drive.google.com/drive/folders/1kf4lTu3-ZMlUveiCQL_B7qYZm0WAHKKB?usp=sharing)
    * Databases are split in two parts, the Piracy/ directory and everything else
2. Format the databases to feed to the program
    * Move the databases to the "database" folder
    * python3 formatter.py [inputfile] [outputfile]
    * Wait for it to finish
3. Compile the searcher program
    * Navigate to the cpp folder
    * Compile the searcher:
        * g++ fastSearch.cpp thirdParty.{cpp,h} -lz -lpthread -lzmq -o searcher
    * In case of errors, make sure required libs are installed(libzmq3-dev and others as needed)
4. Install required python libraries:   
    * pip3 install pyzmq flask rapidfuzz
---- 

### Usage
1. Rename formatted database file to "dbformatted.json" and move it to cpp/
    * You can edit the fastSearch.cpp file to modify this file name(i was too lazy to implement something for that)
1. Run the searcher file in cpp/ and wait for it to be loaded
1. While waiting for it to load to RAM, run the main.py file to initiate flask
    * You can customize things like minimum matching score from the main.py file
1. Navigate to localhost:5000 in a browser(more info provided there)
1. Done
---- 

### Notes
* This was originally meant to be hosted on a server; however the cost of a server is too high for me so it's open source instead
* This is NOT a mirror of all files in The-Eye, it is just an index of the files hosted there
* I'll try to update the database roughly every month. I will not be releasing the scraping code just yet
* The database is NOT 100% accurate, and stuff like html pages are not scraped correctly
* I used json as it is easy to use, readable and supports the nested format that i want. The format is easy to iterate over line-by-line(inspect the first few hundred bytes to see what i mean)