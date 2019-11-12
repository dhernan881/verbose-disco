import hltvScript
import requests
from flask import Flask, render_template, redirect, request, url_for
# reminder it only searches for players who have at least 100 recorded matches

app = Flask(__name__)

@app.route('/')
def index():
    stats = hltvScript.getPlayerStatsFromWord("pashabiceps")
    return render_template("index.html", stats=stats)

if __name__ == "__main__":
	app.run(port="5000")