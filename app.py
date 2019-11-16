import hltvScript
# reminder it only searches for players who have at least 100 recorded matches
import requests
from flask import Flask, render_template, redirect, request, url_for, g, session
from flask_openid import OpenID
from urllib.parse import urlencode, quote
import csv
import ast


app = Flask(__name__)
oid = OpenID(app, './OpenID-Store', safe_roots=[])
steamAPIKey = "99265BB0548A6F48052B8784D88B8A44"

'''
@app.before_request
def lookup_current_user():
    g.user = None
    if 'openid' in session:
        openid = session['open']
        g.user = User.query.filter_by(openid=openid).first()

@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
'''

'''
    steamID = request.args["openid.claimed_id"]
    steamID = steamID[steamID.index("/id/") + 4:]
    return steamID
'''

@app.route('/')
def index():
    return '''
    <a href="/signin">
        <img alt="Sign in with steam" src="https://bit.ly/2QkePzb"
        width=118 height=51></img>
    </a>
    '''

steamURL = 'https://steamcommunity.com/openid/login'

# begin not mine
@app.route('/signin')
def signIn():
    params = {
    'openid.ns': "http://specs.openid.net/auth/2.0",
    'openid.identity': "http://specs.openid.net/auth/2.0/identifier_select",
    'openid.claimed_id': "http://specs.openid.net/auth/2.0/identifier_select",
    'openid.mode': 'checkid_setup',
    'openid.return_to': 'http://127.0.0.1:5000/authorize',
    'openid.realm': 'http://127.0.0.1:5000'
    }
    queryString = urlencode(params)
    authURL = steamURL + "?" + queryString
    return redirect(authURL)

@app.route('/authorize')
def authorize():
    steamID = request.args["openid.claimed_id"]
    steamID = steamID[steamID.index("/id/") + 4:]
    return redirect(url_for('profile', steamID=steamID))
# end not mine

def getSteamUserStats(steamID):
    pass

def getUserProfile(steamID):
    userProfile = None
    with open("userData.csv") as csvfile:
        profileReader = csv.reader(csvfile, delimiter=',')
        for row in profileReader:
            if steamID in row:
                userProfile = row
    if userProfile == None:
        with open("userData.csv", "a+") as csvfile:
            csvfile.write(f"{steamID},[]\n")
        with open("userData.csv") as csvfile:
            profileReader = csv.reader(csvfile, delimiter=',')
            userProfile = profileReader[-1]
        
    return userProfile

def getUserTeam(L):
    return ast.literal_eval(L[1])
    return L[1].strip('][').split()

def addPlayerToTeam(player, steamID):
    userProfile = getUserProfile(steamID)
    userTeam = getUserTeam(userProfile)
    for elem in userTeam:
        elem.replace("'", "")
        elem.replace('"', '')
    print(len(userTeam))
    if(len(userTeam) < 5 and player not in userTeam):
        userTeam.append(player)
    newRow = [steamID, userTeam]

    with open("userData.csv", "r") as readFile:
        profileReader = csv.reader(readFile)
        lines = list(profileReader)
        for i in range(len(lines)):
            if(steamID in lines[i]): rowIndex = i
        lines[rowIndex] = newRow
    
    with open("userData.csv", "w") as writeFile:
        profileWriter = csv.writer(writeFile)
        profileWriter.writerows(lines)

@app.route('/profile/<steamID>', methods=["GET", "POST"])
def profile(steamID):
    accountName, accountProfilePicture = getUserInfo(steamID)
    userProfile = getUserProfile(steamID)
    userTeam = getUserTeam(userProfile)

    if(request.method == "POST"):
        try:
            button = request.form["searchName"]
            addPlayerToTeam(button, steamID)
        except:
            try:
                searchResults = hltvScript.getPlayerStatsFromWord(request.form["search"])
                if(searchResults == None):
                    searchResults = "Name not found: " + request.form["search"]
                if(isinstance(searchResults, str)):
                    return render_template("profile.html", **locals())
                    
                searchName = searchResults['nickname']
                searchRating = searchResults['rating']
            except:
                return render_template("profile.html", **locals())
    return render_template("profile.html",  **locals())

def getUserInfo(steamID):
    requestURL = 'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key='
    requestURL += steamAPIKey
    requestURL += '&steamids='
    requestURL += str(steamID)
    playerInfo = requests.get(requestURL).json()
    accountName = playerInfo['response']['players'][0]['personaname']
    accountProfilePicture = playerInfo['response']['players'][0]['avatar']
    return accountName, accountProfilePicture
    
# tomorrow add team formation, self stats, saving in csv?

if __name__ == "__main__":
	app.run(port="5000")