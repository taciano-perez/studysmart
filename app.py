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
                studied_parent BOOLEAN DEFAULT FALSE,
                notes VARCHAR(250)
            )"""
        )
        c.execute(
            "ALTER TABLE STUDY_HOURS ADD COLUMN IF NOT EXISTS studied_parent BOOLEAN DEFAULT FALSE"
        )
        c.execute(
            "ALTER TABLE STUDY_HOURS ADD COLUMN IF NOT EXISTS notes VARCHAR(250)"
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
                studied_parent INTEGER DEFAULT 0,
                notes TEXT
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
        if 'notes' not in cols:
            c.execute(
                "ALTER TABLE STUDY_HOURS ADD COLUMN notes TEXT"
            )
        conn.commit()
        conn.close()

init_db()

app = Flask(__name__)

@app.route('/')
def index():
    now = datetime.date.today()
    month_str = request.args.get('month')
    if month_str:
        try:
            display_month = datetime.datetime.strptime(month_str, '%Y-%m').date()
            display_month = display_month.replace(day=1)
        except ValueError:
            display_month = now.replace(day=1)
    else:
        display_month = now.replace(day=1)

    logging.info(
        "Rendering index for %s (current month %s)",
        display_month.isoformat(),
        now.isoformat(),
    )
    cal = calendar.HTMLCalendar(calendar.MONDAY).formatmonth(
        display_month.year, display_month.month
    )

    display_month_str = display_month.strftime('%Y-%m')
    prev_month = (display_month - datetime.timedelta(days=1)).replace(day=1)
    next_month_candidate = (display_month + datetime.timedelta(days=31)).replace(day=1)
    next_month = (
        next_month_candidate if next_month_candidate <= now.replace(day=1) else None
    )

    conn = get_conn()
    c = conn.cursor()
    if USING_POSTGRES:
        c.execute(
            "SELECT id, study_date, num_minutes, descr, studied_parent, notes FROM STUDY_HOURS "
            "WHERE to_char(study_date, 'YYYY-MM') = %s",
            (display_month_str,),
        )
    else:
        c.execute(
            "SELECT id, study_date, num_minutes, descr, studied_parent, notes FROM STUDY_HOURS "
            "WHERE strftime('%Y-%m', study_date) = ?",
            (display_month_str,),
        )
    rows = [
        {
            "id": r[0],
            "study_date": r[1],
            "num_minutes": r[2],
            "descr": r[3],
            "studied_parent": bool(r[4]),
            "notes": r[5],
        }
        for r in c.fetchall()
    ]
    logging.info("Fetched %d study rows", len(rows))
    logging.debug("Study rows detail: %s", rows)
    if USING_POSTGRES:
        c.execute(
            "SELECT id, date, number_hours FROM SLEEP_HOURS "
            "WHERE to_char(date, 'YYYY-MM') = %s",
            (display_month_str,),
        )
    else:
        c.execute(
            "SELECT id, date, number_hours FROM SLEEP_HOURS "
            "WHERE strftime('%Y-%m', date) = ?",
            (display_month_str,),
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
    weeks = []
    for i in range(4):
        week_start = start_week - datetime.timedelta(days=7 * i)
        week_end = week_start + datetime.timedelta(days=6)
        if USING_POSTGRES:
            c.execute(
                "SELECT study_date, SUM(num_minutes) FROM STUDY_HOURS "
                "WHERE study_date BETWEEN %s AND %s GROUP BY study_date",
                (week_start, week_end),
            )
        else:
            c.execute(
                "SELECT study_date, SUM(num_minutes) FROM STUDY_HOURS "
                "WHERE study_date BETWEEN ? AND ? GROUP BY study_date",
                (week_start.isoformat(), week_end.isoformat()),
            )
        week_rows = c.fetchall()
        week_minutes = [0] * 7
        for d, total in week_rows:
            dt = d if isinstance(d, datetime.date) else datetime.date.fromisoformat(d)
            idx = (dt - week_start).days
            week_minutes[idx] = total
        week_total = sum(week_minutes)
        week_colors = []
        if week_total >= 300:
            for m in week_minutes:
                if m >= 60:
                    week_colors.append('bg-success')
                else:
                    week_colors.append('bg-secondary')
        else:
            if i == 0:
                today_idx = now.weekday()
                for j, m in enumerate(week_minutes):
                    if j >= today_idx:
                        week_colors.append('bg-white')
                    elif m >= 60:
                        week_colors.append('bg-success')
                    elif m > 0:
                        week_colors.append('bg-warning')
                    else:
                        week_colors.append('bg-danger')
            else:
                for m in week_minutes:
                    if m >= 60:
                        week_colors.append('bg-success')
                    elif m > 0:
                        week_colors.append('bg-warning')
                    else:
                        week_colors.append('bg-danger')
        week_num = (now - datetime.timedelta(days=7 * i)).isocalendar()[1]
        weeks.append({'week_num': week_num, 'colors': week_colors, 'total': week_total})

    if USING_POSTGRES:
        c.execute(
            "SELECT descr, SUM(num_minutes) FROM STUDY_HOURS GROUP BY descr"
        )
    else:
        c.execute(
            "SELECT descr, SUM(num_minutes) FROM STUDY_HOURS GROUP BY descr"
        )
    subject_totals = [
        {"descr": (r[0] or ''), "num_minutes": r[1]} for r in c.fetchall()
    ]
    max_minutes = max((r["num_minutes"] for r in subject_totals), default=0)
    for r in subject_totals:
        r["num_hours"] = round(r["num_minutes"] / 60.0, 2)
        r["percent"] = (
            r["num_minutes"] / max_minutes * 100 if max_minutes else 0
        )
    conn.close()

    return render_template(
        'index.html',
        calendar_html=cal,
        today=now.isoformat(),
        study_rows=rows,
        sleep_rows=sleep_rows,
        weeks=weeks,
        subject_totals=subject_totals,
        prev_month=prev_month.strftime('%Y-%m'),
        next_month=(next_month.strftime('%Y-%m') if next_month else None),
    )


@app.route('/study_hours', methods=['POST'])
def study_hours():
    study_date = request.form.get('studyDate')
    num_minutes = request.form.get('studyLength')
    descr = request.form.get('studyDesc', '')
    descr = descr.strip().lower()
    notes = request.form.get('studyNotes', '')
    notes = notes.strip()
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
            'INSERT INTO STUDY_HOURS (study_date, num_minutes, descr, studied_parent, notes) VALUES (%s, %s, %s, %s, %s)',
            (study_date, int(num_minutes), descr[:500], studied_parent, notes[:250] if notes else None),
        )
    else:
        c.execute(
            'INSERT INTO STUDY_HOURS (study_date, num_minutes, descr, studied_parent, notes) VALUES (?, ?, ?, ?, ?)',
            (study_date, int(num_minutes), descr[:500], int(studied_parent), notes[:250] if notes else None),
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
