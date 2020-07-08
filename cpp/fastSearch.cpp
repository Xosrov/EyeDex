// Modified for use in web server
//basics
#include <string>
#include <iostream>
#include <vector>
#include <fstream>
#include <iterator>
#include <math.h>
#include <boost/variant.hpp>
#include <boost/algorithm/string.hpp>
#include <zmq.hpp>
//third-party shiz
#include "thirdParty.h"
#include "rapidfuzz-cpp/src/fuzz.hpp"
#include "rapidfuzz-cpp/src/utils.hpp"
using namespace std;
//time
#include <chrono>
/// threading
#include <future>
#include <mutex>
//comm port
const string PORT = "612300";
// NOTE: DELIMITER FOR COMPRESSING TO RAM, should be removed by formatter
// if causes issues, make sure it's stripped from all strings in db, currently only
// stipped from "name", via fuzz's default_process
// stripped from "url" via HTML quoting
// NOT STRIPPED FROM DATE AND SIZE (should not contain these characters) --fix this
#define DELIMITER "|"
// PART OF URL STRIPPED FROM INPUT DB, CHECK formatter 
#define BASEURL "https://the-eye.eu/public/"
//less writing for future
using rapidfuzz::utils::default_process;
using rapidfuzz::fuzz::quick_lev_ratio;
typedef enum {basic, fuzzy, exactS, exactL} search_type;
class VarCompressor {
    public:
        static string getCompressed (vector<string>& dataToCompress, string delimiter = DELIMITER) 
        {
            string concatedString = "";
            for(auto const& value: dataToCompress)
            {
                concatedString += value + delimiter;
            }
            string result = zlibencode(concatedString, 9);
            return result;
        }
        static void getDecompressed (string& compressedData, vector<string>& desitnation, string delimiter = DELIMITER)
        {
            string concatedString = zlibdecode(compressedData);
            boost::split(desitnation, concatedString, boost::is_any_of(delimiter));
        }
};

class Searcher
{
private:
    vector<vector<string>> minimal_data;
    unsigned threadCount;
    unsigned size;
public:
    Searcher(string);
    unsigned search_by_name(vector<vector<string>>& results, string query, float min_score, unsigned splice_count = 20, search_type searchType = fuzzy, bool formated = false);
    void slice_search_fuzzy(string processed_query, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score);
    void slice_search_basic(vector<string> processed_query_splited, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score); //checks that each part of query is in the results somewhere
    void slice_search_exact_loose(vector<string> processed_query_splited, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score); //makes sure each part of query is EXACTLY in results
    void slice_search_exact_strict(string processed_query, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score); //makes sure all of query is EXACTLY in results
    string convert_to_json(vector<vector<string>>&); // only body contents are in string
};

int main()
{
    zmq::context_t ctx;
    zmq::socket_t server(ctx, zmq::socket_type::rep);
    server.bind("tcp://0.0.0.0:" + PORT);
    zmq::message_t input;
    Searcher searcher("dbformatted.json");
    cout << "Database Loaded\n===============\n";
    /*
    Message format:
    TTMMQQQQ..
    * first two characters specify Type:
        fu: fuzzy
        ba: basic
        el: exact loose
        es: exact strict
    * next two characters specify minimum score(int between 10 and 99)
    * all subsequent characters are the passed query
    */
    while(true)
    {
        server.recv(&input);
        string message = string(static_cast<char*>(input.data()), input.size());
        string type = message.substr(0,2);
        float minScore = stof(message.substr(2,2));
        string query = message.substr(4);
        cout << "Got query '" << query << "' With search type: " << type << endl;
        search_type typeToPass;
        if (type == "fu")
            typeToPass = fuzzy;
        else if (type == "ba")
            typeToPass = basic;
        else if (type == "el")
            typeToPass = exactL;
        else if (type == "es")
            typeToPass = exactS;
        vector<vector<string>> results;
        searcher.search_by_name(results, query, minScore, 44, typeToPass, true);
        cout << "Got "<< results.size() << " results!\n===============" << endl;
        string answer;
        if (results.size() == 0)
            answer = "[]";
        else
            answer = searcher.convert_to_json(results);
        unsigned leng = answer.length();
        zmq::message_t response(leng);
        memcpy (response.data(), answer.c_str(), leng);
        server.send(response);
    }
    return 0;
}
string Searcher::convert_to_json(vector<vector<string>>& allResults)
{
    string finalstr = "["; //json formatted string with results
    for (auto it = allResults.rbegin() ; it != allResults.rend() ; it++)
    {
        //                   score               name                    details
        finalstr += "[" + it->at(0) + ",\"" + it->at(1) + "\",\"" + base64_encode(it->at(2)) + "\"],";
        allResults.pop_back(); //NOTE: does this improve performance considerably anyway?
    }
    finalstr.pop_back(); //remove excess comma
    finalstr += "]"; //close list
    return finalstr;
    /* OLD METHOD, used to return fully formatted html, changed to weakly sorted json for less load on server(more on client)
    string finalStr = "";
    finalStr += "<h2 class=\"red\">" + to_string(allResults.size()) +  " results for " + query + "</h1>\n";
    unsigned counter = 0;
    bool usingdirs = true; //find when dirs are ended in case directories are first
    for (const auto &data : allResults)
    {
        string url = BASEURL + zlibdecode(data[2]);
        if (counter == each_page)
        {
            finalStr += "<div class=\"sep\">\n";
            counter = 0;
        }
        if (data.size() == 4)
        {
            finalStr += "<h1>At score " + data[0] + " is \"" + data[1] + "\" Directory with below info:</h1>";
            finalStr += "<section class=\"data\"><p>Date: " + data[3] + "</p>";
        }
        else 
        {
            if (directoriesFirst and usingdirs)
            {
                finalStr += "<h2 class=\"red\">Files</h1>\n<hr />\n";
                usingdirs = false;
            }
            string ftype;
            if (url.rfind('/') > url.rfind('.'))
                ftype = "???";
            else
                ftype = url.substr(url.rfind('.'));
            finalStr += "<h1>At score " + data[0] + " is \"" + data[1] + "\" File with below info:</h1>";
            finalStr += "<section class=\"data\"><p>Date: " + data[3] + "</p><p>Type: " + ftype + "</p><p>Size: " + data[4] + "</p>";
        }
        finalStr += "<a target=\"_blank\" href=\"" + url + "\">" + url + "</a></section>\n";
        counter ++;
    }

    finalStr += "</div>";
    return finalStr;
    */

}
/*
//NOTE:uses start, doesn't use end
*/
void Searcher::slice_search_exact_strict(string processed_query, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score)
{
    auto endit = next(this -> minimal_data.begin(), end);
    string delimiters = " _-.,'\"!?$`=+;:|<>/\\";
    for(auto it = next(this -> minimal_data.begin(), start); it != endit; it++)
    {
        string stringToCheck = it -> at(0);
        auto index = stringToCheck.find(processed_query);
        if (index != string::npos && 
            ( stringToCheck.length() == index + processed_query.length() || delimiters.find(stringToCheck[index + processed_query.length()]) != string::npos ) && //proceeded by end of string or delimiter
            ( index == 0                                                 || delimiters.find(stringToCheck[index -1])                         != string::npos )    //proceeds end of string or delimiter
        )
        {
            vector<string> data;
            data.push_back("100");
            //append the rest of the data
            for(const auto &subdata : *it)
                data.push_back(subdata);
            threadMutex.lock();
            allResults.push_back(data);
            threadMutex.unlock();
        }
    }
}
void Searcher::slice_search_exact_loose(vector<string> processed_query_splited, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score)
{
    float percentToAdd = 100/processed_query_splited.size();
    auto endit = next(this -> minimal_data.begin(), end);
    string delimiters = " _-.,'\"!?$`=+;:|<>/\\";
    for(auto it = next(this -> minimal_data.begin(), start); it != endit; it++)
    {
        string stringToCheck = it -> at(0);
        float score = 0;
        for (const string &namePart : processed_query_splited)
        {
            auto index = stringToCheck.find(namePart); 
            if (index != string::npos && 
                ( stringToCheck.length() == index + namePart.length() || delimiters.find(stringToCheck[index + namePart.length()]) != string::npos ) && //proceeded by end of string or delimiter
                ( index == 0                                          || delimiters.find(stringToCheck[index -1])                  != string::npos )    //proceeds end of string or delimiter
            )
                score += percentToAdd;
        }
        if (score >= min_score)
        {
            vector<string> data;
            data.push_back(to_string(score));
            //append the rest of the data
            for(const auto &subdata : *it)
                data.push_back(subdata);
            threadMutex.lock();
            allResults.push_back(data);
            threadMutex.unlock();
        }
    }
}
void Searcher::slice_search_basic(vector<string> processed_query_splited, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score)
{
    float percentToAdd = 100/processed_query_splited.size();
    auto endit = next(this -> minimal_data.begin(), end);
    for(auto it = next(this -> minimal_data.begin(), start); it != endit; it++)
    {
        string stringToCheck = it -> at(0);
        float score = 0;
        for (const string &namePart : processed_query_splited)
            if (stringToCheck.find(namePart) != string::npos)
                score += percentToAdd;
        if (score >= min_score)
        {
            vector<string> data;
            data.push_back(to_string(score));
            //append the rest of the data
            for(const auto &subdata : *it)
                data.push_back(subdata);
            threadMutex.lock();
            allResults.push_back(data);
            threadMutex.unlock();
        }
    }
}
void Searcher::slice_search_fuzzy(string processed_query, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score)
{
    auto endit = next(this -> minimal_data.begin(), end);
    for(auto it = next(this -> minimal_data.begin(), start); it != endit; it++)
    {
        string stringToCheck = it -> at(0);
        //empty strings cause problems..
        if (!quick_lev_ratio(processed_query, stringToCheck, min_score)) 
            continue;
        auto score = rapidfuzz::fuzz::ratio(processed_query, stringToCheck, min_score);
        if (score) 
        {
            vector<string> data;
            data.push_back(to_string(score));
            //append the rest of the data
            for(const auto &subdata : *it)
                data.push_back(subdata);
            threadMutex.lock();
            allResults.push_back(data);
            threadMutex.unlock();
        }
    }
}
unsigned Searcher::search_by_name(vector<vector<string>>& results, string query, float min_score, unsigned splice_count, search_type searchType, bool formated)
{
    // exactMatch only works when fuzzy is false. it ensures query matches exact word in result
    //process query
    // max result count 0 for none
    if (!formated)
    {
        //remove double spaces if they exist
        size_t doubleSpace = query.find("  ");
        while (doubleSpace != string::npos)
        {
            query.erase(doubleSpace, 1);
            doubleSpace = query.find("  ");
        }
        query = default_process(query);
    }
    // for types that need split input, one for all solution
    vector<string> splitted;
    if (searchType == basic or searchType == exactL)
    {
        boost::split(splitted, query, boost::is_any_of(" "));
        for (const auto& i:splitted) 
            cout << i << endl;
    }
    
    mutex threadMu;
    vector<future<void>> processes;
    unsigned splitSize = static_cast<unsigned>(this -> size/splice_count)+1;
    unsigned start = 0;
    //TODO: make sure iterators aren't missing the borders
    auto time0 = std::chrono::high_resolution_clock::now();
    for (unsigned i = splitSize ; i < this-> size + 1 ; i+=splitSize)
    {
        // cout << "starting thread from " << start << " to " << i << endl;
        if (searchType == fuzzy)
            processes.push_back(async(&Searcher::slice_search_fuzzy, this, query, start, i, ref(results), ref(threadMu), ref(min_score)));
        else if (searchType == exactS)
            processes.push_back(async(&Searcher::slice_search_exact_strict, this, query, start, i, ref(results), ref(threadMu), ref(min_score)));
        else if (searchType == basic)
            processes.push_back(async(&Searcher::slice_search_basic, this, splitted, start, i, ref(results), ref(threadMu), ref(min_score)));
        else if (searchType == exactL)
            processes.push_back(async(&Searcher::slice_search_exact_loose, this, splitted, start, i, ref(results), ref(threadMu), ref(min_score)));
        start = i;
    }
    // cout << "starting thread from " << start << " to " << this ->minimal_data.size() << endl;
    if (searchType == fuzzy)
        processes.push_back(async(&Searcher::slice_search_fuzzy, this, query, start, this -> minimal_data.size(),ref(results), ref(threadMu), ref(min_score)));
    else if (searchType == exactS)
        processes.push_back(async(&Searcher::slice_search_exact_strict, this, query, start, this -> minimal_data.size(), ref(results), ref(threadMu), ref(min_score)));
    else if (searchType == basic)
        processes.push_back(async(&Searcher::slice_search_basic, this, splitted, start, this -> minimal_data.size(), ref(results), ref(threadMu), ref(min_score)));
    else if (searchType == exactL)
        processes.push_back(async(&Searcher::slice_search_exact_loose, this, splitted, start, this -> minimal_data.size(), ref(results), ref(threadMu), ref(min_score)));
    cout << "Processes started, waiting for output..\n";
    for (int i = 0; i < splice_count; ++i)
        processes[i].get();
    auto time1 = std::chrono::high_resolution_clock::now(); 
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(time1 - time0);
    display_mem_usage();
    cout << "Took " << duration.count() << " milliseconds" << endl;
    return duration.count();
    // remove duplicate results DEPRECATED, remove duplicate from database after load instead
    // sort(results.begin(), results.end());
    // results.erase( unique( results.begin(), results.end() ), results.end() );

}
Searcher::Searcher(string dbPath)
{
    ifstream fileStream(dbPath);
    string line;
    auto start = std::chrono::high_resolution_clock::now();
    while(getline(fileStream, line))
    {
        string debug = line;
        try{
            if (line != "}" and line.substr(line.size()-2, 2) == " {")
            {
                vector<string> compactList;
                vector<string> descriptionList;
                // name - 0
                compactList.push_back(line.substr(1, line.size()-5));
                getline(fileStream, line);
                // files:
                if (line[0] == '\t')
                {
                    // url - 1
                    descriptionList.push_back(line.substr(9, line.size()-11));
                    getline(fileStream, line);
                    // date - 2
                    descriptionList.push_back(line.substr(10, line.size()-18));
                    getline(fileStream, line);
                    // size - 3
                    descriptionList.push_back(line.substr(10, line.size()-11));
                }
                //directories:
                else
                {
                    // url - 1
                    descriptionList.push_back(line.substr(8, line.size()-10));
                    getline(fileStream, line);
                    // date - 2
                    descriptionList.push_back(line.substr(9, line.size()-17));
                }
                compactList.push_back(VarCompressor::getCompressed(descriptionList));
                this -> minimal_data.push_back(compactList);
            }
        } catch(...) {
            cout << "Exception encountered reading \"" << debug << "\" from db, continue anyway\n";
            continue;
        }
    }
    auto stop = std::chrono::high_resolution_clock::now(); 
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(stop - start);
    cout << "Took " << duration.count() << " milliseconds" << endl;
    unsigned old_size = this -> minimal_data.size();
    std::sort(this->minimal_data.begin(), this->minimal_data.end());
    this->minimal_data.erase(std::unique(this->minimal_data.begin(), this->minimal_data.end()), this->minimal_data.end());
    this -> size = this -> minimal_data.size();
    cout << "Usable len of data: " << this -> size << ", Had " << old_size-this->size << " Dupes" << endl;
    display_mem_usage();
    //display data:
    // for (int i = 0; i < this -> minimal_data.size() ; i++)
    // {
    //     cout << "for i = " << i << " data is: \n"; 
    //     list<string>::iterator it;
    //     for (it = this -> minimal_data[i].begin(); it != this -> minimal_data[i].end(); ++it)
    //         cout << "\t" << *it << endl;
        
    // }
}

