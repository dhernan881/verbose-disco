import hltvScript
# reminder it only searches for players who have at least 100 recorded matches
import requests
from flask import Flask, render_template, redirect, request, url_for, g, session
from flask_openid import OpenID
from urllib.parse import urlencode, quote
import csv
import ast


app = Flask(__name__)
# oid = OpenID(app, './OpenID-Store', safe_roots=[])
steamAPIKey = "99265BB0548A6F48052B8784D88B8A44"

@app.route('/')
def index():
    return '''
    <a href="/signin">
        <img alt="Sign in with steam" src="https://bit.ly/2QkePzb"
        width=118 height=51></img>
    </a>
    '''

steamURL = 'https://steamcommunity.com/openid/login'

# BEGIN NOT MINE
# from https://github.com/fourcube/minimal-steam-openid
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
# END NOT MINE

# gets the user's in-game CS:GO stats; will probably be migrated into 
# another script just for clarity/less clutter
def getSteamUserStats(steamID):
    steamAPILink = 'https://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v2/?appid=730&key='
    steamAPILink += steamAPIKey
    steamAPILink += "&steamid="
    steamAPILink += steamID
    userSteamStats = requests.get(steamAPILink).json()

    userStats = dict()
    # just for now, only take K/D
    for elem in userSteamStats['playerstats']['stats']:
        if (elem['name'] == 'total_kills'):
            userStats['totalKills'] = elem['value']
        elif(elem['name'] == 'total_deaths'):
            userStats['totalDeaths'] = elem['value']
    userStats['killDeathRatio'] = userStats['totalKills'] / userStats['totalDeaths']
    return userStats

# get's the user's profile from csv [steamID, [favoritePlayer]]
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
            userProfile = [f'{steamID}','[]']
        
    return userProfile

# gets just the team from a given user profile
def getUserTeam(L):
    return ast.literal_eval(L[1])

# sets the user's favoritePlayer in the csv
def setFavoritePlayer(player, steamID):
    userProfile = getUserProfile(steamID)
    newRow = [steamID, [player]]

    with open("userData.csv", "r") as readFile:
        profileReader = csv.reader(readFile)
        lines = list(profileReader)
        for i in range(len(lines)):
            if(steamID in lines[i]):
                rowIndex = i
        lines[rowIndex] = newRow
    
    with open("userData.csv", "w") as writeFile:
        profileWriter = csv.writer(writeFile)
        profileWriter.writerows(lines)

# main profile page, for comparing user stats with their favorite pro's stats
@app.route('/profile/<steamID>', methods=["GET", "POST"])
def profile(steamID):
    accountName, accountProfilePicture = getUserInfo(steamID)
    userProfile = getUserProfile(steamID)
    if(len(getUserTeam(userProfile)) > 0):
        userTeam = getUserTeam(userProfile)
    else:
        userStats = getSteamUserStats(steamID)
        userKillDeath = userStats['killDeathRatio']
        userKillDeath = round(userKillDeath, 2)

    if(request.method == "POST"):
        try:
            button = request.form["searchName"]
            setFavoritePlayer(button, steamID)
            # update list
            userProfile = getUserProfile(steamID)
            userTeam = getUserTeam(userProfile)
        except:
            try:
                searchResults = hltvScript.getPlayerStatsFromWord(request.form["search"])
                if(searchResults == None):
                    searchResults = "Name not found: " + request.form["search"]
                if(isinstance(searchResults, str)):
                    return render_template("profile.html", **locals())
                    
                searchName = searchResults['nickname']
                searchKillDeathRatio = searchResults['killDeathRatio']
                searchRating = searchResults['rating']
            except:
                return render_template("profile.html", **locals())
    return render_template("profile.html",  **locals())

# page for recommending ways to improve
@app.route('/recommendations/<steamID>')
def recommendations(steamID, option1, option2, option3):
    accountName, accountProfilePicture = getUserInfo(steamID)

# gets the user's steam info (name and profile picture)
def getUserInfo(steamID):
    requestURL = 'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key='
    requestURL += steamAPIKey
    requestURL += '&steamids='
    requestURL += str(steamID)
    playerInfo = requests.get(requestURL).json()
    accountName = playerInfo['response']['players'][0]['personaname']
    accountProfilePicture = playerInfo['response']['players'][0]['avatarmedium']
    return accountName, accountProfilePicture

if __name__ == "__main__":
	app.run(port="5000")