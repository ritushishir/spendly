# Spendly

A personal expense tracker built with Flask and SQLite.

This repository is a teaching scaffold: the landing, register, and login pages are
built out, while the remaining routes are placeholders to be implemented step by step.

## Requirements

- Python 3.11+

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the app

```bash
python app.py
```

The app starts in debug mode at http://127.0.0.1:5001.

## Running tests

```bash
pytest
```

## Project structure

```
app.py              Flask application and routes
database/
  db.py             Database connection, schema, and seed helpers
static/
  css/style.css     Styles
  js/main.js        Client-side behaviour
templates/
  base.html         Shared layout
  landing.html      Landing page
  login.html        Login form
  register.html     Registration form
```

## Implementation status

| Route | Status |
| --- | --- |
| `GET /` | Done |
| `GET /register` | Done |
| `GET /login` | Done |
| `GET /logout` | Placeholder — Step 3 |
| `GET /profile` | Placeholder — Step 4 |
| `GET /expenses/add` | Placeholder — Step 7 |
| `GET /expenses/<id>/edit` | Placeholder — Step 8 |
| `GET /expenses/<id>/delete` | Placeholder — Step 9 |

`database/db.py` is also unimplemented — it needs `get_db()`, `init_db()`, and
`seed_db()` (Step 1).
