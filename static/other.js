/* laod database and shit like that */
$(document).ready(function() {
    document.body.innerHTML = "<h2 class=\"red\">" + results.length +  " results for "+ query + "</h1>\n";
    var fullres = []; //list of lists containing decompressed results
    for (let i = 0 ; i < results.length ; i++)
    {
        listToAdd = [results[i][0], results[i][1]];
        getDecompressed(results[i][2], listToAdd);
        fullres.push(listToAdd);
    }
    //sort by score and put dirs first:
    fullres.sort(function(a,b) {
        scorea = parseFloat(a[0]) + (a.length == 4 ? 100.0 : 0.0);
        scoreb = parseFloat(b[0]) + (b.length == 4 ? 100.0 : 0.0);
        return scorea < scoreb;
    });
    //TODO: theres gotta be a better way for this lol
    //TODO: get this from page size data:
    var each_page = 20; 
    var pageCounter = 0;
    var totalCounter = 1;
    digitCount = results.length.toString().length;
    var finalStr = "<h2 class=\"red\">Directories</h1>\n<hr />\n";
    var startFiles = false;
    for (data of fullres) {
        var url = data[2];
        if (pageCounter == each_page)
        {
            finalStr += "<div class=\"sep\">\n";
            pageCounter = 0;
        }
        if (data.length == 4) {
            finalStr += "<h1>" + pad(totalCounter, digitCount) + ". At score " + data[0] + " is \"" + data[1] + "\" Directory with below info:</h1>";
            finalStr += "<section class=\"data\"><p>Date: " + data[3] + "</p>";
        }
        else {
            if (!startFiles) {
                finalStr += "<h2 class=\"red\">Files</h1>\n<hr />\n";
                startFiles = true;
            }
            var ftype = "";
            if (url.lastIndexOf('/') > url.lastIndexOf('.'))
                ftype = "???";
            else
                ftype = url.substr(url.lastIndexOf('.'));
            finalStr += "<h1>" + pad(totalCounter, digitCount) + ". At score " + data[0] + " is \"" + data[1] + "\" File with below info:</h1>";
            finalStr += "<section class=\"data\"><p>Date: " + data[3] + "</p><p>Type: " + ftype + "</p><p>Size: " + data[4] + "</p>";
        }
        finalStr += "<a target=\"_blank\" href=\"" + url + "\">" + url + "</a></section>\n";
        pageCounter ++;
        totalCounter++;
    }
    document.body.innerHTML += finalStr;

    
});
//delimiter is '|' from other files
function getDecompressed (compressedData, whereToAppend) {
    var charData    = atob(compressedData).split('').map(function(x){return x.charCodeAt(0);});
    var binData     = new Uint8Array(charData);
    var concatedString     = String.fromCharCode.apply(null, new Uint16Array(pako.inflate(binData)));
    var listToAdd = concatedString.slice(0, -1).split("|");
    whereToAppend.push(baseURL + listToAdd[0])
    for (var i = 1 ; i < listToAdd.length ; i++) {
        whereToAppend.push(listToAdd[i]);
    }
}
function pad(number, length) {
    var str = '' + number;
    while (str.length < length) {
        str = '0' + str;
    }
    return str;
}
//load more results:
let index = 0;
let loading = true;
let selector = document.getElementsByClassName("sep");
window.onscroll = function(ev) { 
    if ((window.innerHeight + window.pageYOffset) >= document.body.offsetHeight) {
        AddMoreContent();
    }
};
function AddMoreContent() {
    if (loading) {
        try {
            selector[index].style.display = "block";
            index = index+1;
        } catch(err) { 
            loading=false;
        }
    }
}