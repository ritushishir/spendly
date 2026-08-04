# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Spendly — a personal expense tracker in Flask + SQLite (stdlib `sqlite3`, no ORM). Python 3.11+.

**This is a teaching scaffold, not a finished app.** The landing/register/login pages are built out; everything else is a deliberate placeholder that a student implements step by step. When asked to work here, respect that framing: implement the specific step requested rather than filling in all the stubs at once.

## Commands

```bash 
source venv/bin/activate          # venv/ is committed-adjacent but gitignored
pip install -r requirements.txt

python app.py                     # dev server, debug mode, http://127.0.0.1:5001
pytest                            # no tests exist yet; pytest + pytest-flask are installed
pytest path/to/test_x.py::test_name   # single test
```

Note the non-default port **5001** (hardcoded in `app.py`), not 5000.

## Architecture

Single-module Flask app — all routes live in `app.py`; there are no blueprints. `database/db.py` is the only intended data-access layer.

`database/db.py` is currently an empty stub documenting the three functions it must provide (Step 1):
- `get_db()` — SQLite connection with `row_factory` set and foreign keys enabled
- `init_db()` — `CREATE TABLE IF NOT EXISTS` for all tables
- `seed_db()` — sample dev data

The DB file is `expense_tracker.db` at the repo root (gitignored). Every other unimplemented route depends on this file, so it is the first thing to build.

### Route status

Implemented: `GET /`, `GET /register`, `GET /login` (templates render; **no POST handlers exist yet** — `register.html` and `login.html` already post to `/register` and `/login`, so adding `methods=["GET", "POST"]` is part of the auth steps).

Placeholders returning plain strings: `/logout` (Step 3), `/profile` (Step 4), `/expenses/add` (Step 7), `/expenses/<int:id>/edit` (Step 8), `/expenses/<int:id>/delete` (Step 9).

Sessions are not configured — `app.secret_key` must be set before any login/session work.

### Templates & styling

Jinja templates extend `base.html`, which defines blocks `title`, `head`, `content`, `scripts`, plus the shared navbar and footer. The navbar currently hardcodes signed-out links (Sign in / Get started); it needs conditional rendering once sessions exist.

`static/css/style.css` is hand-written with CSS custom properties defined in `:root` (`--ink*`, `--paper*`, `--accent`, `--danger`, `--font-display`/`--font-body`, `--radius-*`). Use these tokens rather than literal colors or fonts — the design is a warm-paper / deep-green editorial look, and new UI should match it. No build step, no CSS framework.

Auth templates render a `{{ error }}` string into `.auth-error` when present — follow that pattern (pass `error=` to `render_template`) rather than introducing flash messages, unless asked.

`static/js/main.js` is intentionally empty.

Amounts are displayed in Indian rupees (₹).

## Housekeeping

`file.txt` and `test.md` in the repo root are stray leftovers (an empty file and a pasted terminal transcript), not project files. Don't treat them as source or reference material.