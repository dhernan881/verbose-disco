import hltvScript
# reminder it only searches for players who have at least 100 recorded matches
import requests
from flask import Flask, render_template, redirect, request, url_for, g, session
from flask.ext.openid import OpenID

oid = OpenID(app, './OpenID-Store', safe_roots=[])

app = Flask(__name__)

@app.before_request
def lookup_current_user():
    g.user = None
    if 'openid' in session:
        openid = session['open']
        g.user = User.query.filter_by(openid=openid).first()

@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler


@app.route('/')
def index():
    stats = hltvScript.getPlayerStatsFromWord("pashabiceps")
    return render_template("index.html", stats=stats)

if __name__ == "__main__":
	app.run(port="5000")