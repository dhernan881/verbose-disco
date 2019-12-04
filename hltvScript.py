import requests

# this file is used for getting data from hltv.org

def getProfileLinkSuffixes():
    # makes an hltv request to the player stats page
    # changed minimum maps required from 0 to 100 to speed things up quite a bit
    request = requests.get('https://www.hltv.org/stats/players?minMapCount=100')
    pageLines = request.text.splitlines()

    i = 0
    while i < len(pageLines):
        # removes any line that doesn't have a player name in it
        if('''<td class="playerCol ">''' not in pageLines[i]):
            pageLines.pop(i)
        else:
            i += 1

    # gets the link references
    for i in range(len(pageLines)):
        line = pageLines[i]
        hIndex = line.find("href")
        i0 = line.find('"', hIndex+1)
        i1 = line.find('"', i0+1)
        line = line[i0+1:i1]
        pageLines[i] = line
    return set(pageLines)

# gets the full link to a player profile given their name
def getFullLinkFromPlayerName(name):
    hltvLink = 'https://www.hltv.org'
    lines = []
    for line in getProfileLinkSuffixes():
        lineWithSpaces = line.replace("%20", " ")
        if name.lower() in lineWithSpaces.lower():
            lines.append(hltvLink + line)
    if(len(lines) == 0):
        return None
    elif(len(lines) == 1):
        return lines[0]
    else:
        return lines

# summaryStatBreakdownDataValue is for values contained in the upper part
# of the page next to his profile pic; the values are:
# 
# Rating (2.0 for some, 1.0 for others?), DPR, KAST %, Impact (?), ADR, KPR
# 
# The stats are in 2 summaryStatBreakdownRow's of 3 stats
# both of which are contained in the summaryBreakdownContainer that also has
# the profile pic and other small info at the top upper part of the page
# 
# Futhermore, the other stats contained on this page are located inside two
# "col stats-rows standard-box" objects. the first one has:
# 
# Total Kills, HS %, Total Deaths, K/D Ratio, ADR, Grenade ADR, Maps Played
# 
# The second one has:
# 
# Rounds Played, KPR, APR, DPR, Saved by Teammates / Round (i.e. was traded),
# Saved Teammates / Round (i.e. traded), Rating 2.0

# get's the player's stats given a link to their page
def getPlayerStatsFromLink(link):
    playerRequest = requests.get(link)
    profilePageLines = playerRequest.text.splitlines()
    # key words to search for that have lines with stats on them
    # see above for descriptions
    keyTerms = ["summaryStatBreakdownDataValue", "text-ellipsis", '"stats-row"',
    '"SummaryTeamname"']
    # isolate the important lines (i.e. lines with a key term)
    importantLines = []
    for line in profilePageLines:
        for term in keyTerms:
            if(term in line):
                importantLines.append(line)
                break
    # this line and all lines after it are all junk 
    # but still come up in importantLines: 
    uselessLine = '                        <div class="text-ellipsis">Maps in filter</div>'
    uselessIndex = importantLines.index(uselessLine)
    importantLines = importantLines[:uselessIndex]

    # The big part: getting the individual stats and putting them in a dict:

    playerStats = dict()

    i0 = importantLines[0].index(">")
    i1 = importantLines[0][i0:].index("<")
    playerStats["nickname"] = importantLines[0][i0 + 1 : i0 + i1]

    i0 = importantLines[1].index("alt=") + 5
    i1 = importantLines[1][i0:].index('"')
    playerStats["country"] = importantLines[1][i0 : i0 + i1]

    i0 = importantLines[2].index(">")
    i1 = importantLines[2][i0:].index("<")
    playerStats["name"] = importantLines[2][i0 + 1: i0 + i1]

    if("No team" in importantLines[3]):
        playerStats["team"] = "No team"
    else:
        i0 = importantLines[3].index("teams/") + 6
        i0 = importantLines[3][i0:].index("/") + 1 + i0
        i1 = importantLines[3][i0:].index('"')
        playerStats["team"] = importantLines[3][i0 : i0 + i1]

    i0 = importantLines[4].index(">")
    i1 = importantLines[4][i0:].index("<")
    playerStats["rating"] = float(importantLines[4][i0 + 1: i0 + i1])

    i0 = importantLines[5].index(">")
    i1 = importantLines[5][i0:].index("<")
    playerStats["averageDeathsPerRound"] = float(importantLines[5][i0 + 1: i0 + i1])

    i0 = importantLines[6].index(">")
    i1 = importantLines[6][i0:].index("<") - 1
    playerStats["percentKAST"] = float(importantLines[6][i0 + 1: i0 + i1])

    i0 = importantLines[7].index(">")
    i1 = importantLines[7][i0:].index("<")
    playerStats["impact"] = float(importantLines[7][i0 + 1: i0 + i1])
    # "Measures the impact made from multikills, opening kills, and clutches"

    i0 = importantLines[8].index(">")
    i1 = importantLines[8][i0:].index("<")
    playerStats["averageDamagePerRound"] = float(importantLines[8][i0 + 1: i0 + i1])

    i0 = importantLines[9].index(">")
    i1 = importantLines[9][i0:].index(("<"))
    playerStats["averageKillsPerRound"] = float(importantLines[9][i0 + 1: i0 + i1])

    i0 = importantLines[10].index("</span>") + 13
    i1 = importantLines[10][i0:].index("<")
    playerStats["totalKills"] = int(importantLines[10][i0: i0 + i1])

    i0 = importantLines[11].index("</span>") + 13
    i1 = importantLines[11][i0:].index("<") - 1
    playerStats["percentHeadshot"] = float(importantLines[11][i0: i0 + i1])

    i0 = importantLines[12].index("</span>") + 13
    i1 = importantLines[12][i0:].index("<")
    playerStats["totalDeaths"] = int(importantLines[12][i0: i0 + i1])

    i0 = importantLines[13].index("</span>") + 13
    i1 = importantLines[13][i0:].index("<")
    playerStats["killDeathRatio"] = float(importantLines[13][i0: i0 + i1])

    # skip importantLines[14] because it's ADR again

    i0 = importantLines[15].index("</span>") + 13
    i1 = importantLines[15][i0:].index("<")
    playerStats["averageGrenadeDamagePerRound"] = \
        float(importantLines[15][i0: i0 + i1])

    i0 = importantLines[16].index("</span>") + 13
    i1 = importantLines[16][i0:].index("<")
    playerStats["mapsPlayed"] = int(importantLines[16][i0: i0 + i1])

    i0 = importantLines[17].index("</span>") + 13
    i1 = importantLines[17][i0:].index("<")
    playerStats["roundsPlayed"] = int(importantLines[17][i0: i0 + i1])

    # skip importantLines[18] becaues it's KPR again

    i0 = importantLines[19].index("</span>") + 13
    i1 = importantLines[19][i0:].index("<")
    playerStats["averageAssistsPerRound"] = float(importantLines[19][i0: i0 + i1])

    # skip importantLines[20] because it's DPR again

    # skip importantLines[21] because it's saved by teammates / round (irrelevant?)

    # skip importantLines[22] because it's saved teammates / round (irrelevant?)

    # skip importantLines[23] because it's Rating again

    # Done!
    playerStats['winPercent'], playerStats['lastMatchKillDeathRatio'] = \
        getMatchStatsFromLink(link)
    return playerStats

# gets the players match stats (win rate, last match K/D) given a link to
# their profile page. The match stats are stored on a different page
def getMatchStatsFromLink(link):
    i0 = link.index("/players") + 9
    link = link[:i0] + "matches/" + link[i0:]
    matchPageLines = requests.get(link)
    matchPageLines = matchPageLines.text.splitlines()
    importantLines = []
    for i in range(len(matchPageLines)):
        if('<div class="value">' in matchPageLines[i]):
            importantLines.append(matchPageLines[i].strip())
        elif('<td class="statsMapPlayed">' in matchPageLines[i]):
            importantLines.append(matchPageLines[i + 1].strip())
            break
    i0 = importantLines[1].index(">") + 1
    i1 = importantLines[1].index("/") - 2
    winPercent = float(importantLines[1][i0:i1])

    i0 = importantLines[-1].index(">") + 1
    i1 = importantLines[-1].index("/") - 1
    killDeathString = importantLines[-1][i0:i1]

    i = killDeathString.index("-") - 1
    lastMatchKills = int(killDeathString[:i])
    lastMatchDeaths = int(killDeathString[i + 2:])
    lastMatchKillDeathRatio = lastMatchKills / lastMatchDeaths
    lastMatchKillDeathRatio = round(lastMatchKillDeathRatio, 2)

    return winPercent, lastMatchKillDeathRatio

# now let's put it all into one method
# get a player's stats given a search term
def getPlayerStatsFromWord(word):
    link = getFullLinkFromPlayerName(word)
    if(link == None):
        return None
    if(isinstance(link, list)):
        msg = "Did you mean:"
        for elem in link:
            playerName = elem[elem.index("players") + 8:]
            playerName = playerName[playerName.index("/") + 1:]
            playerName = playerName.replace("%20", " ")
            msg += (" " + playerName + ",")
        msg = msg[:-1]
        msg += "?"
        return msg
    return getPlayerStatsFromLink(link)

# gets the player's win percent on the given map name and search term
def getFavoriteMapWinPercentFromWord(word, map):
    # same as normal map stats method but specific to one map
    link = getFullLinkFromPlayerName(word)
    i0 = link.index("/players") + 9
    link = link[:i0] + "matches/" + link[i0:]
    link = link + "?maps=" + map

    matchPageLines = requests.get(link)
    matchPageLines = matchPageLines.text.splitlines()
    importantLines = []

    for i in range(len(matchPageLines)):
        if('<div class="value">' in matchPageLines[i]):
            importantLines.append(matchPageLines[i].strip())
        elif('<td class="statsMapPlayed">' in matchPageLines[i]):
            importantLines.append(matchPageLines[i + 1].strip())
            break

    i0 = importantLines[1].index(">") + 1
    i1 = importantLines[1].index("/") - 2
    winPercent = float(importantLines[1][i0:i1])
    return winPercent