from flask import Flask, render_template, request, redirect, url_for
import calendar
import datetime
import sqlite3
import os
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
try:
    import psycopg2
except ImportError:
    psycopg2 = None

USING_POSTGRES = bool(os.environ.get('DATABASE_URL') and psycopg2)
if USING_POSTGRES:
    print("Using PostgreSQL database", flush=True)
else:
    print("Using local SQLite database", flush=True)
    
DB_NAME = 'studysmart.db'

def get_conn():
    if USING_POSTGRES:
        return psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_conn()
    c = conn.cursor()
    if USING_POSTGRES:
        c.execute(
            """CREATE TABLE IF NOT EXISTS STUDY_HOURS (
                id SERIAL PRIMARY KEY,
                study_date DATE,
                num_minutes INTEGER,
                descr VARCHAR(500)
            )"""
        )
    else:
        c.execute(
            """CREATE TABLE IF NOT EXISTS STUDY_HOURS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                study_date TEXT,
                num_minutes INTEGER,
                descr VARCHAR(500)
            )"""
        )
    conn.commit()
    conn.close()

init_db()

app = Flask(__name__)

@app.route('/')
def index():
    now = datetime.date.today()
    logging.info("Rendering index for %s", now.isoformat())
    cal = calendar.HTMLCalendar(calendar.MONDAY).formatmonth(now.year, now.month)

    conn = get_conn()
    c = conn.cursor()
    if USING_POSTGRES:
        c.execute(
            "SELECT study_date, num_minutes, descr FROM STUDY_HOURS "
            "WHERE to_char(study_date, 'YYYY-MM') = %s",
            (now.strftime('%Y-%m'),),
        )
    else:
        c.execute(
            "SELECT study_date, num_minutes, descr FROM STUDY_HOURS "
            "WHERE strftime('%Y-%m', study_date) = ?",
            (now.strftime('%Y-%m'),),
        )
    rows = [
        {
            "study_date": r[0],
            "num_minutes": r[1],
            "descr": r[2],
        }
        for r in c.fetchall()
    ]
    logging.info("Fetched %d study rows", len(rows))
    logging.debug("Study rows detail: %s", rows)
    conn.close()

    return render_template(
        'index.html',
        calendar_html=cal,
        today=now.isoformat(),
        study_rows=rows,
    )


@app.route('/study_hours', methods=['POST'])
def study_hours():
    study_date = request.form.get('studyDate')
    num_minutes = request.form.get('studyLength')
    descr = request.form.get('studyDesc', '')
    logging.info("Received study hours submission date=%s minutes=%s", study_date, num_minutes)
    conn = get_conn()
    c = conn.cursor()
    if USING_POSTGRES:
        c.execute(
            'INSERT INTO STUDY_HOURS (study_date, num_minutes, descr) VALUES (%s, %s, %s)',
            (study_date, int(num_minutes), descr[:500]),
        )
    else:
        c.execute(
            'INSERT INTO STUDY_HOURS (study_date, num_minutes, descr) VALUES (?, ?, ?)',
            (study_date, int(num_minutes), descr[:500]),
        )
    conn.commit()
    logging.info("Study hours inserted for %s", study_date)
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
