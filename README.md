# StudySmart

A web application to help high schoolers to manage their study and sleep hours. I have created it to help my daughter track & plan her studies.

It also served as a vehicle for me to explore how to use AI agents for coding. StudySmart has been entirely developed using OpenAI's Codex. For this project, I followed the "vibe coding" approach, where I hardly did any reviews of the code.

The application consists of a Python frontend and a SQL database. It is deployed to Render.com.

## Setup

Install the requirements (requires network access to PyPI):

```bash
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

When deployed (for example on Render), the service is started with
``gunicorn app:app`` as defined in ``render.yaml``.

Then open `http://127.0.0.1:5000/` in your browser. The app now reads the
`PORT` environment variable if set (for example on Render), defaulting to
`5000` when run locally.

The application uses SQLite to store study hours when run locally. In that case, the 
database file `studysmart.db` is created automatically on first run.
On Render, if the `DATABASE_URL` environment variable is provided (for example by
attaching the **studysmart** PostgreSQL database), the app connects to that
database instead. The SQLite file `studysmart.db` is only created when no
external database URL is present.

## Design

StudySmart is a small, server-rendered Flask application. Most behavior is kept in
`app.py`; there is no separate service or model layer. A request generally flows
from a Flask route, through SQL executed with a DB-API cursor, into a Jinja
template, with a little browser-side JavaScript adding interactions to the
rendered page.

### Repository map

- `app.py` selects and initializes the database, defines every route, performs
  queries and report calculations, and starts the development server.
- `templates/base.html` provides the shared HTML shell and loads Bootstrap from a
  CDN.
- `templates/index.html` contains the complete user interface: the calendar,
  entry forms, targets and reports, plus inline CSS and JavaScript for modals,
  calendar markers, tooltips and deletion.
- `tests/test_app.py` exercises the application through Flask's test client while
  replacing `app.DB_NAME` with a temporary SQLite database.
- `SCHOOL_YEAR_REPORTS_DESIGN.md` records the school-year selector's boundary,
  query, UI and test decisions.
- `render.yaml` describes the Render deployment. It installs dependencies, runs
  the test suite, then serves `app:app` with Gunicorn.

### Request and data flow

`GET /` is the main read path. It parses the optional `month=YYYY-MM` and
`school_year=2026-2027` query parameters, fetches the selected month's study and
sleep entries, calculates per-subject totals and weekly study status for the
selected school year, and renders `index.html`. The template embeds the monthly
rows as JSON; its JavaScript attaches colored markers and delete controls to the
days in Python's generated HTML calendar.

The write paths use HTML form field names as their input contract:

- `POST /study_hours` reads `studyDate`, `studyLength`, `studyDesc`, optional
  `studiedParent`, and optional `studyNotes`, then inserts a study entry.
- `POST /sleep_hours` reads `sleepDate` and `sleepLength`, then inserts a sleep
  entry.
- `POST /delete/<entry_type>/<entry_id>` deletes a `study` or `sleep` entry and is
  called with `fetch()` by the tooltip UI.

Both create routes redirect to `/`; deletion returns HTTP 204 and the browser
reloads the page.

### Persistence and domain rules

`get_conn()` is the database boundary. Database selection happens once when
`app.py` is imported: a usable `DATABASE_URL` selects PostgreSQL, otherwise the
application uses SQLite at `DB_NAME`. `init_db()` creates the two tables and
performs the small additive migrations needed by older databases. SQL branches
on `USING_POSTGRES` because placeholders, date queries, ID types and booleans
differ between PostgreSQL and SQLite.

The tables are intentionally simple:

- `STUDY_HOURS`: date, duration in minutes, lower-cased subject/description, a
  studied-with-parent flag, and optional notes.
- `SLEEP_HOURS`: date and duration in whole hours.

School-year report ranges start on the Monday of ISO week 30, continue through
ISO week 31 of the following year, and use the starting year in their label (for
example, `2026-2027`). A week meets its target at 300 study minutes; individual
days meet their target at 60 minutes. Subject totals and weekly rows are limited
to the selected school year, while calendar markers are limited to the
independently selected month. The school-year dropdown always includes the
current year plus every year represented by stored data. Future-month navigation
is deliberately hidden.

### Changing the application safely

Keep the route, template and schema contracts synchronized. For example, adding
a study field requires updating table creation/migration for both databases, the
two SQL insert/select paths, the dictionary passed to Jinja, the form and its
JavaScript rendering, and the tests. Preserve parameterized SQL and explicitly
commit writes. Date values must remain ISO `YYYY-MM-DD` strings at the HTML and
SQLite boundaries; PostgreSQL may return them as `datetime.date` objects.

Tests should use the existing `client` fixture so they do not touch the checked-in
local database. Because database choice and initial schema creation occur during
module import, tests that need a different backend or environment must configure
it before importing `app`. For larger changes, natural extraction seams are a
database/repository module, pure reporting functions, and separate static CSS and
JavaScript files; until such a refactor is made, `app.py` and `index.html` are the
authoritative implementation.

## Testing

To run the automated tests:

```bash
pytest
```
