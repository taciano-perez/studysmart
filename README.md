# StudySmart

A simple Flask web application that displays the current month's calendar.
A plus button above the calendar opens a dialog with two options: **study hours** and **sleep time**.

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
=======
The application uses SQLite to store study hours. 