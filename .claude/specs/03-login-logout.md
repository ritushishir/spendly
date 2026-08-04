# Spec: Login and Logout

## Overview
Turn `/login` from a render-only route into a working sign-in flow, and turn
`/logout` from a placeholder string into a real session teardown. Registration
(Step 2) can now create accounts, but nothing can *use* one — there is no
`app.secret_key`, no `session` anywhere in the app, and the navbar hardcodes
signed-out links. This step configures the session, verifies a submitted
password against the stored werkzeug hash, stores the signed-in user's identity
in the session cookie, and makes `base.html` render different navigation for
signed-in visitors. It is the hinge of the roadmap: every remaining feature —
profile, the expense list, add/edit/delete — is scoped to "the logged-in user",
and that phrase has no meaning until this step exists.

**Non-goal:** this step does not add a `@login_required` decorator or protect
`/profile` and `/expenses/*`. Those placeholders stay exactly as they are; the
decorator arrives in Step 4 alongside its first real consumer, so nothing
speculative is built here.

## Depends on
- **Step 1 — Database setup** (complete): `get_db()`, `init_db()`, `seed_db()`
  and the `users` table.
- **Step 2 — Registration** (complete): `get_user_by_email(email)` already
  exists in `database/db.py` and returns the full row including
  `password_hash` — this step reuses it rather than adding a second lookup.
  Real accounts exist to sign in with, including the seeded
  `demo@spendly.com` / `demo123`.

Nothing else.

## Routes
- `GET /login` — render the sign-in form (already implemented; the route
  decorator gains `methods=["GET", "POST"]`). If a session is already active,
  redirect to `/profile` instead of showing the form — **public**
- `POST /login` — verify email and password, set the session keys, then
  redirect to `/profile`; on failure re-render `login.html` with `error=` and
  the submitted email — **public**
- `GET /logout` — clear the session and redirect to `/` — **public**
  (deliberately not session-gated: logging out when not logged in is a
  harmless no-op, and gating it would need the Step 4 decorator)

No other new routes. `/logout` keeps its existing `GET`-only decorator so the
navbar link works as a plain anchor.

## Database changes
**No database changes.** The `users` table already has everything needed —
`email` (UNIQUE) to look the account up and `password_hash` to verify against.
Verified against `database/db.py`: the `SCHEMA` constant is unchanged by this
step, and no migration is required.

## Templates
- **Create:** none.
- **Modify:**
  - `templates/login.html`
    - Change `action="/login"` to `action="{{ url_for('login') }}"`, matching
      the `url_for('register')` already used further down the file and the
      change made to `register.html` in Step 2.
    - Repopulate the email field on a failed submit
      (`value="{{ email or '' }}"`). Never repopulate the password field.
    - The existing `{% if error %}<div class="auth-error">{{ error }}</div>{% endif %}`
      block is the only error channel — do not introduce flash messages.
  - `templates/base.html`
    - Make the `.nav-links` block conditional on `session.user_id`
      (Flask exposes `session` to every template with no extra work):
      - signed out — unchanged: "Sign in" and "Get started"
      - signed in — a greeting or `Profile` link plus a "Sign out" link to
        `url_for('logout')`
    - Make **"Sign out" the `.nav-cta`** element. The responsive rule at
      `static/css/style.css:528` hides `.nav-links a:not(.nav-cta)` on narrow
      screens, so any other choice makes signing out impossible on mobile.

No CSS work is needed: `.nav-links a`, `.nav-cta`, `.auth-error`,
`.form-group`, `.form-input` and `.btn-submit` are all already styled and are
reused as-is.

## Files to change
- `app.py` — set `app.secret_key`; add `methods=["GET", "POST"]` and the POST
  branch to `login`; implement `logout`; extend the flask imports with
  `session` (`request`, `redirect`, `url_for` are already imported from Step 2).
- `database/db.py` — add `verify_user(email, password)`.
- `templates/login.html` — `url_for` action, email repopulation.
- `templates/base.html` — conditional navbar.

## Files to create
- None.

## New dependencies
**No new dependencies.** `werkzeug.security.check_password_hash` ships with
Flask and is the counterpart of the `generate_password_hash` already imported
in `database/db.py`.

## Rules for implementation
- **No SQLAlchemy or ORMs** — stdlib `sqlite3` only.
- **Parameterised queries only** — `?` placeholders, never f-strings or `%`
  formatting in SQL.
- **Passwords hashed with werkzeug** — verification uses
  `check_password_hash(row["password_hash"], password)`. Never compare
  passwords with `==`, never re-hash the input and compare hashes, and never
  log or echo the plaintext.
- **Use CSS variables — never hardcode hex values.** Use the `:root` tokens
  (`--ink*`, `--paper*`, `--accent`, `--danger`, `--radius-*`).
- **All templates extend `base.html`.**
- All database access goes through `database/db.py`. No `sqlite3.connect` or
  `get_db()` calls in `app.py` — `grep -n "sqlite3\|get_db" app.py` must stay
  empty, as it has since Step 2.
- Close every connection (`try/finally`), matching the existing style in
  `db.py`.
- `verify_user(email, password)` belongs in `db.py`, not the route: it reuses
  `get_user_by_email()`, returns the user row on a correct password and `None`
  otherwise, and keeps every werkzeug call inside the one module that already
  imports werkzeug. `app.py` must not import `check_password_hash`.
- `app.secret_key` must not be a bare literal committed as a real secret. Read
  it from the environment with a clearly-labelled development fallback, e.g.
  `os.environ.get("SECRET_KEY", "dev-only-not-for-production")`, and note in a
  comment that a fixed fallback means sessions survive a restart in dev.
- Normalise the submitted email the same way registration does —
  `.strip().lower()` — or accounts created as `MixedCase@Example.COM` (stored
  lowercased) will never match. The password is not stripped.
- Validation, applied server-side regardless of the HTML attributes:
  - `email` and `password` are both required after `.strip()`
  - **do not** re-apply registration's 8-character minimum or the `@` check on
    login; an existing account may predate those rules (the seeded
    `demo123` is 6 characters and must still be able to sign in)
- **The failure message must not reveal whether the email exists.** A wrong
  password and an unknown address produce the same string, e.g.
  "Incorrect email or password." Do not branch the message on which half
  failed.
- Session keys: store `session["user_id"]` and `session["user_name"]` — the id
  for scoping later queries, the name so the navbar can greet without a
  database hit on every page. Store nothing sensitive; never put the password
  or the hash in the session.
- `logout` uses `session.clear()` (not a single `pop`) so no stale keys
  survive, then `return redirect(url_for("landing"))`.
- One error at a time in `.auth-error`, phrased for a person.
- On success: `return redirect(url_for("profile"))`. `/profile` is still the
  Step 4 placeholder string — that is expected, and redirecting there now means
  Step 4 needs no change to this route.
- On failure: `return render_template("login.html", error=..., email=...)` with
  HTTP 200 — same page, email still filled in.
- Leave every other placeholder route (`/profile`, `/expenses/*`) untouched,
  and leave the Step 2 `register` route untouched.
- `templates/landing.html` keeps its signed-out CTAs ("Start tracking free",
  "Sign in"). A logged-in visitor on `/` will still see them — a known cosmetic
  inconsistency, explicitly out of scope here.

## Definition of done
Run `python app.py` and visit `http://127.0.0.1:5001`:

- [ ] `GET /login` still renders the form exactly as before — no layout or
      styling regression.
- [ ] Signing in as the seeded user (`demo@spendly.com` / `demo123`) redirects
      to `/profile` and shows the Step 4 placeholder string.
- [ ] After signing in, the navbar shows the signed-in links (Profile / Sign
      out) on every page, and no longer shows "Sign in" / "Get started".
- [ ] "Sign out" is the `.nav-cta` element, so it is still visible when the
      window is narrowed past the `static/css/style.css:528` breakpoint.
- [ ] `GET /logout` clears the session, redirects to `/`, and the navbar is
      back to the signed-out links.
- [ ] After logging out, pressing the browser Back button and reloading does
      not restore the signed-in navbar.
- [ ] Visiting `/login` while already signed in redirects to `/profile` rather
      than rendering the form.
- [ ] A correct email with the wrong password is rejected with
      "Incorrect email or password." and the email field stays filled in.
- [ ] An email with no account produces the **identical** message — confirm the
      two responses are byte-identical apart from the echoed email:
      ```
      curl -s -X POST -d "email=demo@spendly.com&password=wrong" http://127.0.0.1:5001/login | grep auth-error
      curl -s -X POST -d "email=nobody@nowhere.com&password=wrong" http://127.0.0.1:5001/login | grep auth-error
      ```
- [ ] An empty email or empty password is rejected with a required-field
      message and no session is set.
- [ ] `DEMO@Spendly.COM` (different casing) signs in successfully, proving the
      email is normalised the same way registration normalises it.
- [ ] An account registered in Step 2 (e.g. via the `/register` form) can sign
      in with the password used at registration.
- [ ] The session cookie is actually set and drives access — verify with a
      cookie jar rather than trusting the redirect:
      ```
      curl -s -c jar.txt -X POST -d "email=demo@spendly.com&password=demo123" http://127.0.0.1:5001/login -o /dev/null -w '%{http_code} %{redirect_url}\n'
      curl -s -b jar.txt http://127.0.0.1:5001/ | grep -c "Sign out"     # 1
      curl -s http://127.0.0.1:5001/ | grep -c "Sign out"                # 0 — no cookie, signed-out nav
      ```
- [ ] The submitted password appears nowhere in any response body and nowhere
      in the terminal log.
- [ ] `grep -n "sqlite3\|get_db" app.py` still shows no direct database access.
- [ ] `grep -n "check_password_hash" app.py` is empty — verification lives in
      `database/db.py`.
- [ ] `app.secret_key` is read from the environment with a development
      fallback, not a hardcoded production secret.
- [ ] No flash messages were introduced; the error still renders inside
      `.auth-error`, and `static/css/style.css` has no new hex values.
