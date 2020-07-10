from flask import Flask, render_template, request, abort
from rapidfuzz.utils import default_process
import zmq
PORT = "612300"
app = Flask(__name__)
#app.debug = True
#connect to IPC port
context = zmq.Context()
client = context.socket(zmq.REQ)
client.connect(f"tcp://0.0.0.0:{PORT}")


class Constants:
   minQueryLength = 3
   maxQueryLength = 300
   #for all search types except fuzzy
   minScoreToShow: int = 66
   #for fuzzy. generally takes more time so has a higher min score
   minScoreToShowForFuzz: int = 80
   #base URL stripped from base DB files
   baseURL = "https://the-eye.eu/public/"
   #TODO: maximumResultCount = ? implement in search first
   searchBarPlaceholder = "Query"
   submitButtonPlaceholder = "Search"
   inputNames = {
       "query": "query",
       "searchType": "type",
   }
   types = [
       {"label": "Fuzzy", "value": "fuzzy"},
       {"label": "Basic", "value": "basic"},
       {"label": "Strict Perfect match", "value": "spm"},
       {"label": "Loose Perfect match", "value": "lpm"}
   ]
   sortMethods = [
       {"label": "Sort by grades", "value": "grade"}
   ]
   errors = {
       1: f"Query must contain between {minQueryLength} and {maxQueryLength} alphanumerical characters(words maximum separated by one space)",
       2: "Invalid query",
   }
#temp


@app.route('/', methods=['POST', 'GET'])
def search_page():
   if request.method == 'POST':
      if all(inputName in request.form for inputName in Constants.inputNames.values()):
         #get results...
         query = request.form[Constants.inputNames["query"]]
         query = processQuery(query)
         if not Constants.minQueryLength <= len(query) <= Constants.maxQueryLength:
            return render_template("error.html", error=Constants.errors[1])
         results = askForResults(
             query, request.form[Constants.inputNames["searchType"]])
         if results is None:
            return render_template("error.html", error=Constants.errors[2])
         return render_template("results.html", results=results, query=query, base=Constants.baseURL)
      else:
         return render_template("error.html", error=Constants.errors[2])
   return render_template("main.html", constants=Constants)


def processQuery(query: str) -> str:
   return default_process(" ".join(query.split())).replace('  ', ' ')


def askForResults(query: str, search_type: str):
   Stype = search_type
   minscore = str(Constants.minScoreToShow)
   if Stype == "fuzzy":
      minscore = str(Constants.minScoreToShowForFuzz)
      Stype = "fu"
   elif Stype == "basic":
      Stype = "ba"
   elif Stype == "lpm":
      Stype = "el"
   elif Stype == "spm":
      Stype = "es"
   else:
      return None
   # Message format:
   #  TTMMQQQQ..
   #  * first two characters specify Type:
   #  * next two characters specify minimum score(int between 10 and 99)
   #  * all subsequent characters are the passed query
   message = Stype + minscore + query
   client.send_string(message)
   return client.recv().decode("utf-8")


if __name__ == '__main__':
   app.run(host='0.0.0.0')
