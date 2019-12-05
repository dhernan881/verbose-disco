# verbose-disco
GitHub repository for Dakota Hernandez's 112 Term Project

Welcome to CS:GO Stat's Manager!

This is a website designed to help people improve at playing CS:GO.
The site takes user stats, compares them to those of a professional
player, and offers personalized advice on how to improve. The user
can also see their progression over time and can compare stats with
their friends.

To Run:
* Run app.py
* Open a browser
* Go to localhost:5000 (if you want to use a differnt port, you can
specify that in app.py down at the very bottom)
* You will need a Steam account and have played CS:GO (Free to play!)
to see the main features. However, you can still access the
recommendations section and pages without logging in!

Required Libraries:
The full list is available in requirements.txt, but this is
    mainly for server deployment.
In addition to the core Python libraries, you will need:
* requests
* flask
* flask_openid
* urllib3
The following libraries should be core libraries. Just in case they
are not installed by default, you will also need:
* csv
* ast
