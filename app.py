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
    mapsDict = dict()
    winsDict = dict()
    # just for now, only take K/D
    for elem in userSteamStats['playerstats']['stats']:
        if (elem['name'] == 'total_kills'): userStats['totalKills'] = elem['value']
        elif(elem['name'] == 'total_deaths'): userStats['totalDeaths'] = elem['value']
        elif(elem['name'] == 'total_kills_headshot'): headshotKills = elem['value']
        elif(elem['name'] == 'total_rounds_played'): roundsPlayed = elem['value']
        elif(elem['name'] == 'total_wins'): roundsWon = elem['value']
        elif(elem['name'] == 'last_match_kills'): lastKills = elem['value']
        elif(elem['name'] == 'last_match_deaths'): lastDeaths = elem['value']
        elif('total_rounds_map_de' in elem['name']): mapsDict[elem['name']] = elem['value']
        elif('total_wins_map_de' in elem['name']): winsDict[elem['name']] = elem['value']

    userStats['overallWinRate'] = roundsWon / roundsPlayed
    userStats['headshotRatio'] = headshotKills / userStats['totalKills']
    userStats['killDeathRatio'] = userStats['totalKills'] / userStats['totalDeaths']
    userStats['lastKillDeathRatio'] = lastKills / lastDeaths
    userStats['favoriteMap'],userStats['favoriteMapWinRate'] = \
        getFavoriteMapAndWinRate(mapsDict, winsDict)
    return userStats
    # want kdr (compare to pro overall k/d), headshot %,
    # favorite map, favorite map win %, 
    # overall win rate (how to close out more rounds? idk),
    # last map k/d (compare to pro last match, teach warmup)

def getFavoriteMapAndWinRate(mapsDict, winsDict):
    favoriteMap = ''
    favoriteMapRounds = 0
    favoriteMapRoundWins = 0
    for map in mapsDict:
        if mapsDict[map] > favoriteMapRounds:
            favoriteMap = map[map.find("de_"):]
            favoriteMapRounds = mapsDict[map]

    # is there a better way to loop through this?
    for map in winsDict:
        if favoriteMap in map:
            favoriteMapRoundWins = winsDict[map]
    
    return favoriteMap, favoriteMapRoundWins / favoriteMapRounds

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

# needed for jinja
def getUserLocals(steamID):
    userStats = getSteamUserStats(steamID)
    userKillDeath = userStats['killDeathRatio']
    userKillDeath = round(userKillDeath, 2)
    userHeadshotPercent = userStats['headshotRatio'] * 100
    userHeadshotPercent = round(userHeadshotPercent, 2)
    userOverallWinPercent = userStats['overallWinRate'] * 100
    userOverallWinPercent = round(userOverallWinPercent, 2)
    userLastMatchKillDeath = userStats['lastKillDeathRatio']
    userLastMatchKillDeath = round(userLastMatchKillDeath, 2)
    userFavoriteMap = userStats['favoriteMap']
    userFavoriteMapWinRate = userStats['favoriteMapWinRate'] * 100
    userFavoriteMapWinRate = round(userFavoriteMapWinRate, 2)

    return userKillDeath, userHeadshotPercent, userOverallWinPercent, \
        userLastMatchKillDeath, userFavoriteMap, userFavoriteMapWinRate

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

# needed for jinja
def getHLTVLocals(d, map):
    name = d['nickname']
    killDeathRatio = d['killDeathRatio']
    headshotPercent = d['percentHeadshot']
    winPercent = d['winPercent']
    lastMatchKillDeathRatio = d['lastMatchKillDeathRatio']

    legalMaps = ['de_dust2', 'de_inferno', 'de_nuke', 'de_train',
    'de_vertigo', 'de_cbble']
    if map in legalMaps:
        favoriteMapWinPercent = \
            hltvScript.getFavoriteMapWinPercentFromWord(name, map)
    else:
        favoriteMapWinPercent = "Map not in HLTV database"
    
    return name, killDeathRatio, headshotPercent, winPercent, \
        lastMatchKillDeathRatio, favoriteMapWinPercent

# put everything in a dict for easier access than just the values listed out
def getUserStatsDict(steamID):
    userKillDeath, userHeadshotPercent, userOverallWinPercent, \
        userLastMatchKillDeath, userFavoriteMap, userFavoriteMapWinRate = \
            getUserLocals(steamID)
    d = dict()
    d['userKillDeath'] = userKillDeath
    d['userHeadshotPercent'] = userHeadshotPercent
    d['userOverallWinPercent'] = userOverallWinPercent
    d['userLastMatchKillDeath'] = userLastMatchKillDeath
    d['userFavoriteMap'] = userFavoriteMap
    d['userFavoriteMapWinRate'] = userFavoriteMapWinRate
    
    return d

def getThreeLowestStats(userDict, hltvDict):

    # So the steam API is old and they have made almost no updates since it
    # came out. The only actual competitive maps that are tracked are the ones
    # in legalMaps
    legalMaps = ['de_dust2', 'de_inferno', 'de_nuke', 'de_train',
    'de_vertigo', 'de_cbble']
    fractions = dict()

    killDeathFraction = userDict['userKillDeath'] / hltvDict['killDeathRatio']
    headshotFraction = userDict['userHeadshotPercent'] / hltvDict['percentHeadshot']
    winPercentFraction = userDict['userOverallWinPercent'] / hltvDict['winPercent']
    lastKillDeathFraction = userDict['userLastMatchKillDeath'] / hltvDict['lastMatchKillDeathRatio']
    proNickname = hltvDict['nickname']
    favoriteMapFraction = userDict['userFavoriteMapWinRate'] / \
        hltvScript.getFavoriteMapWinPercentFromWord(proNickname, userDict['userFavoriteMap'])

    fractions['K/D Ratio'] = killDeathFraction
    fractions['Headshot %'] = headshotFraction
    fractions['Overall Win Rate'] = winPercentFraction
    fractions['Last Match K/D Ratio'] = lastKillDeathFraction
    if(userDict["userFavoriteMap"] in legalMaps):
        fractions[f'{userDict["userFavoriteMap"]} Win Rate'] = favoriteMapFraction

    sortedValues = sorted(fractions.values())
    lowest1, lowest2, lowest3 = sortedValues[0], sortedValues[1], sortedValues[2]

    for elem in fractions:
        if(fractions[elem] == lowest1): lowest1 = elem
        elif(fractions[elem] == lowest2): lowest2 = elem
        elif(fractions[elem] == lowest3): lowest3 = elem
    
    return lowest1, lowest2, lowest3

def getFirstWorkshopItemLink(workshopLink):
    workshopRequest = requests.get(workshopLink).text
    # loop until we get to the first item:
    lines = workshopRequest.splitlines()
    for i in range(len(lines)):
        if("workshopBrowseRow" in lines[i]):
            j0 = lines[i + 1].index('"') + 1
            j1 = lines[i + 1][j0:].index('"')
            link = lines[i + 1][j0: j0 + j1]
            return link

def getFirstYoutubeThumbnailAndLink(link):
    youtubeRequest = requests.get(link).text.splitlines()
    for i in range(len(youtubeRequest)):
        if ('height="138"' in youtubeRequest[i]):
            linkLine = youtubeRequest[i-1]
            imgLine = youtubeRequest[i]
            break
    i0 = linkLine.index("href=") + 6
    i1 = linkLine[i0:].index('"')
    link = "http://youtube.com" + linkLine[i0:i0 + i1]
    
    i0 = imgLine.index("src=") + 5
    i1 = imgLine[i0:].index('"')
    image = imgLine[i0:i0 + i1]

    return link,image

# main profile page, for comparing user stats with their favorite pro's stats
# since Flask uses Jinja, variables can be passed into the html
# AS LONG AS THEY'RE DEFINED AS LOCALS
@app.route('/profile/<steamID>', methods=["GET", "POST"])
def profile(steamID):
    accountName, accountProfilePicture = getUserInfo(steamID)
    userProfile = getUserProfile(steamID)

    userKillDeath, userHeadshotPercent, userOverallWinPercent, \
        userLastMatchKillDeath, userFavoriteMap, userFavoriteMapWinRate = \
            getUserLocals(steamID)
    
    if(len(getUserTeam(userProfile)) > 0):
        userTeam = getUserTeam(userProfile)[0]
        userHLTVStats = hltvScript.getPlayerStatsFromWord(userTeam)
        favoriteName, favoriteKillDeath, favoriteHeadshotPercent, \
            favoriteWinPercent, favoriteLastMatchKillDeath, \
                favoriteFavoriteMapWinPercent = \
                    getHLTVLocals(userHLTVStats, userFavoriteMap)  

        userStatsDict = getUserStatsDict(steamID)
        lowest1, lowest2, lowest3 = getThreeLowestStats(userStatsDict, userHLTVStats)

    if(request.method == "POST"):
        try:
            button = request.form["searchName"]
            setFavoritePlayer(button, steamID)
            # update list
            userProfile = getUserProfile(steamID)
            userTeam = getUserTeam(userProfile)[0]

            # everything that follows is repeated from before because
            # you have to account for first time adding a player
            userHLTVStats = hltvScript.getPlayerStatsFromWord(button)
            favoriteName, favoriteKillDeath, favoriteHeadshotPercent, \
            favoriteWinPercent, favoriteLastMatchKillDeath, \
                favoriteFavoriteMapWinPercent = \
                    getHLTVLocals(userHLTVStats, userFavoriteMap)
            userStatsDict = getUserStatsDict(steamID)
            lowest1, lowest2, lowest3 = getThreeLowestStats(userStatsDict, userHLTVStats)

        except:
            try:
                searchResults = hltvScript.getPlayerStatsFromWord(request.form["search"])
                if(searchResults == None):
                    searchResults = "Name not found: " + request.form["search"]
                if(isinstance(searchResults, str)):
                    return render_template("profile.html", **locals())
                
                searchName, searchKillDeathRatio, searchHeadshotPercent, \
                    searchWinPercent, searchLastMatchKillDeathRatio, \
                        searchFavoriteMapWinPercent = \
                            getHLTVLocals(searchResults, userFavoriteMap)
                
            except:
                return render_template("profile.html", **locals())
    return render_template("profile.html",  **locals())

@app.route('/K/D Ratio/<steamID>')
def kdRatioPage(steamID):
    # link is to youtube search
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/33cSw17")
    return render_template("kdPage.html", **locals())

@app.route('/Headshot %/<steamID>')
def headshotPage(steamID):
    # link is to steam workshop search
    workshopLink = getFirstWorkshopItemLink("https://bit.ly/37BWQKH")
    # link is to youtube search
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/2QO4cVN")
    return render_template("headshotPage.html", **locals())

@app.route('/Overall Win Rate/<steamID>')
def overallWinRatePage(steamID):
    # link is to youtube search
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/34fpwHC")
    return render_template("winRatePage.html", **locals())

@app.route('/Last Match K/D Ratio/<steamID>')
def warmupPage(steamID):
    # link is to steam workshop search
    workshopLink = getFirstWorkshopItemLink("https://bit.ly/2OiDpPJ")
    # link is to youtube search
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/2qLrUqO")
    return render_template("warmupPage.html", **locals())

@app.route('/de_dust2 Win Rate/<steamID>')
def dust2Page(steamID):
    return '''<p>hello world</p>'''

@app.route('/de_inferno Win Rate/<steamID>')
def infernoPage(steamID):
    return '''<p>hello world</p>'''

@app.route('/de_nuke Win Rate/<steamID>')
def nukePage(steamID):
    return '''<p>hello world</p>'''

@app.route('/de_train Win Rate/<steamID>')
def trainPage(steamID):
    return '''<p>hello world</p>'''

@app.route('/de_vertigo Win Rate/<steamID>')
def vertigoPage(steamID):
    return '''<p>hello world</p>'''

@app.route('/de_cbble Win Rate/<steamID>')
def cbblePage(steamID):
    return '''<p>hello world</p>'''

# page for recommending ways to improve
@app.route('/recommendations/<steamID>')
def recommendations():
    accountName, accountProfilePicture = getUserInfo(steamID)

if __name__ == "__main__":
	app.run(port="5000")