/*
2020 Xosrov
Who needs header files x-x
*/
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
#include <chrono>
#include <future>
#include <mutex>
//non standard
#include "thirdParty.h"
#include "zmq.hpp"
#include "rapidfuzz-cpp/src/fuzz.hpp"
#include "rapidfuzz-cpp/src/utils.hpp"
using namespace std;
//back-end communication port
const string PORT = "612300";
//delimiters used between words, for example "Word1 Word2" is treated like "Word1-Word2"
const string seperators = " _-.,'\"!?$`=+;:|<>/\\";
//TODO: delimiter should be removed from everything, currently only removed from name(Assumed other data fields don't contain it). see main class' constructor and how data is processed before being loaded
#define DELIMITER "|"
// Base url stripped in formatter
#define BASEURL "http://the-eye.eu/public/"
//less writing for future
using rapidfuzz::utils::default_process;
using rapidfuzz::fuzz::quick_lev_ratio;
//supported search types
typedef enum {basic, fuzzy, exactS, exactL} search_type;
class Searcher
{
private:
    vector<vector<string>> minimal_data;
    unsigned threadCount;
    unsigned size;
public:
    Searcher(string);
    unsigned search_by_name(vector<vector<string>>& results, string query, float min_score, unsigned splice_count = 20, search_type searchType = fuzzy);
    void slice_search_fuzzy(string processed_query, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score);
    void slice_search_basic(vector<string> processed_query_splited, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score); //checks that each part of query is in the results somewhere
    void slice_search_exact_loose(vector<string> processed_query_splited, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score); //makes sure each part of query is EXACTLY in results
    void slice_search_exact_strict(string processed_query, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score); //makes sure all of query is EXACTLY in results
    string convert_to_json(vector<vector<string>>&); // only body contents are in string
};
//TODO: implement something in case database is not formatted(include special chars in search)
int main(int argc, char** argv)
{
    if (argc != 2)
    {
        cout << "Takes formatted database as argument" << endl;
        return 0;
    }
    zmq::context_t ctx;
    zmq::socket_t server(ctx, zmq::socket_type::rep);
    server.bind("tcp://0.0.0.0:" + PORT);
    zmq::message_t input;
    Searcher searcher(argv[1]);
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
        //clear results
        vector<vector<string>> results; 
        server.recv(&input);
        string message = string(static_cast<char*>(input.data()), input.size());
        string type = message.substr(0,2);
        float minScore = stof(message.substr(2,2));
        string query = message.substr(4);
        //convert to lower-case 
        boost::algorithm::to_lower(query);
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
        searcher.search_by_name(results, query, minScore, 44, typeToPass);
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
/*
    convert results to json string.
    List of lists, with each element having the format below:
        [score, name, base64-encoded of zlib-encoded details]
*/
string Searcher::convert_to_json(vector<vector<string>>& allResults)
{
    string finalstr = "["; //json formatted string with results
    for (auto it = allResults.rbegin() ; it != allResults.rend() ; it++)
    {
        //                   score               name                    details
        finalstr += "[" + it->at(0) + ",\"" + it->at(1) + "\",\"" + base64_encode(it->at(2)) + "\"],";
    }
    finalstr.pop_back(); //remove excess comma
    finalstr += "]"; //close list
    return finalstr;
}
void Searcher::slice_search_exact_strict(string processed_query, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score)
{
    auto endit = next(this -> minimal_data.begin(), end);
    
    for(auto it = next(this -> minimal_data.begin(), start); it != endit; it++)
    {
        string stringToCheck = it -> at(0);
        auto index = stringToCheck.find(processed_query);
        if (index != string::npos && 
            ( stringToCheck.length() == index + processed_query.length() || seperators.find(stringToCheck[index + processed_query.length()]) != string::npos ) && //proceeded by end of string or delimiter
            ( index == 0                                                 || seperators.find(stringToCheck[index -1])                         != string::npos )    //proceeds end of string or delimiter
        )
        {
        threadMutex.lock();
        allResults.push_back(vector<string>{"100", stringToCheck, it->at(1)});
        threadMutex.unlock();
        }
    }
}
void Searcher::slice_search_exact_loose(vector<string> processed_query_splited, unsigned start, unsigned end, vector<vector<string>>& allResults, mutex& threadMutex, const float& min_score)
{
    float percentToAdd = 100/processed_query_splited.size();
    auto endit = next(this -> minimal_data.begin(), end);
    for(auto it = next(this -> minimal_data.begin(), start); it != endit; it++)
    {
        string stringToCheck = it -> at(0);
        float score = 0;
        for (const string &namePart : processed_query_splited)
        {
            auto index = stringToCheck.find(namePart); 
            if (index != string::npos && 
                ( stringToCheck.length() == index + namePart.length() || seperators.find(stringToCheck[index + namePart.length()]) != string::npos ) && //proceeded by end of string or delimiter
                ( index == 0                                          || seperators.find(stringToCheck[index -1])                  != string::npos )    //proceeds end of string or delimiter
            )
            {
                score += percentToAdd;
            }
        }
        if (score >= min_score)
        {
            threadMutex.lock();
            allResults.push_back(vector<string>{to_string(score), stringToCheck, it->at(1)});
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
            threadMutex.lock();
            allResults.push_back(vector<string>{to_string(score), stringToCheck, it->at(1)});
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
            threadMutex.lock();
            allResults.push_back(vector<string>{to_string(score), stringToCheck, it->at(1)});
            threadMutex.unlock();
        }
    }
}
/*
    run search on splice_count splices of the database, each running in a different thread
    stores to results list of lists with below format:
        [score, name, zlib-encoded details]
*/
unsigned Searcher::search_by_name(vector<vector<string>>& results, string query, float min_score, unsigned splice_count, search_type searchType)
{
    // exactMatch only works when fuzzy is false. it ensures query matches exact word in result
    vector<string> splitted;
    if (searchType == basic or searchType == exactL)
    {
        boost::split(splitted, query, boost::is_any_of(" "));
        // for (const auto& i:splitted) 
        //     cout << i << endl;
    }
    mutex threadMu;
    vector<future<void>> processes;
    unsigned splitSize = static_cast<unsigned>(this -> size/splice_count)+1;
    unsigned start = 0;
    //TODO: make sure iterators aren't missing the borders
    auto time0 = std::chrono::high_resolution_clock::now();
    if (searchType == fuzzy)
    {
        for (unsigned i = splitSize ; i < this-> size + 1 ;start = i, i+=splitSize)
            processes.push_back(async(&Searcher::slice_search_fuzzy, this, query, start, i, ref(results), ref(threadMu), ref(min_score)));
        processes.push_back(async(&Searcher::slice_search_fuzzy, this, query, start, this -> minimal_data.size(),ref(results), ref(threadMu), ref(min_score)));
    }
    else if (searchType == exactS)
    {
        for (unsigned i = splitSize ; i < this-> size + 1 ;start = i, i+=splitSize)
            processes.push_back(async(&Searcher::slice_search_exact_strict, this, query, start, i, ref(results), ref(threadMu), ref(min_score)));
        processes.push_back(async(&Searcher::slice_search_exact_strict, this, query, start, this -> minimal_data.size(), ref(results), ref(threadMu), ref(min_score)));
    }
    else if (searchType == basic)
    {
        for (unsigned i = splitSize ; i < this-> size + 1 ;start = i, i+=splitSize)
            processes.push_back(async(&Searcher::slice_search_basic, this, splitted, start, i, ref(results), ref(threadMu), ref(min_score)));
        processes.push_back(async(&Searcher::slice_search_basic, this, splitted, start, this -> minimal_data.size(), ref(results), ref(threadMu), ref(min_score)));
    }
    else if (searchType == exactL)
    {
        for (unsigned i = splitSize ; i < this-> size + 1 ;start = i, i+=splitSize)
            processes.push_back(async(&Searcher::slice_search_exact_loose, this, splitted, start, i, ref(results), ref(threadMu), ref(min_score)));
        processes.push_back(async(&Searcher::slice_search_exact_loose, this, splitted, start, this -> minimal_data.size(), ref(results), ref(threadMu), ref(min_score)));
    }
    cout << "Processes started, waiting for output..\n";
    for (int i = 0; i < splice_count; ++i)
        processes[i].get();
    auto time1 = std::chrono::high_resolution_clock::now(); 
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(time1 - time0);
    cout << "Took " << duration.count() << " milliseconds" << endl;
    display_mem_usage();
    return duration.count();

}
/*
    load database to RAM, as a list of lists:
        [name, zlib-encoded details]
*/
Searcher::Searcher(string dbPath)
{
    ifstream fileStream(dbPath);
    string line;
    int urlLen = string(BASEURL).length();
    auto start = std::chrono::high_resolution_clock::now();
    while(getline(fileStream, line))
    {
        string debug = line;
        try{
            if (line[0] == '"' and line[line.length()-1] == '{')
            {
                string concatedString = "";
                // name - 0
                string name = line.substr(1, line.length()-5);
                boost::algorithm::to_lower(name);
                boost::algorithm::replace_all_copy(name, DELIMITER, "-");
                getline(fileStream, line);
                // files:
                if (line[0] == '\t')
                {
                    // url - 1
                    concatedString += line.substr(9 + urlLen, line.length() - 11 - urlLen) + '|';
                    // type - skip
                    getline(fileStream, line);
                    // date - 2
                    getline(fileStream, line);
                    concatedString += line.substr(10, line.length()-18) + '|';
                    // size - 3
                    getline(fileStream, line);
                    concatedString += line.substr(10, line.length()-11) + '|';
                }
                //directories:
                else
                {
                    // url - 1
                    concatedString += line.substr(8 + urlLen, line.length() - 10 - urlLen) + '|';
                    // date - 2
                    getline(fileStream, line);
                    concatedString += line.substr(9, line.length()-17) + '|';
                }
                minimal_data.push_back(vector<string>{name, zlibencode(concatedString)});
            }
        } catch(out_of_range) {
            cout << "Exception encountered reading \"" << debug << "\" from db, continuing anyway...\n";
            continue;
        }
    }
    cout << "Removing Dupes.." << endl;
    unsigned old_size = minimal_data.size();
    std::sort(minimal_data.begin(), minimal_data.end());
    minimal_data.erase(std::unique(minimal_data.begin(), minimal_data.end()), minimal_data.end());
    this -> size = minimal_data.size();
    auto stop = std::chrono::high_resolution_clock::now(); 
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(stop - start);
    cout << "Took " << duration.count() << " milliseconds" << endl;
    cout << "Usable len of data: " << this -> size << ", Had " << old_size-this->size << " Dupes" << endl;
    display_mem_usage();

}

