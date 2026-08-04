# Spec: Registration

## Overview
Turn `/register` from a render-only route into a working sign-up flow. The page and
form already exist and already POST to `/register`; what is missing is the server
side — validating the submitted name, email and password, hashing the password with
werkzeug, and inserting a row into the `users` table via `database/db.py`. This is
the first step that writes user-supplied data to the database, so it is the point
where input validation and the UNIQUE-email constraint stop being theoretical. It
comes directly after the data layer (Step 1) because every remaining feature —
login, profile, expenses — needs real accounts to exist before it can be built.

**Non-goal:** this step does not log the user in. Sessions and `app.secret_key` are
deliberately left for the login step; a successful registration redirects to
`/login` so the user signs in explicitly.

## Depends on
- **Step 1 — Database setup** (complete): `get_db()`, `init_db()`, `seed_db()` and
  the `users` table are already implemented in `database/db.py`.

Nothing else. Sessions, login and logout are not required for this step.

## Routes
- `GET /register` — render the sign-up form (already implemented; the route
  decorator gains `methods=["GET", "POST"]`) — **public**
- `POST /register` — validate input, hash the password, insert the user, then
  redirect to `/login`; on failure re-render `register.html` with `error=` and the
  previously submitted values — **public**

No other new routes.

## Database changes
**No database changes.** The existing `users` table in `database/db.py` already has
everything this step needs:

| Column | Type | Constraints |
| --- | --- | --- |
| `id` | INTEGER | primary key, autoincrement |
| `name` | TEXT | not null |
| `email` | TEXT | not null, **UNIQUE** |
| `password_hash` | TEXT | not null |
| `created_at` | TEXT | not null, default `datetime('now')` |

The `UNIQUE` constraint on `email` is the backstop for duplicate accounts and must
be handled (`sqlite3.IntegrityError`), not just pre-checked with a SELECT.

## Templates
- **Create:** none.
- **Modify:** `templates/register.html`
  - Change `action="/register"` to `action="{{ url_for('register') }}"` to match the
    `url_for` usage already present elsewhere in the file.
  - Repopulate `name` and `email` on a failed submit
    (`value="{{ name or '' }}"`, `value="{{ email or '' }}"`) so the user does not
    retype them. Never repopulate the password field.
  - Add `minlength="8"` to the password input so the browser hint matches the
    server-side rule.

The existing `{% if error %}<div class="auth-error">{{ error }}</div>{% endif %}`
block is the only error channel — do not introduce flash messages.

No CSS work is needed: `.auth-error`, `.form-group`, `.form-input`, `.btn-submit`
and `.auth-switch` are all already styled in `static/css/style.css`.

## Files to change
- `app.py` — add `methods=["GET", "POST"]` to the `register` route, add the POST
  branch, extend the imports (`request`, `redirect`, `url_for`).
- `templates/register.html` — `url_for` action, value repopulation, `minlength`.
- `database/db.py` — add a `create_user(name, email, password)` helper and an
  `email_exists(email)` (or `get_user_by_email(email)`) helper, so `app.py` never
  opens its own connection.

## Files to create
- None.

## New dependencies
**No new dependencies.** `werkzeug` ships with Flask and
`werkzeug.security.generate_password_hash` is already imported in `database/db.py`.

## Rules for implementation
- **No SQLAlchemy or ORMs** — stdlib `sqlite3` only.
- **Parameterised queries only** — `?` placeholders, never f-strings or `%`
  formatting in SQL.
- **Passwords hashed with werkzeug** — `generate_password_hash`. The plaintext
  password must never be written to the database, logged, or echoed back into the
  template.
- **Use CSS variables — never hardcode hex values.** Use the `:root` tokens
  (`--ink*`, `--paper*`, `--accent`, `--danger`, `--radius-*`).
- **All templates extend `base.html`.**
- All database access goes through `database/db.py`. No `sqlite3.connect` or
  `get_db()` calls in `app.py`.
- Close every connection (`try/finally`), matching the existing style in `db.py`.
- Validation rules, applied server-side regardless of the HTML attributes:
  - `name`, `email`, `password` are all required after `.strip()`
  - password must be at least 8 characters
  - email must contain an `@`
  - store email lowercased and stripped; store name stripped
- Duplicate email must be handled in both places: a friendly check before the
  insert *and* a caught `sqlite3.IntegrityError` around it. The user-facing message
  must not confirm whether an email is registered any more specifically than
  "An account with that email already exists."
- One error at a time in `.auth-error`, phrased for a person, e.g.
  "Password must be at least 8 characters."
- On success: `return redirect(url_for("login"))`. Do not set any session keys and
  do not touch `app.secret_key` in this step.
- On failure: `return render_template("register.html", error=..., name=..., email=...)`
  with HTTP 200 — same page, form still filled in.
- Leave every other placeholder route (`/logout`, `/profile`, `/expenses/*`)
  untouched.

## Definition of done
Run `python app.py` and visit `http://127.0.0.1:5001`:

- [ ] `GET /register` still renders the form exactly as before — no layout or
      styling regression.
- [ ] Submitting a valid new name / email / password redirects to `/login`.
- [ ] That account now exists in SQLite:
      `sqlite3 expense_tracker.db "SELECT id, name, email, created_at FROM users;"`
      shows the new row with a populated `created_at`.
- [ ] The stored `password_hash` is a werkzeug hash (starts with `scrypt:` or
      `pbkdf2:`) and the plaintext password appears nowhere in the table.
- [ ] Registering the *same* email again re-renders `/register` with
      "An account with that email already exists." and does **not** create a second
      row (`SELECT COUNT(*)` for that email stays at 1).
- [ ] `demo@spendly.com` (the seeded user) is likewise rejected as a duplicate.
- [ ] A 7-character password is rejected with a length message and no row is
      inserted.
- [ ] An email with no `@` is rejected with an email message and no row is inserted.
- [ ] Whitespace-only `name` (e.g. `"   "`) is rejected even though the browser's
      `required` attribute allows it — verifiable with
      `curl -X POST -d "name=   &email=a@b.com&password=abcdefgh" http://127.0.0.1:5001/register`.
- [ ] `MixedCase@Example.COM` is stored as `mixedcase@example.com`, and a second
      attempt with different casing is rejected as a duplicate.
- [ ] After a failed submit, the name and email fields are still filled in and the
      password field is empty.
- [ ] The error appears inside `.auth-error` (no flash messages introduced) and uses
      the existing warm-paper / deep-green styling with no new hex values in
      `style.css`.
- [ ] `grep -n "sqlite3\|get_db" app.py` shows no direct database access in `app.py`.
- [ ] Restarting the app does not duplicate or lose the registered account.
