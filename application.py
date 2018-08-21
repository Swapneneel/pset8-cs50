import os
import re
from flask import Flask, jsonify, render_template, request

from cs50 import SQL
from helpers import lookup

# Configure application
app = Flask(__name__)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///mashup.db")

# Ensure that the API_KEY is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    """Render map"""
    # hold the API_KEY in the Python env
    return render_template("index.html", API_KEY=os.getenv("API_KEY"))


@app.route("/articles")
def articles():
    """Look up articles for geo"""

    # TODO
    geo_loc = request.args.get("geo")
    if not geo_loc:
        raise RuntimeError("Geo not found.")

    data = lookup(geo_loc)  # calling the lookup to fetch news

    # Not letting to return more than 5 news for one place
    rn = len(data)
    if rn > 5:
        return jsonify([data[i] for i in range(5)])
    else:
        return jsonify(data)


@app.route("/search")
def search():
    """Search for places that match query"""

    # TODO
    try:
        # the value of this form will be always text
        q = request.args.get("q")

        # Sorting the value of q, desiding the query type
        # if not (' ' in q) or not (',' in q):
        #  query for top 10 places that match
        places = db.execute("SELECT * FROM places WHERE postal_code LIKE :q OR place_name LIKE :q \
                            OR admin_name1 LIKE :q OR admin_code1 LIKE :q LIMIT 10", q=q + "%")
        # country_code is not searched here
        """
        else:
            l = [i.strip() for i in q.split(',')]
            c = len(l)
            if c is 1:
                places = db.execute("SELECT * FROM places WHERE postal_code LIKE :q OR place_name LIKE :q \
                                OR admin_name1 LIKE :q OR admin_code1 LIKE :q OR country_code LIKE :q \
                                LIMIT 10", q=l[0]+"%")
            elif c is 2:
                places = db.execute("SELECT * FROM places WHERE (place_name LIKE :q_1 AND (admin_name1 LIKE :q_2 OR postal_code LIKE :q_2)) AND \
                (admin_name1 LIKE :q_1 AND (place_name LIKE :q_2 OR postal_code LIKE :q_2)) AND (postal_code LIKE :q_1 AND \
                (place_name LIKE :q_2 OR admin_code1 LIKE :q_2))", q_1=l[0]+"%", q_2=l[1]+"%")
            elif c is 3:
                places = db.execute("SELCET * FROM places WHERE (postal_code LIKE :q_1 OR admin_name1 LIKE :q_1 OR place_name LIKE :q_1) \
                AND (postal_code LIKE :q_2 OR admin_name1 LIKE :q_2 OR place_name LIKE :q_2) AND (postal_code LIKE :q_3 OR admin_name1 \
                LIKE :q_3 OR place_name LIKE :q_3) LIMIT 10", q_1=l[0]+"%", q_2=l[1]+"%", q_3=l[2]+"%")
        """
    except AttributeError:
        return "Nothing"

    return jsonify([
        {
            "accuracy": place["accuracy"],
            "admin_code1": place["admin_code1"],
            "admin_code2": place["admin_code2"],
            "admin_code3": place["admin_code3"],
            "admin_name1": place["admin_name1"],
            "admin_name2": place["admin_name2"],
            "admin_name3": place["admin_name3"],
            "country_code": place["country_code"],
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "place_name": place["place_name"],
            "postal_code": place["postal_code"]
        } for place in places
    ])


@app.route("/update")
def update():
    """Find up to 10 places within view"""

    # Ensure parameters are present
    if not request.args.get("sw"):
        raise RuntimeError("missing sw")
    if not request.args.get("ne"):
        raise RuntimeError("missing ne")

    # Ensure parameters are in lat,lng format
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("sw")):
        raise RuntimeError("invalid sw")
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("ne")):
        raise RuntimeError("invalid ne")

    # Explode southwest corner into two variables
    sw_lat, sw_lng = map(float, request.args.get("sw").split(","))

    # Explode northeast corner into two variables
    ne_lat, ne_lng = map(float, request.args.get("ne").split(","))

    # Find 10 cities within view, pseudorandomly chosen if more within view
    if sw_lng <= ne_lng:

        # Doesn't cross the antimeridian
        rows = db.execute("""SELECT * FROM places
                          WHERE :sw_lat <= latitude AND latitude <= :ne_lat AND (:sw_lng <= longitude AND longitude <= :ne_lng)
                          GROUP BY country_code, place_name, admin_code1
                          ORDER BY RANDOM()
                          LIMIT 10""",
                          sw_lat=sw_lat, ne_lat=ne_lat, sw_lng=sw_lng, ne_lng=ne_lng)

    else:

        # Crosses the antimeridian
        rows = db.execute("""SELECT * FROM places
                          WHERE :sw_lat <= latitude AND latitude <= :ne_lat AND (:sw_lng <= longitude OR longitude <= :ne_lng)
                          GROUP BY country_code, place_name, admin_code1
                          ORDER BY RANDOM()
                          LIMIT 10""",
                          sw_lat=sw_lat, ne_lat=ne_lat, sw_lng=sw_lng, ne_lng=ne_lng)

    # Output places as JSON
    return jsonify(rows)
