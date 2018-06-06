import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Ensure environment variable is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    
    user = session.get("user_id")
    shares = db.execute("SELECT symbol, SUM(share) AS shares FROM transactions WHERE userId = :userid GROUP BY symbol", userid = user)
    cash = db.execute("SELECT cash FROM users WHERE id = :userid", userid = user)
    cashReal = usd(cash[0]["cash"])

    # print(len(shares))
    # print(shares)

    return render_template("home.html", shares = shares, cash = cashReal, cashNumber = cash[0]["cash"])

    # return apology("TODO")


@app.route("/_quote_symbol", methods=["GET"])
@login_required
def quote_api():
    """API_GET_STOCK_QUOTE"""

    symbol = request.args.get('symbol')
    quoteResult = lookup(symbol)

    if quoteResult is None:
            return apology("symbol unavailble", 403)
    
    quotePrice = usd(quoteResult['price'])

    return jsonify(realPrice=quotePrice, number=quoteResult['price'], symbol=symbol)

    # return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        
        # Ensure buySymbol was submitted
        if not request.form.get("buySymbol"):
            return apology("must provide symbol", 403)

        # Ensure shares was submitted
        elif not request.form.get("shares") or not request.form.get("shares").isdigit():
            return apology("must provide shares", 403)
        
        # Perform the query
        buySymbol = request.form.get("buySymbol")
        shares = request.form.get("shares")
        quoteResult = lookup(buySymbol)

        if quoteResult is None:
            return apology("symbol unavailble", 403)
        
        quotePrice = usd(quoteResult['price'])
        buyPrice = quoteResult['price']

        cashNeed = float(buyPrice) * float(shares)

        user = session.get("user_id")
        cash = db.execute("SELECT cash FROM users WHERE id = :userid", userid = user)
        cashYouHave = cash[0]["cash"]

        if cashYouHave < cashNeed:
            return apology("insufficient cash", 403)
        
        cashRemain = cashYouHave - cashNeed

        rows = db.execute("INSERT INTO transactions (userId, symbol, share, price, remain, bought) VALUES (:user, :buySymbol, :shares, :quotePrice, :cashRemain, 1)", user=user, buySymbol = buySymbol, shares = shares, quotePrice = buyPrice, cashRemain = cashRemain)
        rows = db.execute("UPDATE users SET cash = :cashRemain WHERE id = :user", user=user,cashRemain = cashRemain)

        flash(f"You've just got {shares} shares of {buySymbol}!")

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("buy.html")

    # return apology("TODO")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    user = session.get("user_id")
    shares = db.execute("SELECT symbol, share, price, remain, datetime(timestamp, 'localtime') AS timestamp FROM transactions WHERE userId = :userid", userid = user)
    newShares = []

    for share in shares:
        share["price"] = usd(share["price"])
        share["remain"] = usd(share["remain"])
        newShares.append(share)

    # print(len(shares))
    # print(shares)

    return render_template("history.html", shares = newShares)

    # return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        flash("Login Success!")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        
        # Ensure symbol was submitted
        if not request.form.get("quoteSymbol"):
            return apology("must provide symbol", 403)
        
        # Perform the query
        quoteSymbol = request.form.get("quoteSymbol")
        quoteResult = lookup(quoteSymbol)

        if quoteResult is None:
            return apology("symbol unavailble", 403)
        
        quotePrice = usd(quoteResult['price'])

        # Show results
        return render_template("quote.html", quoted = True, symbol = quoteSymbol, price = quotePrice)
    
    else:
        return render_template("quote.html")
    # return apology("TODO")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        
        if len(rows) != 0:
            return apology("User Exists!", 403)
        
        pwd_hash = generate_password_hash(request.form.get("password"))
        rows = db.execute("INSERT INTO users (username, hash) VALUES (:username, :passhash)", username=request.form.get("username"), passhash = pwd_hash)

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        flash("Registed Success!")

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("login.html", reg = 'Reg')

    # return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":
        
        # Ensure sellSymbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)

        # Ensure shares was submitted
        elif not request.form.get("shares") or not request.form.get("shares").isdigit():
            return apology("must provide shares", 403)
        
        # Perform the query
        sellSymbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        sharesNegative = 0 - shares

        # Check if you have enough shares
        user = session.get("user_id")
        shareAvailable = db.execute("SELECT SUM(share) AS shares FROM transactions WHERE userId = :userid AND symbol = :sellSymbol GROUP BY symbol", userid = user, sellSymbol = sellSymbol)
        shareAvailable = shareAvailable[0]["shares"]
        if shareAvailable < shares:
            return apology("insufficient shares", 403)
        
        quoteResult = lookup(sellSymbol)
        if quoteResult is None:
            return apology("symbol unavailble", 403)

        quotePrice = usd(quoteResult['price'])
        sellPrice = quoteResult['price']

        cashObtained = float(sellPrice) * float(shares)
        cash = db.execute("SELECT cash FROM users WHERE id = :userid", userid = user)
        cashYouHave = cash[0]["cash"]

        cashRemain = cashYouHave + cashObtained

        rows = db.execute("INSERT INTO transactions (userId, symbol, share, price, remain, bought) VALUES (:user, :sellSymbol, :shares, :quotePrice, :cashRemain, 1)", user=user, sellSymbol = sellSymbol, shares = sharesNegative, quotePrice = sellPrice, cashRemain = cashRemain)
        rows = db.execute("UPDATE users SET cash = :cashRemain WHERE id = :user", user=user,cashRemain = cashRemain)

        flash(f"You've just sold {shares} shares of {sellSymbol} for {usd(cashObtained)}!")

        # Redirect user to home page
        return redirect("/")

    else:

        user = session.get("user_id")
        shares = db.execute("SELECT symbol, SUM(share) AS shares FROM transactions WHERE userId = :userid GROUP BY symbol", userid = user)
        return render_template("sell.html", shares=shares)

    # return apology("TODO")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

app.run(debug=True)