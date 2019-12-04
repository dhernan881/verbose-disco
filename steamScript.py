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

# gets win rate on a given map
def getSpecificMapWinRate(steamID, map):
    steamAPILink = 'https://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v2/?appid=730&key='
    steamAPILink += steamAPIKey
    steamAPILink += "&steamid="
    steamAPILink += str(steamID)
    userSteamStats = requests.get(steamAPILink).json()

    for elem in userSteamStats['playerstats']['stats']:
        if(elem['name'] == f'total_wins_map_{map}'):
            totalMapWins = elem['value']
        elif(elem['name'] == f'total_rounds_map_{map}'):
            totalMapRounds = elem['value']
            break
    
    winPercent = totalMapWins / totalMapRounds * 100
    winPercent = round(winPercent, 2)

    return winPercent

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
    
    # inefficient. can be streamlined later
    # searches through the API call for these in-game stats:
    # note it gets all the rounds/wins on every map as well
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
    # call getFavoriteMapAndWinRate to determine favorite map and win rate on it
    userStats['favoriteMap'],userStats['favoriteMapWinRate'] = \
        getFavoriteMapAndWinRate(mapsDict, winsDict)
    return userStats

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

# get's the user's last match KDR and ADR only; used for progression
# and the google chart
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

# gets the json containing all of the user's Steam friends
def getFriends(steamID):
    requestURL = 'https://api.steampowered.com/ISteamUser/GetFriendList/v1/?key='
    requestURL += steamAPIKey
    requestURL += '&steamid='
    requestURL += str(steamID)
    friends = requests.get(requestURL).json()
    return friends

# get the names of the user's friends. used to make searching more easy to use
def getFriendNicknames(steamID):
    friends = getFriends(steamID)
    friendSteamIDs = []
    friendsDict = dict()
    
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
            # I can't think of a better way to organize it. will update after
            friendsDict[player['personaname']] = player['steamid']

        # trim off friendsDestructive and reset requestURL for next pass
        friendsDestructive = friendsDestructive[100:]
        requestURL = 'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key='
        requestURL += steamAPIKey
        requestURL += '&steamids='
    # once the length is at most 100, get the rest of the friend steam IDs
    for i in range(len(friendsDestructive)):
        requestURL += str(friendsDestructive[i])
        requestURL += ','
    friendRequest = requests.get(requestURL).json()
    for player in friendRequest['response']['players']:
        friendsDict[player['personaname']] = player['steamid']
    
    return friendsDict

# get the friends steam id given a word (search term)
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
        # if more than one match, return a list of the matches
        matches = []
        for person in searchMatches:
            matches.append(list(person.keys())[0])
        return matches