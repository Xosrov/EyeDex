from flask import Flask, render_template, request
from argparse import ArgumentParser
import zmq
#internal communication port
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
       1: f"Query must contain between {minQueryLength} and {maxQueryLength} characters",
       2: "Invalid query",
   }


@app.route('/', methods=['POST', 'GET'])
def search_page():
   if request.method == 'POST':
      if all(inputName in request.form for inputName in Constants.inputNames.values()):
         #get results...
         query = request.form[Constants.inputNames["query"]]
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
   parser = ArgumentParser(description="Initiate front-end for searcher")
   parser.add_argument('-mfs', '--minimum-fuzzy_score', dest='minIntFuzz', type=int,
                       help=f"Minumum score for fuzzy search(affects search times) -> default {Constants.minScoreToShowForFuzz}")
   parser.add_argument('-mfo', '--minimum-others_score', dest='minIntOthers', type=int,
                       help=f"Minumum score for other search types(doesn't affect performance as much) -> default {Constants.minScoreToShow}")
   parser.add_argument('-p', '--port', dest='port', type=str, default='5000',
                       help=f"Port for front-end -> default 5000 at localhost:5000")
   args = parser.parse_args()
   if args.port == PORT:
      print("Port already in use for back-end, try another")
      quit()
   if args.minIntFuzz is not None:
      Constants.minScoreToShowForFuzz = args.minIntFuzz
      print(f"Using {args.minIntFuzz} as min for fuzz")
   if args.minIntOthers is not None:
      Constants.minScoreToShow = args.minIntOthers
      print(f"Using {args.minIntOthers} as min for others")
   app.run(host='0.0.0.0', port=args.port)
