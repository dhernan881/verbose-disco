import requests
import copy

steamAPIKey = "99265BB0548A6F48052B8784D88B8A44"

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

# gets the user's in-game CS:GO stats
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

# get's the user's "favorite" map (i.e. one with the most rounds played)
# and their winrate on that map
# unfortunately the map is de_dust2 for pretty much everyone cuz it's so popular
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

# get's the user's last match KDR and ADR exclusively; used for progression
def getLastMatchKDRAndADR(steamID):
    steamLink = 'https://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v2/?appid=730&key='
    steamLink += steamAPIKey
    steamLink += "&steamid="
    steamLink += str(steamID)

    userSteamStats = requests.get(steamLink).json()
    lastMatchStats = dict()
    for elem in userSteamStats['playerstats']['stats']:
        if(elem['name'] == 'last_match_rounds'): lastMatchRounds = elem['value']
        elif(elem['name'] == 'last_match_damage'): lastMatchDamage = elem['value']
        elif(elem['name'] == 'last_match_kills'): lastMatchKills = elem['value']
        elif(elem['name'] == 'last_match_deaths'): lastMatchDeaths = elem['value']

    lastMatchStats['lastMatchADR'] = lastMatchDamage // lastMatchRounds
    lastMatchStats['lastMatchKDR'] = lastMatchKills / lastMatchDeaths
    lastMatchStats['lastMatchKDR'] = round(lastMatchStats['lastMatchKDR'], 2)

    return lastMatchStats

def getFriends(steamID):
    requestURL = 'https://api.steampowered.com/ISteamUser/GetFriendList/v1/?key='
    requestURL += steamAPIKey
    requestURL += '&steamid='
    requestURL += str(steamID)
    friends = requests.get(requestURL).json()
    return friends

def getFriendNicknames(steamID):
    friends = getFriends(steamID)
    friendSteamIDs = []
    friendsDict = dict()
    hundreds = len(friends['friendslist']['friends']) // 100
    
    for elem in friends['friendslist']['friends']:
        friendSteamIDs.append(elem['steamid'])

    requestURL = 'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key='
    requestURL += steamAPIKey
    requestURL += '&steamids='

    # the API can only handle 100 steamIDs at once
    friendsDestructive = copy.deepcopy(friendSteamIDs)
    while len(friendsDestructive) > 100:
        for i in range(100):
            requestURL += str(friendsDestructive[i])
            requestURL += ','

        friendRequest = requests.get(requestURL).json()
        for player in friendRequest['response']['players']:
            # map steamID to name
            # I can't think of an efficient way to do this. need to fix later
            friendsDict[player['personaname']] = player['steamid']

        # trim off friendsDestructive and reset requestURL for next pass
        friendsDestructive = friendsDestructive[100:]
        requestURL = 'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key='
        requestURL += steamAPIKey
        requestURL += '&steamids='
    for i in range(len(friendsDestructive)):
        requestURL += str(friendsDestructive[i])
        requestURL += ','
    friendRequest = requests.get(requestURL).json()
    for player in friendRequest['response']['players']:
        # map steamID to name
        # I can't think of an efficient way to do this. need to fix later
        friendsDict[player['personaname']] = player['steamid']
    
    return friendsDict

def getFriendSteamIDFromWord(yourSteamID, word):
    yourFriends = getFriendNicknames(yourSteamID)
    searchMatches = []
    for friend in yourFriends:
        if(word.lower() in friend.lower()):
            searchMatches.append({f'{friend}':yourFriends[friend]})
    if(len(searchMatches) == 0):
        return None
    elif(len(searchMatches) == 1):
        return list(searchMatches[0].values())[0]
    else:
        matches = []
        return searchMatches
        for person in searchMatches:
            matches.append(person.keys()[0])
        return matches

print(getFriendSteamIDFromWord(76561198111669661, 'Krach'))