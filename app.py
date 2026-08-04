import os
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for

from database.db import (
    create_user,
    get_user_by_email,
    init_db,
    seed_db,
    verify_user,
)

app = Flask(__name__)

# Signs the session cookie. The fallback keeps dev restarts from logging
# everyone out; a real deployment must set SECRET_KEY in the environment.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-not-for-production")

# Make sure the schema and dev data exist before any route runs.
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Access control                                                      #
# ------------------------------------------------------------------ #

def login_required(view):
    """Send anonymous visitors to the sign-in page instead of the view.

    wraps() keeps the wrapped function's name, which Flask uses as the
    endpoint — without it every decorated view would register as "wrapper"
    and the second one would collide.
    """
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapper


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        # Not stripped — leading/trailing spaces can be part of a real password.
        password = request.form.get("password", "")

        error = None
        if not name:
            error = "Please enter your name."
        elif not email:
            error = "Please enter your email address."
        elif "@" not in email:
            error = "Please enter a valid email address."
        elif not password.strip():
            error = "Please enter a password."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif get_user_by_email(email):
            error = "An account with that email already exists."

        if error is None:
            # The UNIQUE constraint is the real guard; create_user() returns
            # None if the check above lost a race with another signup.
            if create_user(name, email, password) is None:
                error = "An account with that email already exists."
            else:
                return redirect(url_for("login"))

        # Same page, form still filled in — never echo the password back.
        return render_template(
            "register.html", error=error, name=name, email=email
        )

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        # Normalised the same way register does, or an account stored
        # lowercased could never be matched.
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        error = None
        if not email:
            error = "Please enter your email address."
        elif not password.strip():
            error = "Please enter your password."
        else:
            # Deliberately no length or "@" check here — an existing account
            # may predate registration's rules (the seeded demo user's
            # password is six characters) and must still be able to sign in.
            user = verify_user(email, password)
            if user is None:
                # One message for both a wrong password and an unknown
                # address, so the response never confirms an email exists.
                error = "Incorrect email or password."
            else:
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                return redirect(url_for("profile"))

        # Same page, email still filled in — never echo the password back.
        return render_template("login.html", error=error, email=email)

    return render_template("login.html")


@app.route("/logout")
def logout():
    # clear() rather than popping single keys, so no stale session data
    # survives. Harmless when nobody is signed in.
    session.clear()
    return redirect(url_for("landing"))


# ------------------------------------------------------------------ #
# Placeholder profile data                                            #
# ------------------------------------------------------------------ #
# Hardcoded on purpose: this step builds the profile layout only, so the
# template can be validated before Step 5 replaces these three constants
# with real queries. Amounts are pre-formatted strings — the grouping a
# real total needs is a formatting concern, not part of the layout work.

PROFILE_USER = {
    "initials": "DU",
    "name": "Demo User",
    "email": "demo@spendly.com",
    "member_since": "01 August 2026",
}

PROFILE_STATS = [
    {"label": "Total spent", "value": "₹4,295.25"},
    {"label": "Transactions", "value": "8"},
    {"label": "Top category", "value": "Bills"},
]

# Mirrors the eight seeded expenses so the switch to real data in Step 5
# should not change what this page looks like. Newest first.
PROFILE_TRANSACTIONS = [
    {
        "date": "04 Aug 2026",
        "description": "Lunch with a friend",
        "category": "Food",
        "amount": "185.75",
    },
    {
        "date": "04 Aug 2026",
        # A real expense may have no description; the template shows a dash.
        "description": None,
        "category": "Other",
        "amount": "210.00",
    },
    {
        "date": "03 Aug 2026",
        "description": "Running shoes",
        "category": "Shopping",
        "amount": "1,250.00",
    },
    {
        "date": "03 Aug 2026",
        "description": "Streaming subscription",
        "category": "Entertainment",
        "amount": "299.00",
    },
    {
        "date": "02 Aug 2026",
        "description": "Pharmacy",
        "category": "Health",
        "amount": "450.00",
    },
    {
        "date": "02 Aug 2026",
        "description": "Metro card top-up",
        "category": "Transport",
        "amount": "80.00",
    },
    {
        "date": "01 Aug 2026",
        "description": "Electricity bill",
        "category": "Bills",
        "amount": "1,500.00",
    },
    {
        "date": "01 Aug 2026",
        "description": "Groceries",
        "category": "Food",
        "amount": "320.50",
    },
]

# Same eight expenses grouped by category, largest first. Totals add up to
# the "Total spent" stat above.
PROFILE_BREAKDOWN = [
    {"category": "Bills", "total": "1,500.00"},
    {"category": "Shopping", "total": "1,250.00"},
    {"category": "Food", "total": "506.25"},
    {"category": "Health", "total": "450.00"},
    {"category": "Entertainment", "total": "299.00"},
    {"category": "Other", "total": "210.00"},
    {"category": "Transport", "total": "80.00"},
]


@app.route("/profile")
@login_required
def profile():
    return render_template(
        "profile.html",
        user=PROFILE_USER,
        stats=PROFILE_STATS,
        transactions=PROFILE_TRANSACTIONS,
        breakdown=PROFILE_BREAKDOWN,
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
