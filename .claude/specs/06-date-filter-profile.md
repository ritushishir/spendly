# Spec: Date Filter on Profile

## Overview
Step 6 lets a signed-in user narrow their profile page to a date range. Right
now `/profile` always shows every expense the account has ever recorded — fine
for the eight seeded rows, useless once a real user has hundreds. This step adds
a **From / To** filter bar above the transaction panel; submitting it reloads
`/profile` with `?start=&end=` query parameters, and every figure on the page —
summary stats, transaction list, and category breakdown — recomputes over the
selected window. The filter is a GET form on purpose: the resulting URL is
shareable, bookmarkable, and survives a refresh, and it keeps the page a single
read-only route with no new endpoints. This is the last step before expense
creation (Step 7), so it also establishes the date-validation helper that the
add/edit forms will reuse.

## Depends on
- Step 1: Database setup — `get_db()`, `expenses.date` stored as ISO `YYYY-MM-DD`
- Step 2: Registration — accounts exist
- Step 3: Login / Logout — `session["user_id"]` and `@login_required` exist
- Step 4: Profile page UI — `profile.html` renders all four sections
- Step 5: Backend connection — `/profile` reads live data via
  `get_expenses_for_user()` and `get_category_totals_for_user()`

## Routes
- `GET /profile` — **modified, not new.** Accepts two optional query
  parameters, `start` and `end`, both `YYYY-MM-DD`. Omitting both (or passing
  blanks) behaves exactly as today: all expenses, no filter. Access:
  logged-in only, unchanged `@login_required`.

No new routes.

## Database changes
No database changes. `expenses.date` is already `TEXT NOT NULL` holding
zero-padded ISO dates (`day()` in `seed_db()` formats `%04d-%02d-%02d`), so
lexicographic `>=` / `<=` comparison in SQL is a correct date comparison. No new
columns, tables, indexes, or constraints.

## Templates
- **Create:** none.
- **Modify:** `templates/profile.html`
  - Add a filter bar between the stats row (`.stats-row`) and
    `.profile-grid`: a `<form method="get" action="{{ url_for('profile') }}">`
    with two `<input type="date" name="start">` / `name="end"` fields, an
    "Apply" submit button, and a "Clear" link back to the unfiltered
    `url_for('profile')` shown only when a filter is active.
  - Both date inputs must be pre-filled from `filters.start` / `filters.end`
    so the form reflects the range currently applied.
  - Render `filter_error` into the bar when validation fails (same pattern as
    `.auth-error` in the auth templates — a plain string passed to
    `render_template`, no flash messages).
  - Show `filters.label` (e.g. "1 Aug 2026 – 4 Aug 2026", or "All time") next
    to the panel title so the numbers on screen are never ambiguous.
  - The transaction panel needs a second empty state: distinguish "No expenses
    yet" (the account has none at all) from "No expenses in this range"
    (filter matched nothing). Same for the breakdown panel.

## Files to change
- `database/db.py`
  - `get_expenses_for_user(user_id, start=None, end=None)` — add two optional
    keyword parameters. Build the `WHERE` clause conditionally and append
    values to the parameter tuple; `ORDER BY date DESC, id DESC` is unchanged.
  - `get_category_totals_for_user(user_id, start=None, end=None)` — same
    treatment, `GROUP BY` / `ORDER BY` unchanged.
  - Both keep their existing call signature working when the new arguments are
    omitted, so nothing else in the app has to change at once.
- `app.py`
  - Add `_parse_date_arg(value)` — returns a validated ISO date string, or
    `None` for blank/missing input. Uses
    `datetime.strptime(value, "%Y-%m-%d")` and raises/flags on anything else.
  - Add `_range_label(start, end)` — human-readable label built from the
    existing `_display_date()` helper: both bounds → "1 Aug 2026 – 4 Aug 2026",
    start only → "From 1 Aug 2026", end only → "Up to 4 Aug 2026", neither →
    "All time".
  - `profile()` — read `request.args`, validate, pass `start`/`end` down to
    both query helpers, and add `filters` and `filter_error` to the
    `render_template` call. The existing `_initials` / `_rupees` /
    `_display_date` formatting stays exactly as it is.
- `static/css/style.css`
  - Add `.filter-bar`, `.filter-field`, `.filter-actions`, `.filter-error`,
    `.filter-label`, and a `.filter-clear` link, plus a narrow-screen rule that
    stacks the fields. Reuse `.form-input`, `.btn-primary`, and `.btn-ghost`
    rather than restyling controls from scratch.

## Files to create
No new files.

## New dependencies
No new dependencies. `datetime` is stdlib and already imported in `app.py`.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` through `get_db()` only.
- Parameterised queries only. The date bounds are user input from the query
  string: they go in the parameter tuple, never into an f-string or `%`-format.
  Only the *presence* of a clause may be decided in Python.
- Passwords hashed with werkzeug — unchanged; this step touches no auth code.
- Use CSS variables — never hardcode hex values. The filter bar uses
  `--paper-card`, `--border`, `--radius-md`, `--ink-muted`, `--font-body`, etc.
- All templates extend `base.html`.
- Every expense query keeps its `user_id = ?` filter. A date filter must never
  replace or weaken the ownership check — one account must not be able to read
  another's rows by supplying a range.
- Invalid dates must not 500. A malformed `?start=banana`, an impossible date
  like `2026-02-31`, or a `start` later than `end` renders the page with
  `filter_error` set and falls back to the unfiltered result set.
- Bounds are inclusive on both ends: `?start=2026-08-01&end=2026-08-01` returns
  that day's expenses.
- A missing bound is open-ended, not "today" and not "epoch" — `?start=` alone
  means everything from that date onwards.
- Summary stats, transaction list, **and** category breakdown must all reflect
  the same filtered set. A total that disagrees with the rows below it is the
  main failure mode of this step.
- No inline styles, no JavaScript. `static/js/main.js` stays empty — the native
  `<input type="date">` and a plain GET submit are the whole interaction.
- Amounts stay in ₹ via the existing `_rupees()` helper.

## Definition of done
- [ ] Signed in as the seed user, `/profile` with no query string shows all 8
      transactions and ₹4,295.25 total spent — identical to before this step.
- [ ] The filter bar renders above the two panels with empty From / To inputs
      and a range label reading "All time".
- [ ] Picking a From date of the 3rd of the current month and applying it
      reloads with `?start=…` in the URL, shows only the 4 expenses dated the
      3rd or 4th, and the total drops to ₹1,944.75.
- [ ] Setting To = the 1st of the current month shows only the 2 expenses from
      that day (₹1,820.50), and "Transactions" reads 2.
- [ ] Setting From and To to the same day (the 2nd) returns that day's 2 rows —
      bounds are inclusive.
- [ ] With a filter applied, the category breakdown lists only categories that
      appear in the filtered rows, and its totals sum to the "Total spent" stat.
- [ ] "Top category" reflects the filtered range, not the all-time winner.
- [ ] After applying a filter, both date inputs are still populated with the
      applied values and a "Clear" link is visible; clicking it returns to the
      unfiltered `/profile`.
- [ ] Visiting `/profile?start=banana` renders the page with a visible error
      message and the full unfiltered list — no traceback, still HTTP 200.
- [ ] Visiting `/profile?start=2026-02-31` behaves the same way (rejected as
      invalid, not silently coerced).
- [ ] Visiting `/profile?start=2026-08-04&end=2026-08-01` (start after end)
      shows an error and the unfiltered list.
- [ ] A range with no expenses in it (e.g. `?start=2020-01-01&end=2020-01-31`)
      shows "No expenses in this range" in both panels, ₹0.00 total, 0
      transactions, and "—" for top category — not the "No expenses yet" copy.
- [ ] A brand-new registered user sees "No expenses yet" (not the range copy)
      and the filter bar still renders without error.
- [ ] `/profile?start=2026-01-01` while signed out still redirects to `/login`.
- [ ] Two accounts with expenses: applying a range as user A never shows a row
      belonging to user B.
- [ ] The page has no inline `style=` attributes and no new hex colours in
      `style.css`.
