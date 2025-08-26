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
                descr VARCHAR(500),
                studied_parent BOOLEAN DEFAULT FALSE
            )"""
        )
        c.execute(
            "ALTER TABLE STUDY_HOURS ADD COLUMN IF NOT EXISTS studied_parent BOOLEAN DEFAULT FALSE"
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS SLEEP_HOURS (
                id SERIAL PRIMARY KEY,
                date DATE,
                number_hours INTEGER
            )"""
        )
    else:
        c.execute(
            """CREATE TABLE IF NOT EXISTS STUDY_HOURS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                study_date TEXT,
                num_minutes INTEGER,
                descr VARCHAR(500),
                studied_parent INTEGER DEFAULT 0
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS SLEEP_HOURS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                number_hours INTEGER
            )"""
        )
        c.execute("PRAGMA table_info(STUDY_HOURS)")
        cols = [col[1] for col in c.fetchall()]
        if 'studied_parent' not in cols:
            c.execute(
                "ALTER TABLE STUDY_HOURS ADD COLUMN studied_parent INTEGER DEFAULT 0"
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
            "SELECT id, study_date, num_minutes, descr, studied_parent FROM STUDY_HOURS "
            "WHERE to_char(study_date, 'YYYY-MM') = %s",
            (now.strftime('%Y-%m'),),
        )
    else:
        c.execute(
            "SELECT id, study_date, num_minutes, descr, studied_parent FROM STUDY_HOURS "
            "WHERE strftime('%Y-%m', study_date) = ?",
            (now.strftime('%Y-%m'),),
        )
    rows = [
        {
            "id": r[0],
            "study_date": r[1],
            "num_minutes": r[2],
            "descr": r[3],
            "studied_parent": bool(r[4]),
        }
        for r in c.fetchall()
    ]
    logging.info("Fetched %d study rows", len(rows))
    logging.debug("Study rows detail: %s", rows)
    if USING_POSTGRES:
        c.execute(
            "SELECT id, date, number_hours FROM SLEEP_HOURS "
            "WHERE to_char(date, 'YYYY-MM') = %s",
            (now.strftime('%Y-%m'),),
        )
    else:
        c.execute(
            "SELECT id, date, number_hours FROM SLEEP_HOURS "
            "WHERE strftime('%Y-%m', date) = ?",
            (now.strftime('%Y-%m'),),
        )
    sleep_rows = [
        {
            "id": r[0],
            "sleep_date": r[1],
            "number_hours": r[2],
        }
        for r in c.fetchall()
    ]
    logging.info("Fetched %d sleep rows", len(sleep_rows))
    logging.debug("Sleep rows detail: %s", sleep_rows)
    start_week = now - datetime.timedelta(days=now.weekday())
    end_week = start_week + datetime.timedelta(days=6)
    if USING_POSTGRES:
        c.execute(
            "SELECT study_date, SUM(num_minutes) FROM STUDY_HOURS "
            "WHERE study_date BETWEEN %s AND %s GROUP BY study_date",
            (start_week, end_week),
        )
    else:
        c.execute(
            "SELECT study_date, SUM(num_minutes) FROM STUDY_HOURS "
            "WHERE study_date BETWEEN ? AND ? GROUP BY study_date",
            (start_week.isoformat(), end_week.isoformat()),
        )
    week_rows = c.fetchall()
    week_minutes = [0] * 7
    for d, total in week_rows:
        dt = d if isinstance(d, datetime.date) else datetime.date.fromisoformat(d)
        idx = (dt - start_week).days
        week_minutes[idx] = total
    week_total = sum(week_minutes)
    week_num = now.isocalendar()[1]
    week_colors = []
    today_idx = now.weekday()
    for i, m in enumerate(week_minutes):
        if i >= today_idx:
            week_colors.append('bg-white')
        elif m >= 60:
            week_colors.append('bg-success')
        elif m > 0:
            week_colors.append('bg-warning')
        else:
            week_colors.append('bg-secondary' if week_total >= 300 else 'bg-danger')

    prev_start_week = start_week - datetime.timedelta(days=7)
    prev_end_week = start_week - datetime.timedelta(days=1)
    if USING_POSTGRES:
        c.execute(
            "SELECT study_date, SUM(num_minutes) FROM STUDY_HOURS "
            "WHERE study_date BETWEEN %s AND %s GROUP BY study_date",
            (prev_start_week, prev_end_week),
        )
    else:
        c.execute(
            "SELECT study_date, SUM(num_minutes) FROM STUDY_HOURS "
            "WHERE study_date BETWEEN ? AND ? GROUP BY study_date",
            (prev_start_week.isoformat(), prev_end_week.isoformat()),
        )
    prev_week_rows = c.fetchall()
    prev_week_minutes = [0] * 7
    for d, total in prev_week_rows:
        dt = d if isinstance(d, datetime.date) else datetime.date.fromisoformat(d)
        idx = (dt - prev_start_week).days
        prev_week_minutes[idx] = total
    prev_week_total = sum(prev_week_minutes)
    prev_week_num = (now - datetime.timedelta(days=7)).isocalendar()[1]
    prev_week_colors = []
    for m in prev_week_minutes:
        if m >= 60:
            prev_week_colors.append('bg-success')
        elif m > 0:
            prev_week_colors.append('bg-warning')
        else:
            prev_week_colors.append('bg-secondary' if prev_week_total >= 300 else 'bg-danger')
    conn.close()

    return render_template(
        'index.html',
        calendar_html=cal,
        today=now.isoformat(),
        study_rows=rows,
        sleep_rows=sleep_rows,
        week_total=week_total,
        week_num=week_num,
        week_colors=week_colors,
        prev_week_total=prev_week_total,
        prev_week_num=prev_week_num,
        prev_week_colors=prev_week_colors,
    )


@app.route('/study_hours', methods=['POST'])
def study_hours():
    study_date = request.form.get('studyDate')
    num_minutes = request.form.get('studyLength')
    descr = request.form.get('studyDesc', '')
    studied_parent = bool(request.form.get('studiedParent'))
    logging.info(
        "Received study hours submission date=%s minutes=%s parent=%s",
        study_date,
        num_minutes,
        studied_parent,
    )
    conn = get_conn()
    c = conn.cursor()
    if USING_POSTGRES:
        c.execute(
            'INSERT INTO STUDY_HOURS (study_date, num_minutes, descr, studied_parent) VALUES (%s, %s, %s, %s)',
            (study_date, int(num_minutes), descr[:500], studied_parent),
        )
    else:
        c.execute(
            'INSERT INTO STUDY_HOURS (study_date, num_minutes, descr, studied_parent) VALUES (?, ?, ?, ?)',
            (study_date, int(num_minutes), descr[:500], int(studied_parent)),
        )
    conn.commit()
    logging.info("Study hours inserted for %s", study_date)
    conn.close()
    return redirect(url_for('index'))


@app.route('/sleep_hours', methods=['POST'])
def sleep_hours():
    sleep_date = request.form.get('sleepDate')
    number_hours = request.form.get('sleepLength')
    logging.info("Received sleep hours submission date=%s hours=%s", sleep_date, number_hours)
    conn = get_conn()
    c = conn.cursor()
    if USING_POSTGRES:
        c.execute(
            'INSERT INTO SLEEP_HOURS (date, number_hours) VALUES (%s, %s)',
            (sleep_date, int(number_hours)),
        )
    else:
        c.execute(
            'INSERT INTO SLEEP_HOURS (date, number_hours) VALUES (?, ?)',
            (sleep_date, int(number_hours)),
        )
    conn.commit()
    logging.info("Sleep hours inserted for %s", sleep_date)
    conn.close()
    return redirect(url_for('index'))


@app.route('/delete/<string:entry_type>/<int:entry_id>', methods=['POST'])
def delete_entry(entry_type, entry_id):
    logging.info("Deleting %s entry with id=%s", entry_type, entry_id)
    conn = get_conn()
    c = conn.cursor()
    if entry_type == 'study':
        if USING_POSTGRES:
            c.execute('DELETE FROM STUDY_HOURS WHERE id = %s', (entry_id,))
        else:
            c.execute('DELETE FROM STUDY_HOURS WHERE id = ?', (entry_id,))
    elif entry_type == 'sleep':
        if USING_POSTGRES:
            c.execute('DELETE FROM SLEEP_HOURS WHERE id = %s', (entry_id,))
        else:
            c.execute('DELETE FROM SLEEP_HOURS WHERE id = ?', (entry_id,))
    else:
        conn.close()
        logging.warning("Invalid entry type for deletion: %s", entry_type)
        return ('Invalid type', 400)
    conn.commit()
    conn.close()
    return ('', 204)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
