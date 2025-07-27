from flask import Flask, render_template, request, redirect, url_for
import calendar
import datetime
import sqlite3
import os

DB_NAME = 'studysmart.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
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
    cal = calendar.HTMLCalendar(calendar.MONDAY).formatmonth(now.year, now.month)

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
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
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        'INSERT INTO STUDY_HOURS (study_date, num_minutes, descr) VALUES (?, ?, ?)',
        (study_date, int(num_minutes), descr[:500]),
    )
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
