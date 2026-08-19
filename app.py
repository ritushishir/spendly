import os
from datetime import datetime
from functools import wraps

from flask import Flask, redirect, render_template, request, session, url_for

from database.db import (
    create_user,
    get_category_totals_for_user,
    get_expenses_for_user,
    get_user_by_email,
    get_user_by_id,
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
# Profile display formatting                                          #
# ------------------------------------------------------------------ #
# The template prints these values as-is, so the shaping happens here and
# the stored rows stay raw: amounts are REAL, dates plain ISO strings.

def _initials(name):
    """First and last initial, e.g. "Demo User" → "DU".

    A single-word name gives one letter; a blank one gives a placeholder
    rather than an empty avatar.
    """
    parts = name.split()
    if not parts:
        return "?"
    letters = parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")
    return letters.upper()


def _rupees(amount):
    """Format an amount with thousands separators and two decimals."""
    return f"{amount:,.2f}"


def _display_date(iso, fmt="%d %b %Y"):
    """Reformat a stored date, or hand back the raw value if it can't parse.

    Only the leading date is read, so both "2026-08-04" (expenses.date) and
    "2026-08-04 09:15:22" (users.created_at) work.
    """
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime(fmt)
    except (TypeError, ValueError):
        return iso


def _parse_date_arg(value):
    """Validate one YYYY-MM-DD query parameter and hand it back unchanged.

    Returns None for a missing or blank parameter, which the queries read as an
    open-ended bound rather than as "today" or "the beginning of time".

    Raises ValueError on anything else. strptime is doing real work here, not
    just shape-checking: it rejects impossible dates like 2026-02-31, so a typo
    can never quietly widen the range instead of being reported.
    """
    if value is None or not value.strip():
        return None
    value = value.strip()
    datetime.strptime(value, "%Y-%m-%d")
    return value


def _range_label(start, end):
    """Describe the window currently applied, for display next to the figures.

    Every number on the profile page depends on the range, so the range is
    always named on screen — "All time" included.
    """
    if start and end:
        return f"{_display_date(start)} – {_display_date(end)}"
    if start:
        return f"From {_display_date(start)}"
    if end:
        return f"Up to {_display_date(end)}"
    return "All time"


@app.route("/profile")
@login_required
def profile():
    user = get_user_by_id(session["user_id"])
    if user is None:
        # The signed-in account no longer exists — drop the stale session
        # rather than rendering a page for a user we can't look up.
        session.clear()
        return redirect(url_for("login"))

    # Each bound is validated on its own, so one bad field doesn't throw away
    # the other's perfectly good value when the form is redisplayed.
    filter_error = None

    try:
        start = _parse_date_arg(request.args.get("start"))
    except ValueError:
        start = None
        filter_error = "The “From” date must be a real date in YYYY-MM-DD form."

    try:
        end = _parse_date_arg(request.args.get("end"))
    except ValueError:
        end = None
        filter_error = "The “To” date must be a real date in YYYY-MM-DD form."

    if start and end and start > end:
        # Safe as a string compare — both are zero-padded ISO by now.
        filter_error = "The “From” date can't be after the “To” date."

    # A rejected filter shows the unfiltered page plus the message, rather than
    # an error page or an arbitrary guess at what was meant. start/end stay as
    # parsed so the form can still redisplay what the user picked.
    query_start = None if filter_error else start
    query_end = None if filter_error else end

    expenses = get_expenses_for_user(user["id"], query_start, query_end)
    totals = get_category_totals_for_user(user["id"], query_start, query_end)

    return render_template(
        "profile.html",
        filter_error=filter_error,
        filters={
            # "" rather than None: these go straight into a value= attribute.
            "start": start or "",
            "end": end or "",
            # Drives the Clear link, and tells the panels which empty state to
            # show — with no filter applied, an empty result means the account
            # genuinely has no expenses, so no extra query is needed to know.
            "active": bool(query_start or query_end),
            "label": _range_label(query_start, query_end),
        },
        user={
            "initials": _initials(user["name"]),
            "name": user["name"],
            "email": user["email"],
            "member_since": _display_date(user["created_at"], "%d %B %Y"),
        },
        stats=[
            {
                "label": "Total spent",
                "value": "₹" + _rupees(sum(row["total"] for row in totals)),
            },
            {"label": "Transactions", "value": str(len(expenses))},
            {
                # totals is ordered by total DESC, so the first row is the
                # biggest. An account with no expenses has no top category.
                "label": "Top category",
                "value": totals[0]["category"] if totals else "—",
            },
        ],
        transactions=[
            {
                "date": _display_date(expense["date"]),
                "description": expense["description"],
                "category": expense["category"],
                "amount": _rupees(expense["amount"]),
            }
            for expense in expenses
        ],
        breakdown=[
            {"category": row["category"], "total": _rupees(row["total"])}
            for row in totals
        ],
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
