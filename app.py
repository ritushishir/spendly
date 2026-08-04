import os

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
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    return "Profile page — coming in Step 4"


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
