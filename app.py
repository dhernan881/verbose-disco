import hltvScript # reminder it only searches for players who have >= 100 recorded matches
import steamScript # for steam functions
import requests
from flask import Flask, render_template, redirect, request, url_for, g, session
from flask_openid import OpenID
from urllib.parse import urlencode, quote
import csv
import ast

# compare with other people
# store sites already seen
# threading
# aesthetic

# NOTE that css for the html pages is from https://purecss.io/

app = Flask(__name__)
steamAPIKey = "99265BB0548A6F48052B8784D88B8A44"

# landing/index page
@app.route('/')
def index():
    return render_template('index.html')

# landing page with error message for private accounts
@app.route('/login-error')
def loginError():
    errormsg = '''To change privacy settings,
    Go to your profile -> Edit Profile -> My Profile (set to Public) -> Game Details (set to Public)'''
    return render_template('index.html', **locals())

# BEGIN NOT MINE
# from https://github.com/fourcube/minimal-steam-openid
@app.route('/signin')
def signIn():
    steamURL = 'https://steamcommunity.com/openid/login'
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

# get's the user's profile from csv [steamID, [favoritePlayer], [previous matches stats]]
def getUserProfile(steamID):
    userProfile = None
    with open("userData.csv") as csvfile:
        profileReader = csv.reader(csvfile, delimiter=',')
        for row in profileReader:
            if steamID in row:
                userProfile = row
    if userProfile == None:
        with open("userData.csv", "a+") as csvfile:
            csvfile.write(f"{steamID},[],[]\n")
        with open("userData.csv") as csvfile:
            profileReader = csv.reader(csvfile, delimiter=',')
            userProfile = [f'{steamID}','[]','[]']
        
    return userProfile

# needed for jinja
# returns a tuple of variables so I can define them in web functions
def getUserLocals(steamID):
    userStats = steamScript.getSteamUserStats(steamID)
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

# same as above but this is for the stats dict
def getLastMatchDictFromProfile(L):
    return ast.literal_eval(L[2])

# sets the user's favoritePlayer in the csv
def setFavoritePlayer(player, steamID):
    userProfile = getUserProfile(steamID)
    newRow = [steamID, [player], getLastMatchDictFromProfile(userProfile)]

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

# removes the row containing the given steamID from userData.csv
def removeAccountFromCSV(steamID):
    with open("userData.csv", "r") as readFile:
        profileReader = csv.reader(readFile)
        lines = list(profileReader)
        for i in range(len(lines)):
            if(steamID in lines[i]):
                rowIndex = i
        lines.pop(rowIndex)

    with open("userData.csv", "w") as writeFile:
        profileWriter = csv.writer(writeFile)
        profileWriter.writerows(lines)

# updates the user's previous match stats
def updateStats(steamID, stats):
    userProfile = getUserProfile(steamID)
    # get stats list, then append new stats to it
    matchStats = getLastMatchDictFromProfile(userProfile)
    if(len(matchStats) == 0 or matchStats[-1] != stats): # short circuit big brain
        matchStats.append(stats)
        # newStats = oldStats + [stats]
    newRow = [steamID, getUserTeam(userProfile), matchStats]

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

# builds the stats for formatting for Google Charts javascript script
# google charts from https://bit.ly/37LLkwJ
def buildGraphStats(stats):
    graphStats = [['Game', 'K/D Ratio', 'Average Damage/Round']]
    kdrGraphStats = [['Game', 'K/D Ratio']]
    adrGraphStats = [['Game', 'Average Damage/Round']]
    for i in range(len(stats)):
        gameNumber = i + 1
        gameKDR = stats[i]['lastMatchKDR']
        gameADR = stats[i]['lastMatchADR']
        kdrGraphStats.append([gameNumber, gameKDR])
        adrGraphStats.append([gameNumber, gameADR])
    return kdrGraphStats,adrGraphStats

# needed for jinja
# returns a tuple of variables so I can define them in web functions
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

# Gets the users three lowest stats with respect to their favorite player's
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

# gets the first item in the steam workshop from a given workshop page link
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

# gets the first youtube video link and thumbnail from a given youtube search link
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
# so basically there are a lot of variables that may seem to be random
# but are used in the html file
@app.route('/profile/<steamID>', methods=["GET", "POST"])
def profile(steamID):
    # if this try doesn't work (more specifically, the first lines),
    # return to the login page because their account is set to private somewhere
    try:
        accountName, accountProfilePicture = steamScript.getUserInfo(steamID)
        userProfile = getUserProfile(steamID)
        
        userKillDeath, userHeadshotPercent, userOverallWinPercent, \
            userLastMatchKillDeath, userFavoriteMap, userFavoriteMapWinRate = \
                getUserLocals(steamID)
    except:
        return redirect(url_for('loginError'))

    newestMatchStats = steamScript.getLastMatchKDRAndADR(steamID)
    updateStats(steamID, newestMatchStats)
    
    # have to update userProfile because updateStats destructively modifies
    # the list of match stats
    userProfile = getUserProfile(steamID)
    kdrGraphStats,adrGraphStats = \
        buildGraphStats(getLastMatchDictFromProfile(userProfile))
    
    # checks if we need to compare stats to a pro player
    # if the length of the list is 0, then they haven't set a player yet
    if(len(getUserTeam(userProfile)) > 0):
        userTeam = getUserTeam(userProfile)[0]
        userHLTVStats = hltvScript.getPlayerStatsFromWord(userTeam)
        try:
            favoriteName, favoriteKillDeath, favoriteHeadshotPercent, \
                favoriteWinPercent, favoriteLastMatchKillDeath, \
                    favoriteFavoriteMapWinPercent = \
                        getHLTVLocals(userHLTVStats, userFavoriteMap)
        except:
            hltvError = "Error. Could not connect to HLTV. Please try again later."
            return render_template("profile.html", **locals())

        userStatsDict = getUserStatsDict(steamID)
        lowest1, lowest2, lowest3 = getThreeLowestStats(userStatsDict, userHLTVStats)

    if(request.method == "POST"):
        try:
            # checks if the button was pressed, if it wasn't then it'll crash
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
            # checks if we searched for a player, if we didn't it would crash
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
            # if we didn't search or submit anything, then just load the page
            except:
                return render_template("profile.html", **locals())
    return render_template("profile.html",  **locals())

@app.route('/friendSearch/<steamID>', methods=['GET', 'POST'])
def friendSearch(steamID):
    if(steamID == 'nologin'):
        return redirect(url_for('index'))
    if(request.method == 'POST'):
        search = request.form["search"]
        friendResult = steamScript.getFriendSteamIDFromWord(steamID, search)
        if(isinstance(friendResult,list)):
            msg = 'Did you mean: '
            for name in friendResult:
                msg += name
                msg += ', '
            msg = msg[:-2] + '?' # chop off last comma
            return render_template('friendSearch.html', **locals())
        else:
            return redirect(url_for('compareFriends', yourSteamID=steamID, friendSteamID=friendResult))
    else:
        return render_template('friendSearch.html', **locals())

@app.route('/compareFriends/<yourSteamID>/<friendSteamID>')
def compareFriends(yourSteamID,friendSteamID):
    if(yourSteamID == 'nologin'):
        return redirect(url_for('index'))
    yourName, yourProfilePicture = steamScript.getUserInfo(yourSteamID)
    yourKillDeath, yourHeadshotPercent, yourOverallWinPercent, \
        yourLastMatchKillDeath, yourFavoriteMap, yourFavoriteMapWinRate = \
            getUserLocals(yourSteamID)

    try:
        friendName, friendProfilePicture = steamScript.getUserInfo(friendSteamID)
        friendKillDeath, friendHeadshotPercent, friendOverallWinPercent, \
            friendLastMatchKillDeath, friendFavoriteMap, friendFavoriteMapWinRate = \
                getUserLocals(friendSteamID)
        friendFavoriteMapWinRate = steamScript.getSpecificMapWinRate(friendSteamID, yourFavoriteMap)
    except:
        errormsg = "This friend has their game data set to private!"

    return render_template('compareFriends.html', **locals())

# the following pages are mini pages that list out recommendations for
# how a player can improve on a given stat.
# they combine hand-picked suggested materials but also pulls from
# what maps/videos are currently popular on the steam workshop and on youtube

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
    # link is to steam workshop search IF I USED LINK SHORTENER IT DOESN'T WORK
    workshopLink = getFirstWorkshopItemLink("https://steamcommunity.com/workshop/browse/?appid=730&searchtext=de_dust2+practice&childpublishedfileid=0&browsesort=trend&section=readytouseitems")
    # link is to youtube search
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/37COse9")
    return render_template("dust2page.html", **locals())

@app.route('/de_inferno Win Rate/<steamID>')
def infernoPage(steamID):
    workshopLink = getFirstWorkshopItemLink("https://steamcommunity.com/workshop/browse/?appid=730&searchtext=de_inferno+practice&childpublishedfileid=0&browsesort=trend&section=readytouseitems")
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/35wlJps")
    return render_template("infernoPage.html", **locals())

@app.route('/de_nuke Win Rate/<steamID>')
def nukePage(steamID):
    workshopLink = getFirstWorkshopItemLink("https://steamcommunity.com/workshop/browse/?appid=730&searchtext=de_nuke+practice&childpublishedfileid=0&browsesort=trend&section=readytouseitems")
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/34lbeoQ")
    return render_template("nukePage.html", **locals())

@app.route('/de_train Win Rate/<steamID>')
def trainPage(steamID):
    workshopLink = getFirstWorkshopItemLink("https://steamcommunity.com/workshop/browse/?appid=730&searchtext=de_train+practice&childpublishedfileid=0&browsesort=trend&section=readytouseitems")
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/37CVIqj")
    return render_template("trainPage.html", **locals())

@app.route('/de_vertigo Win Rate/<steamID>')
def vertigoPage(steamID):
    workshopLink = getFirstWorkshopItemLink("https://steamcommunity.com/workshop/browse/?appid=730&searchtext=de_vertigo+practice&childpublishedfileid=0&browsesort=trend&section=readytouseitems")
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/35xP5DL")
    return render_template("vertigoPage.html", **locals())

@app.route('/de_cbble Win Rate/<steamID>')
def cbblePage(steamID):
    workshopLink = getFirstWorkshopItemLink("https://steamcommunity.com/workshop/browse/?appid=730&searchtext=cobblestone+practice&childpublishedfileid=0&browsesort=trend&section=readytouseitems")
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/2XNfnPG")
    return render_template("cbblePage.html", **locals())

@app.route('/de_cache Win Rate/<steamID>')
def cachePage(steamID):
    workshopLink = getFirstWorkshopItemLink("https://steamcommunity.com/workshop/browse/?appid=730&searchtext=cache+practice&browsesort=trend&section=items&actualsort=trend&p=1&days=7")
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/34ltRsM")
    return render_template("cachePage.html", **locals())

@app.route('/de_mirage Win Rate/<steamID>')
def miragePage(steamID):
    workshopLink = getFirstWorkshopItemLink("https://steamcommunity.com/workshop/browse/?appid=730&searchtext=mirage+practice&browsesort=trend&section=items&actualsort=trend&p=1&days=7")
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/34l0iHz")
    return render_template("miragePage.html", **locals())

@app.route('/de_overpass Win Rate/<steamID>')
def overpassPage(steamID):
    workshopLink = getFirstWorkshopItemLink("https://steamcommunity.com/workshop/browse/?appid=730&searchtext=overpass+practice&browsesort=trend&section=items&actualsort=trend&p=1&days=7")
    youtubeLink,thumbnail = getFirstYoutubeThumbnailAndLink("https://bit.ly/37HC2Sr")
    return render_template("overpassPage.html", **locals())

# page for recommending ways to improve
@app.route('/recommendations/<steamID>')
def recommendations(steamID):
    return render_template("recommendations.html", **locals())

# deletes account and returns to the login page
@app.route('/deleteAccount/<steamID>')
def deleteAccount(steamID):
    removeAccountFromCSV(steamID)
    return redirect(url_for('index'))

if __name__ == "__main__":
	app.run(port="5000")