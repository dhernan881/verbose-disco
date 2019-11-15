import hltvScript
# reminder it only searches for players who have at least 100 recorded matches
import requests
from flask import Flask, render_template, redirect, request, url_for, g, session
from flask_openid import OpenID
from urllib.parse import urlencode, quote


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

@app.route('/profile/<steamID>')
def profile(steamID):
    accountName, accountProfilePicture = getUserInfo(steamID)
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

@app.route('/profile/<steamID>', methods=["POST"])
def profileWithSearch(steamID):
    accountName, accountProfilePicture = getUserInfo(steamID)
    searchResults = hltvScript.getPlayerStatsFromWord(request.form["search"])
    if(isinstance(searchResults, str)):
        return render_template("profile.html", **locals())
    searchName = searchResults['nickname']
    searchRating = searchResults['rating']
    return render_template("profile.html", **locals())

# tomorrow add team formation, self stats, saving in csv?

if __name__ == "__main__":
	app.run(port="5000")